import re
import difflib
from decimal import Decimal
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from apps.seeds.models import Seed, SeedBatch
from apps.suppliers.models import Supplier
from apps.customers.models import Customer
from apps.purchases.models import PurchaseInvoice, PurchaseItem
from apps.sales.models import SalesInvoice, SalesItem
from apps.gatepass.models import GatePass
from apps.trading.models import TradingSalesInvoice, TradingPurchaseInvoice, TradingGatePass
from .models import VoiceDraftSession

# ---------------------------------------------------------------------------
# URDU SCRIPT & URDU DIGIT NORMALIZER / TRANSLITERATOR
# ---------------------------------------------------------------------------
URDU_DIGITS_MAP = {
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
}

URDU_WORD_MAP = {
    'پنجاب': 'punjab', 'سیڈ': 'seed', 'سیٹ': 'seed', 'کارپوریشن': 'corporation',
    'چوہدری': 'chaudry', 'چودھری': 'chaudry', 'فارمنگ': 'farming', 'سٹور': 'store',
    'الرحمان': 'al-rehman', 'الرحمن': 'al-rehman', 'ایجنسی': 'agency', 'ٹریڈرز': 'traders',
    'گندم': 'wheat', 'ویٹ': 'wheat', 'فیصل آباد': 'faisalabad', 'فیصلاباد': 'faisalabad',
    'چاول': 'rice', 'رائس': 'rice', 'باسمتی': 'basmati', 'سپر': 'super', 'کرنل': 'kernel',
    'کپاس': 'cotton', 'مکئی': 'maize', 'سرسوں': 'mustard',
    'پرچیز': 'purchase', 'خرید': 'purchase', 'خریداری': 'purchase', 'خریدنی': 'purchase', 'خریدے': 'purchase', 'خریدنا': 'purchase',
    'سیلز': 'sales', 'سیل': 'sales', 'بیچ': 'sales', 'بیچنا': 'sales', 'بیچنی': 'sales', 'بیچو': 'sales',
    'گیٹ پاس': 'gate pass', 'گیٹپاس': 'gate pass', 'گیٹ': 'gate', 'پاس': 'pass', 'نکال': 'print', 'پرنٹ': 'print',
    'انوائس': 'invoice', 'ان وائی': 'inv', 'انواِئس': 'invoice',
    'ڈرائیور': 'driver', 'گاڑی': 'vehicle', 'ٹرک': 'vehicle', 'نمبر': 'number',
    'عمران': 'imran', 'اسلم': 'aslam', 'عثمان': 'usman', 'علی': 'ali', 'احمد': 'ahmed', 'طارق': 'tariq',
    'جنرل کارگو': 'general cargo', 'مینول': 'manual',
    'بوری': 'bags', 'بوریاں': 'bags', 'بیگ': 'bags', 'بیگز': 'bags', 'بینک': 'bags',
    'ریٹ': 'rate', 'قیمت': 'rate', 'روپے': 'rate',
    'زیرو': '0', 'ایک': '1', 'دو': '2', 'تین': '3', 'چار': '4', 'پانچ': '5',
    'چھ': '6', 'سات': '7', 'آٹھ': '8', 'نو': '9', 'دس': '10', 'سو': '100',
    'ون': '1', 'ٹو': '2', 'تھری': '3', 'فور': '4', 'فائیو': '5', 'سکس': '6', 'سیون': '7', 'ایٹ': '8', 'نائن': '9'
}

def normalize_text_all_languages(text):
    if not text:
        return ""
    
    # 1. Convert Urdu / Arabic digits to ASCII digits 0-9
    for u_digit, a_digit in URDU_DIGITS_MAP.items():
        text = text.replace(u_digit, a_digit)
    
    # 2. Transliterate Native Urdu Script words to Roman keywords
    for u_word, r_word in URDU_WORD_MAP.items():
        text = text.replace(u_word, r_word)
        
    return text


def normalize_str(s):
    if not s:
        return ""
    s = normalize_text_all_languages(s)
    s = s.lower().strip()
    s = re.sub(r'[^\w\s]', ' ', s)
    return re.sub(r'\s+', ' ', s)


COMMON_STOP_WORDS = set([
    'seed', 'seeds', 'banao', 'bana', 'invoice', 'purchase', 'sales', 'sale', 
    'gate', 'pass', 'gatepass', 'rate', 'bags', 'bag', 'boray', 'bori', 'rupay', 
    'rs', 'rupees', 'se', 'ko', 'hai', 'ka', 'ki', 'ke', 'aur', 'do', 'wala', 
    'bhejni', 'karo', 'kar', 'dein', 'bata', 'karini', 'hain', 'naam', 'driver', 
    'vehicle', 'gaari', 'gari', 'number', 'bana', 'print', 'krdo', 'kardo', 'kr',
    'nikal', 'bhej', 'do'
])

GENERIC_PARTY_WORDS = set([
    'farming', 'store', 'traders', 'agency', 'corporation', 'company', 'seeds', 
    'seed', 'grain', 'market', 'growers', 'farm', 'agri', 'enterprises', 'ltd', 'limited', 'co'
])

SEED_CROP_WORDS = set([
    'wheat', 'rice', 'basmati', 'cotton', 'maize', 'corn', 'mustard', 'gandum',
    'chawal', 'kapas', 'makai', 'sarson', 'kernel', 'super', 'fsd', 'faisalabad',
    'certified', 'hybrid', 'paddy', 'sugar', 'cane', 'sunflower', 'canola',
    'barley', 'millet', 'sorghum', 'gram', 'chana', 'masoor', 'moong', 'daal',
])

PHONETIC_VARIANTS = {
    'chaudry': 'chaudhry',
    'chaudhary': 'chaudhry',
    'chaudri': 'chaudhry',
    'choudhry': 'chaudhry',
    'choudhary': 'chaudhry',
    'choudry': 'chaudhry',
    'rehman': 'rahman',
    'alrehman': 'rahman',
    'al-rehman': 'rahman',
    'al rehman': 'rahman',
    'psc': 'punjab',
}

def normalize_party_token(w):
    w_low = w.lower().strip()
    return PHONETIC_VARIANTS.get(w_low, w_low)

def party_tokens_match(w1, w2):
    t1 = normalize_party_token(w1)
    t2 = normalize_party_token(w2)
    if t1 == t2:
        return True
    if len(t1) >= 4 and len(t2) >= 4:
        if t1 in t2 or t2 in t1:
            return True
        if difflib.SequenceMatcher(None, t1, t2).ratio() >= 0.75:
            return True
    return False

def extract_clean_party_name(query):
    if not query:
        return ""
    q_norm = normalize_str(query)
    words = [w.title() for w in q_norm.split() if len(w) > 1 and w not in COMMON_STOP_WORDS and w not in SEED_CROP_WORDS and not re.search(r'\d', w)]
    return ' '.join(words) if words else query.strip().title()

def strip_seed_words_from_query(text):
    """Remove seed/crop words and numbers from text before party matching."""
    q_norm = normalize_str(text)
    words = [w for w in q_norm.split() if w not in SEED_CROP_WORDS and not re.search(r'^\d+$', w)]
    return ' '.join(words)

def match_supplier(query):
    if not query:
        return {'status': 'not_found', 'match': None, 'choices': []}
    
    q_norm = normalize_str(query)
    suppliers = Supplier.objects.all()
    if not suppliers.exists():
        clean_p_name = extract_clean_party_name(query)
        return {'status': 'new_entity', 'match': None, 'new_name': clean_p_name, 'choices': []}

    q_words = set(w for w in q_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS and w not in SEED_CROP_WORDS)
    if not q_words:
        return {'status': 'not_found', 'match': None, 'choices': []}

    q_distinct = q_words - GENERIC_PARTY_WORDS
    matches = []

    for s in suppliers:
        name_norm = normalize_str(s.name)
        comp_norm = normalize_str(s.company_name or "")
        full_norm = f"{name_norm} {comp_norm}"
        
        # Substring / Exact match
        if q_norm and (q_norm == name_norm or q_norm == comp_norm or q_norm in full_norm or name_norm in q_norm):
            return {'status': 'high_confidence', 'match': s, 'choices': []}

        s_words = set(w for w in full_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)
        s_distinct = s_words - GENERIC_PARTY_WORDS

        distinct_matches = sum(1 for qw in q_distinct if any(party_tokens_match(qw, sw) for sw in s_distinct))
        all_matches = sum(1 for qw in q_words if any(party_tokens_match(qw, sw) for sw in s_words))

        if q_distinct:
            if distinct_matches > 0:
                score = 0.80 + (0.10 * distinct_matches) + (0.05 * all_matches)
            else:
                score = 0.15 if all_matches > 0 else 0.0
        else:
            score = 0.40 + (0.10 * all_matches) if all_matches > 0 else 0.0

        matches.append((score, s))

    matches.sort(key=lambda x: x[0], reverse=True)
    best_score, best_supplier = matches[0]

    if best_score >= 0.70:
        if len(matches) > 1 and matches[1][0] >= 0.70 and (best_score - matches[1][0]) < 0.05:
            candidates = [m[1] for m in matches if m[0] >= 0.40][:4]
            return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'company': c.company_name or ''} for c in candidates]}
        return {'status': 'high_confidence', 'match': best_supplier, 'choices': []}
    elif best_score >= 0.40:
        candidates = [m[1] for m in matches if m[0] >= 0.25][:4]
        return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'company': c.company_name or ''} for c in candidates]}
    
    if q_distinct:
        clean_p_name = extract_clean_party_name(query)
        return {'status': 'new_entity', 'match': None, 'new_name': clean_p_name, 'choices': []}
    return {'status': 'not_found', 'match': None, 'choices': []}


def match_customer(query):
    if not query:
        return {'status': 'not_found', 'match': None, 'choices': []}
    
    q_norm = normalize_str(query)
    customers = Customer.objects.all()
    if not customers.exists():
        clean_p_name = extract_clean_party_name(query)
        return {'status': 'new_entity', 'match': None, 'new_name': clean_p_name, 'choices': []}

    q_words = set(w for w in q_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS and w not in SEED_CROP_WORDS)
    if not q_words:
        return {'status': 'not_found', 'match': None, 'choices': []}

    q_distinct = q_words - GENERIC_PARTY_WORDS
    matches = []

    for c in customers:
        name_norm = normalize_str(c.name)
        comp_norm = normalize_str(c.company_name or "")
        full_norm = f"{name_norm} {comp_norm}"

        # Substring / Exact match
        if q_norm and (q_norm == name_norm or q_norm == comp_norm or q_norm in full_norm or name_norm in q_norm):
            return {'status': 'high_confidence', 'match': c, 'choices': []}

        c_words = set(w for w in full_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)
        c_distinct = c_words - GENERIC_PARTY_WORDS

        distinct_matches = sum(1 for qw in q_distinct if any(party_tokens_match(qw, sw) for sw in c_distinct))
        all_matches = sum(1 for qw in q_words if any(party_tokens_match(qw, sw) for sw in c_words))

        if q_distinct:
            if distinct_matches > 0:
                score = 0.80 + (0.10 * distinct_matches) + (0.05 * all_matches)
            else:
                score = 0.15 if all_matches > 0 else 0.0
        else:
            score = 0.40 + (0.10 * all_matches) if all_matches > 0 else 0.0

        matches.append((score, c))

    matches.sort(key=lambda x: x[0], reverse=True)
    best_score, best_cust = matches[0]

    if best_score >= 0.70:
        if len(matches) > 1 and matches[1][0] >= 0.70 and (best_score - matches[1][0]) < 0.05:
            candidates = [m[1] for m in matches if m[0] >= 0.40][:4]
            return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'company': c.company_name or ''} for c in candidates]}
        return {'status': 'high_confidence', 'match': best_cust, 'choices': []}
    elif best_score >= 0.40:
        candidates = [m[1] for m in matches if m[0] >= 0.25][:4]
        return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'company': c.company_name or ''} for c in candidates]}
    
    if q_distinct:
        clean_p_name = extract_clean_party_name(query)
        return {'status': 'new_entity', 'match': None, 'new_name': clean_p_name, 'choices': []}
    return {'status': 'not_found', 'match': None, 'choices': []}


def match_seed(query):
    if not query:
        return {'status': 'not_found', 'match': None, 'choices': []}
    
    q_norm = normalize_str(query)
    seeds = Seed.objects.all()
    if not seeds.exists():
        return {'status': 'not_found', 'match': None, 'choices': []}

    # 1. Direct explicit keyword shortcuts
    if any(k in q_norm for k in ['faisalabad', 'wheat', 'gandum', 'fsd']):
        s_match = seeds.filter(name__icontains='wheat').first() or seeds.filter(name__icontains='faisalabad').first()
        if s_match:
            return {'status': 'high_confidence', 'match': s_match, 'choices': []}
    
    if any(k in q_norm for k in ['rice', 'basmati', 'chawal', 'super kernel']):
        s_match = seeds.filter(name__icontains='rice').first() or seeds.filter(name__icontains='basmati').first()
        if s_match:
            return {'status': 'high_confidence', 'match': s_match, 'choices': []}

    if any(k in q_norm for k in ['cotton', 'kapas']):
        s_match = seeds.filter(name__icontains='cotton').first()
        if s_match:
            return {'status': 'high_confidence', 'match': s_match, 'choices': []}

    if any(k in q_norm for k in ['maize', 'makai', 'corn']):
        s_match = seeds.filter(name__icontains='maize').first()
        if s_match:
            return {'status': 'high_confidence', 'match': s_match, 'choices': []}

    # 2. Check token intersection
    q_words = set(w for w in q_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)
    has_seed_token = bool(q_words.intersection(SEED_CROP_WORDS))

    matches = []
    for s in seeds:
        name_norm = normalize_str(s.name)
        var_norm = normalize_str(s.variety or "")
        full_norm = f"{name_norm} {var_norm}"
        s_words = set(w for w in full_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)

        if q_norm and (q_norm in name_norm or q_norm in var_norm or name_norm in q_norm):
            return {'status': 'high_confidence', 'match': s, 'choices': []}

        common = q_words.intersection(s_words)
        if common:
            score = 0.80 + (0.10 * len(common))
            matches.append((score, s))
        elif has_seed_token:
            ratio_full = difflib.SequenceMatcher(None, q_norm, full_norm).ratio()
            ratio_name = difflib.SequenceMatcher(None, q_norm, name_norm).ratio()
            best_r = max(ratio_full, ratio_name)
            if best_r >= 0.50:
                matches.append((best_r, s))

    if not matches:
        return {'status': 'not_found', 'match': None, 'choices': []}

    matches.sort(key=lambda x: x[0], reverse=True)
    best_score, best_seed = matches[0]

    if best_score >= 0.70:
        if len(matches) > 1 and matches[1][0] >= 0.70 and (best_score - matches[1][0]) < 0.05:
            candidates = [m[1] for m in matches if m[0] >= 0.40][:4]
            return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'variety': c.variety or ''} for c in candidates]}
        return {'status': 'high_confidence', 'match': best_seed, 'choices': []}
    elif best_score >= 0.40:
        candidates = [m[1] for m in matches if m[0] >= 0.30][:4]
        return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'variety': c.variety or ''} for c in candidates]}
    
    return {'status': 'not_found', 'match': None, 'choices': []}


# ---------------------------------------------------------------------------
# NUMERIC & ENTITY PARSER
# ---------------------------------------------------------------------------
def parse_voice_numbers(text):
    text_norm = normalize_text_all_languages(text)
    numbers = [int(n) for n in re.findall(r'\b\d+\b', text_norm)]
    
    qty = None
    rate = None

    qty_match = re.search(r'(\d+)\s*(?:bag|bags|boray|bori|bora|kg|pack|kilo|bank)', text_norm, re.IGNORECASE)
    if qty_match:
        qty = int(qty_match.group(1))

    rate_match = re.search(r'(?:rate|price|rupay|rs|rupees|per bag|rate ka)?\s*(\d+)\s*(?:rupay|rs|rupees|per bag)?', text_norm, re.IGNORECASE)
    if rate_match and int(rate_match.group(1)) > 100:
        rate = Decimal(rate_match.group(1))

    if not qty and numbers:
        for n in numbers:
            if n <= 1000:
                qty = n
                break
    if not rate and numbers:
        for n in numbers:
            if n >= 100 and n != qty:
                rate = Decimal(str(n))
                break

    return qty, rate


def parse_crop_name(text):
    """Extract crop name from voice text."""
    t = normalize_str(text)
    CROP_MAP = {
        'wheat': 'Wheat', 'gandum': 'Wheat', 'rice': 'Rice', 'chawal': 'Rice',
        'basmati': 'Basmati Rice', 'cotton': 'Cotton', 'kapas': 'Cotton',
        'maize': 'Maize', 'makai': 'Maize', 'corn': 'Maize',
        'mustard': 'Mustard', 'sarson': 'Mustard', 'paddy': 'Paddy Rice',
        'sugar': 'Sugarcane', 'sunflower': 'Sunflower', 'canola': 'Canola',
        'barley': 'Barley', 'gram': 'Gram', 'chana': 'Gram',
    }
    for key, val in CROP_MAP.items():
        if key in t:
            return val
    return None


def parse_trading_fields(text):
    """Parse crop_weight (kg), rate_per_40kg, and crop_name from trading voice commands."""
    text_norm = normalize_text_all_languages(text)
    numbers = [int(n) for n in re.findall(r'\b\d+\b', text_norm)]

    crop_weight = None
    rate_40kg = None

    # Try to match explicit kg pattern: "2000 kg" or "2000 kilo"
    kg_match = re.search(r'(\d+)\s*(?:kg|kilo|kilogram|kilograms)', text_norm, re.IGNORECASE)
    if kg_match:
        crop_weight = int(kg_match.group(1))

    # Try to match rate pattern: "rate 4800" or "4800 rupees" or "rate per 40 kg 4800"
    rate_match = re.search(r'(?:rate|price|rupay|rs|rupees|per\s*(?:40\s*kg|maund|man)?)?\s*(\d+)\s*(?:rupay|rs|rupees|per\s*(?:40\s*kg|maund|man)?)?', text_norm, re.IGNORECASE)
    if rate_match and int(rate_match.group(1)) > 100:
        candidate = int(rate_match.group(1))
        if candidate != crop_weight:
            rate_40kg = candidate

    # Fallback: assign numbers by size
    if not crop_weight and numbers:
        for n in numbers:
            if n >= 50:  # weight is usually larger
                crop_weight = n
                break
    if not rate_40kg and numbers:
        for n in numbers:
            if n >= 100 and n != crop_weight:
                rate_40kg = n
                break

    crop_name = parse_crop_name(text)

    return crop_name, crop_weight, rate_40kg


def parse_trading_party_name(text):
    """Extract party name for trading invoices — just clean spoken words, no DB lookup."""
    q_norm = normalize_str(text)
    # Remove all command/intent words, seed words, numbers, and stop words
    TRADING_STOP = COMMON_STOP_WORDS | SEED_CROP_WORDS | {'trading', 'mian', 'trader', 'crop', 'per', 'maund', 'man', 'kg', 'kilo'}
    words = [w.title() for w in q_norm.split() if len(w) > 1 and w not in TRADING_STOP and not re.search(r'^\d+$', w)]
    return ' '.join(words) if words else None


def parse_vehicle_number(text):
    """Extracts vehicle plate numbers (e.g. L251, L-251, LES 1234, LES-1234, LEA-999, FD-123)."""
    text_norm = normalize_text_all_languages(text)
    
    m_kw = re.search(r'(?:gari|gaari|vehicle|truck|car)\s*(?:ka\s*)?(?:number|no|num)?\s*(?:hai|is)?\s*([a-z]{1,4}[-\s]?\d{2,4})', text_norm, re.IGNORECASE)
    if m_kw:
        return re.sub(r'\s+', '-', m_kw.group(1).upper())

    m_plate = re.search(r'\b([a-z]{1,4}[-\s]?\d{2,4})\b', text_norm, re.IGNORECASE)
    if m_plate:
        val = m_plate.group(1).upper()
        if not any(k in val.lower() for k in ['inv', 'pur', 'bill', 'pass', 'gate']):
            return re.sub(r'\s+', '-', val)

    return None


def parse_driver_name(text):
    """Extracts driver names (e.g. 'driver imran', 'driver ka naam aslam hai', 'imran')."""
    text_norm = normalize_text_all_languages(text)
    
    m_kw = re.search(r'(?:driver|gari\s*wala)\s*(?:ka\s*)?(?:nam|naam)?\s*(?:hai|is)?\s*([a-z\s]+)', text_norm, re.IGNORECASE)
    if m_kw:
        raw_name = m_kw.group(1).strip()
        words = []
        for w in raw_name.split():
            w_lower = w.lower()
            if w_lower in ['hai', 'is', 'ka', 'nam', 'naam', 'aur', 'gari', 'vehicle', 'number', 'no']:
                break
            if re.match(r'^[a-z]{1,4}\d{2,4}$', w_lower):
                break
            words.append(w.title())
        if words:
            return ' '.join(words)
            
    return None


def parse_fallback_driver(text):
    """Fallback driver parser when user responds directly with a person's name (1-3 words)."""
    text_clean = text.strip()
    words = [w.title() for w in text_clean.split() if w.lower() not in ['hai', 'is', 'ka', 'nam', 'naam', 'gari', 'vehicle', 'number', 'no', 'gate', 'pass', 'invoice', 'sales', 'purchase', 'pur', 'inv']]
    if words and len(words) <= 3 and not any(re.search(r'\d', w) for w in words):
        return ' '.join(words)
    return None


def parse_fallback_vehicle(text):
    """Fallback vehicle parser when user responds directly with a plate code (e.g. L251)."""
    text_clean = text.strip()
    m = re.search(r'\b([a-z]{1,4}[-\s]?\d{2,4})\b', text_clean, re.IGNORECASE)
    if m:
        return re.sub(r'\s+', '-', m.group(1).upper())
    return None


def parse_invoice_ref(text):
    """Extracts invoice reference numbers like '0018', 'invoice 0018', 'sales invoice gate pass 0018'."""
    text_norm = normalize_text_all_languages(text)
    
    m = re.search(r'(?:invoice|inv|bill|pur|sales|purchase)\s*(?:gate\s*)?(?:pass\s*)?(?:number|no|#)?\s*0*(\d{1,5})', text_norm, re.IGNORECASE)
    if m:
        return m.group(1)
    
    m_direct = re.search(r'\b0*(\d{3,5})\b', text_norm)
    if m_direct:
        val = m_direct.group(1)
        if not re.search(rf'[a-z]{{1,4}}[-\s]?{val}', text_norm, re.IGNORECASE):
            return val

    return None


def fetch_available_invoices_for_party(query):
    """Searches Customer/Supplier and returns all active invoices for fallback selection."""
    cust_res = match_customer(query)
    supp_res = match_supplier(query)

    invoices_list = []
    party_name = None

    if cust_res['status'] == 'high_confidence':
        cust = cust_res['match']
        party_name = cust.name
        sales_invs = SalesInvoice.objects.filter(customer=cust).order_by('-id')[:8]
        for inv in sales_invs:
            item = inv.items.first()
            invoices_list.append({
                'invoice_number': inv.invoice_number,
                'doc_type': 'SALES_INVOICE',
                'party_name': cust.name,
                'party_company': cust.company_name or '',
                'date': str(inv.date),
                'seed_name': item.seed.name if item else 'Seed Item',
                'quantity': item.quantity if item else 0,
                'grand_total': float(inv.grand_total)
            })

    elif supp_res['status'] == 'high_confidence':
        supp = supp_res['match']
        party_name = supp.name
        pur_invs = PurchaseInvoice.objects.filter(supplier=supp).order_by('-id')[:8]
        for inv in pur_invs:
            item = inv.items.first()
            invoices_list.append({
                'invoice_number': inv.invoice_number,
                'doc_type': 'PURCHASE_INVOICE',
                'party_name': supp.name,
                'party_company': supp.company_name or '',
                'date': str(inv.date),
                'seed_name': item.seed.name if item else 'Seed Item',
                'quantity': item.quantity if item else 0,
                'grand_total': float(inv.grand_total)
            })

    return party_name, invoices_list


def detect_intent(text):
    t_norm = normalize_str(text)

    def matches_any(keywords):
        return any(re.search(rf'\b{re.escape(k)}\b', t_norm) for k in keywords)

    if matches_any(['cancel', 'band kar', 'khatam kar', 'reject']):
        return 'CANCEL'
    elif matches_any(['general cargo', 'manual gate pass', 'general gate pass']):
        return 'CREATE_MANUAL_GATEPASS'
    # Trading intents (check BEFORE regular purchase/sales so "trading sales" doesn't match "sales")
    elif matches_any(['trading', 'mian traders', 'mian trader', 'crop trading', 'crop invoice']):
        if matches_any(['purchase', 'khareed', 'khareedna', 'buy']):
            return 'CREATE_TRADING_PURCHASE'
        else:
            return 'CREATE_TRADING_SALES'
    elif matches_any(['purchase', 'khareed', 'khareedna', 'khareedi', 'buy', 'khareedari']):
        return 'CREATE_PURCHASE'
    elif matches_any(['sale', 'bechna', 'bech', 'bicho', 'sell', 'bikri', 'sales']):
        return 'CREATE_SALES'
    elif matches_any(['gate pass', 'gatepass', 'bhejni', 'bahar bhej', 'inward', 'outward', 'truck', 'print', 'nikal']):
        return 'CREATE_GATEPASS'
    elif matches_any(['haan', 'han', 'theek hai', 'approve', 'yes', 'save kar do', 'bilkul sahi', 'ok', 'confirm', 'sahi hai', 'save']):
        return 'APPROVE'
    elif matches_any(['quantity', 'rate', 'price', 'supplier', 'customer', 'driver', 'vehicle', 'gaari', 'change', 'update', 'nahi']):
        return 'EDIT_DRAFT'
    elif matches_any(['invoice', 'document', 'banao', 'bana do', 'bana', 'bag', 'bags', 'wheat', 'rice', 'seed']):
        return 'UNCLEAR_DOC_TYPE'
    return 'UNKNOWN'


# ---------------------------------------------------------------------------
# MAIN CONVERSATIONAL STATE MACHINE
# ---------------------------------------------------------------------------
def process_voice_command(user, text, session_id=None):
    text_clean = text.strip()
    text_norm = normalize_str(text_clean)
    intent = detect_intent(text_clean)

    session = None
    if session_id:
        session = VoiceDraftSession.objects.filter(id=session_id, user=user, status='DRAFT_PENDING').first()
    if not session:
        session = VoiceDraftSession.objects.filter(user=user, status='DRAFT_PENDING').first()

    # 1. CANCEL INTENT
    if intent == 'CANCEL':
        if session:
            session.status = 'CANCELLED'
            session.save()
        return {
            'session_id': None,
            'status': 'CANCELLED',
            'response_text': "Draft cancel kar di gayi hai.",
            'draft': None
        }

    # 2. APPROVE INTENT
    if intent == 'APPROVE' and session and session.draft_data:
        draft = session.draft_data

        missing_err = check_missing_required_fields(draft)
        if missing_err:
            return {
                'session_id': session.id,
                'status': 'DRAFT_PENDING',
                'response_text': missing_err,
                'draft': draft
            }

        doc_num, print_url, err = finalize_voice_draft(session)
        if err:
            return {
                'session_id': session.id,
                'status': 'DRAFT_PENDING',
                'response_text': f"Save failed: {err}",
                'draft': draft
            }
        session.status = 'APPROVED'
        session.save()
        return {
            'session_id': None,
            'status': 'APPROVED',
            'print_url': print_url,
            'response_text': f"Document #{doc_num} save ho gaya hai.",
            'draft': draft,
            'final_doc_number': doc_num
        }

    # 3. MANUAL / GENERAL CARGO GATE PASS
    if intent == 'CREATE_MANUAL_GATEPASS':
        seed_res = match_seed(text_clean)
        qty, rate = parse_voice_numbers(text_clean)
        v_num = parse_vehicle_number(text_clean)
        d_name = parse_driver_name(text_clean)
        seed_obj = seed_res['match'] if seed_res and seed_res['status'] == 'high_confidence' else None

        draft_data = {
            'doc_type': 'GATE_PASS',
            'is_manual': True,
            'linked_invoice_number': None,
            'party_name': 'General Cargo',
            'seed_id': seed_obj.id if seed_obj else None,
            'seed_name': seed_obj.name if seed_obj else None,
            'seed_variety': getattr(seed_obj, 'variety', ''),
            'quantity': qty or None,
            'rate': 0.0,
            'total_amount': 0.0,
            'vehicle_no': v_num,
            'driver_name': d_name,
            'stock_warning': None,
        }

        if not session:
            session = VoiceDraftSession.objects.create(
                user=user,
                doc_type='GATE_PASS',
                draft_data=draft_data,
                transcript_history=[{'user': text_clean, 'time': str(timezone.now())}]
            )
        else:
            session.doc_type = 'GATE_PASS'
            session.draft_data = draft_data
            session.save()

        question = get_next_missing_question(draft_data)
        if question:
            return {
                'session_id': session.id,
                'status': 'DRAFT_PENDING',
                'response_text': question,
                'draft': draft_data
            }

        summary = build_draft_summary_response(draft_data)
        return {
            'session_id': session.id,
            'status': 'DRAFT_PENDING',
            'response_text': summary,
            'draft': draft_data
        }

    # 4. GATE PASS LINKING & INVOICE AVAILABILITY CHECK
    inv_ref = parse_invoice_ref(text_clean)
    is_gatepass_cmd = intent == 'CREATE_GATEPASS' or 'gate' in text_norm or 'pass' in text_norm or 'nikal' in text_norm
    is_explicit_inv_request = bool(re.search(r'(?:invoice|inv|bill|pur|sales|purchase)\s*#?\s*0*\d{1,5}', text_norm, re.IGNORECASE))

    # Case A: User says "print gate pass" without invoice number
    if is_gatepass_cmd and not inv_ref and (not session or session.doc_type != 'GATE_PASS'):
        draft_data = {
            'doc_type': 'GATE_PASS',
            'linked_invoice_number': None,
            'party_name': None,
            'seed_name': None,
            'quantity': None,
            'vehicle_no': None,
            'driver_name': None,
            'awaiting_invoice_ref': True
        }
        session = VoiceDraftSession.objects.create(
            user=user,
            doc_type='GATE_PASS',
            draft_data=draft_data,
            transcript_history=[{'user': text_clean, 'time': str(timezone.now())}]
        )
        return {
            'session_id': session.id,
            'status': 'DRAFT_PENDING',
            'response_text': "Invoice number ya Purchase bill number bata dein.",
            'draft': draft_data
        }

    # Case B: Invoice reference is provided or searched
    if is_gatepass_cmd and inv_ref and (not session or is_explicit_inv_request or session.draft_data.get('awaiting_invoice_ref') or session.draft_data.get('failed_inv_ref')):
        s_inv = None
        p_inv = None
        t_s_inv = None
        t_p_inv = None

        m_full = re.search(r'\b(tsl|tpr|inv|pur)[-\s]?0*(\d{1,5})\b', text_norm)
        if m_full:
            pfx = m_full.group(1).lower()
            num = m_full.group(2)
            if pfx == 'tsl':
                t_s_inv = TradingSalesInvoice.objects.filter(invoice_number__icontains=num).first()
            elif pfx == 'tpr':
                t_p_inv = TradingPurchaseInvoice.objects.filter(invoice_number__icontains=num).first()
            elif pfx == 'inv':
                s_inv = SalesInvoice.objects.filter(invoice_number__icontains=num).first()
            elif pfx == 'pur':
                p_inv = PurchaseInvoice.objects.filter(invoice_number__icontains=num).first()

        if not (s_inv or p_inv or t_s_inv or t_p_inv):
            if 'tsl' in text_norm or ('trading' in text_norm and any(k in text_norm for k in ['sale', 'sales', 'bech'])):
                t_s_inv = TradingSalesInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
            elif 'tpr' in text_norm or ('trading' in text_norm and any(k in text_norm for k in ['purchase', 'khareed', 'pur'])):
                t_p_inv = TradingPurchaseInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
            elif 'purchase' in text_norm or 'khareed' in text_norm or 'pur' in text_norm:
                p_inv = PurchaseInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
                if not p_inv:
                    t_p_inv = TradingPurchaseInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
            elif 'sale' in text_norm or 'sales' in text_norm or 'bech' in text_norm or 'inv' in text_norm:
                s_inv = SalesInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
                if not s_inv:
                    t_s_inv = TradingSalesInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
            else:
                t_s_inv = TradingSalesInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
                t_p_inv = TradingPurchaseInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
                s_inv = SalesInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
                p_inv = PurchaseInvoice.objects.filter(invoice_number__icontains=inv_ref).first()

        found_inv = s_inv or p_inv or t_s_inv or t_p_inv

        # FALLBACK CONDITION: Invoice NOT found in DB -> Ask for Supplier/Customer Name to list available invoices!
        if not found_inv:
            draft_data = session.draft_data if session else {'doc_type': 'GATE_PASS'}
            draft_data['failed_inv_ref'] = inv_ref
            draft_data['awaiting_party_for_invoices'] = True

            if not session:
                session = VoiceDraftSession.objects.create(
                    user=user,
                    doc_type='GATE_PASS',
                    draft_data=draft_data,
                    transcript_history=[{'user': text_clean, 'time': str(timezone.now())}]
                )
            else:
                session.draft_data = draft_data
                session.save()

            return {
                'session_id': session.id,
                'status': 'DRAFT_PENDING',
                'response_text': f"Invoice #{inv_ref} available nahi hai. Supplier ya Customer ka naam bata dein taake available invoices check ki ja sakain.",
                'draft': draft_data
            }
        
        # INVOICE FOUND -> Inherit all details automatically!
        party_obj = None
        seed_obj = None
        qty = None
        party_name_str = ""
        seed_name_str = ""

        if s_inv:
            linked_inv_no = s_inv.invoice_number
            party_obj = s_inv.customer
            party_name_str = s_inv.customer.name if s_inv.customer else ""
            first_item = s_inv.items.first()
            if first_item:
                seed_obj = first_item.seed
                qty = first_item.quantity
        elif p_inv:
            linked_inv_no = p_inv.invoice_number
            party_obj = p_inv.supplier
            party_name_str = p_inv.supplier.name if p_inv.supplier else ""
            first_item = p_inv.items.first()
            if first_item:
                seed_obj = first_item.seed
                qty = first_item.quantity
        elif t_s_inv:
            linked_inv_no = t_s_inv.invoice_number
            party_name_str = t_s_inv.customer_name
            seed_name_str = t_s_inv.crop_name or 'Agricultural Crop'
            qty = int(t_s_inv.crop_weight / Decimal('50.0')) if t_s_inv.crop_weight else 50
        elif t_p_inv:
            linked_inv_no = t_p_inv.invoice_number
            party_name_str = t_p_inv.supplier_name
            seed_name_str = t_p_inv.crop_name or 'Agricultural Crop'
            qty = int(t_p_inv.crop_weight / Decimal('50.0')) if t_p_inv.crop_weight else 50

        v_num = parse_vehicle_number(text_clean)
        d_name = parse_driver_name(text_clean)

        draft_data = {
            'doc_type': 'GATE_PASS',
            'linked_invoice_number': linked_inv_no,
            'party_id': party_obj.id if party_obj else None,
            'party_name': party_obj.name if party_obj else (party_name_str or 'Customer'),
            'party_company': getattr(party_obj, 'company_name', ''),
            'party_ambiguous': [],
            'seed_id': seed_obj.id if seed_obj else None,
            'seed_name': seed_obj.name if seed_obj else (seed_name_str or 'Seed Item'),
            'seed_variety': getattr(seed_obj, 'variety', ''),
            'seed_ambiguous': [],
            'quantity': qty or 50,
            'rate': 0.0,
            'total_amount': 0.0,
            'vehicle_no': v_num,
            'driver_name': d_name,
            'stock_warning': None,
        }

        if not session:
            session = VoiceDraftSession.objects.create(
                user=user,
                doc_type='GATE_PASS',
                draft_data=draft_data,
                transcript_history=[{'user': text_clean, 'time': str(timezone.now())}]
            )
        else:
            session.doc_type = 'GATE_PASS'
            session.draft_data = draft_data
            session.save()

        question = get_next_missing_question(draft_data)
        if question:
            return {
                'session_id': session.id,
                'status': 'DRAFT_PENDING',
                'response_text': question,
                'draft': draft_data
            }

        summary = build_draft_summary_response(draft_data)
        return {
            'session_id': session.id,
            'status': 'DRAFT_PENDING',
            'response_text': summary,
            'draft': draft_data
        }

    # Case C: Active Session Fallback - User provided Customer/Supplier Name to check available invoices!
    if session and session.draft_data.get('awaiting_party_for_invoices'):
        party_name_found, available_invs = fetch_available_invoices_for_party(text_clean)
        
        if available_invs:
            draft = session.draft_data
            draft['available_invoices'] = available_invs
            draft['awaiting_party_for_invoices'] = False
            session.draft_data = draft
            session.save()

            inv_summary = ", ".join([f"{inv['invoice_number']} ({inv['seed_name']} {inv['quantity']} bags)" for inv in available_invs[:3]])
            return {
                'session_id': session.id,
                'status': 'DRAFT_PENDING',
                'response_text': f"{party_name_found} ke {len(available_invs)} invoices milay hain: {inv_summary}. Kis invoice ka Gate Pass nikalna hai?",
                'draft': draft
            }

    # 5. UNCLEAR DOCUMENT TYPE (NEW COMMAND)
    if intent == 'UNCLEAR_DOC_TYPE' and not session:
        qty, rate = parse_voice_numbers(text_clean)
        seed_res = match_seed(text_clean)
        supp_res = match_supplier(text_clean)
        cust_res = match_customer(text_clean)
        
        doc_type = 'PURCHASE_INVOICE'
        party_obj = None
        if supp_res['status'] == 'high_confidence':
            doc_type = 'PURCHASE_INVOICE'
            party_obj = supp_res['match']
        elif cust_res['status'] == 'high_confidence':
            doc_type = 'SALES_INVOICE'
            party_obj = cust_res['match']

        seed_obj = seed_res['match'] if seed_res and seed_res['status'] == 'high_confidence' else None

        if not rate and seed_obj:
            if doc_type == 'SALES_INVOICE':
                rate = float(seed_obj.retail_price) if seed_obj.retail_price else 3000.0
            elif doc_type == 'PURCHASE_INVOICE':
                rate = float(seed_obj.purchase_price) if seed_obj.purchase_price else 2500.0

        draft_data = {
            'doc_type': doc_type,
            'payment_status': 'Unpaid',
            'party_id': party_obj.id if party_obj else None,
            'party_name': party_obj.name if party_obj else None,
            'party_company': party_obj.company_name if party_obj and hasattr(party_obj, 'company_name') else '',
            'party_ambiguous': supp_res['choices'] if supp_res['status'] == 'ambiguous' else (cust_res['choices'] if cust_res['status'] == 'ambiguous' else []),
            'seed_id': seed_obj.id if seed_obj else None,
            'seed_name': seed_obj.name if seed_obj else None,
            'seed_variety': seed_obj.variety if seed_obj else None,
            'seed_ambiguous': seed_res['choices'] if seed_res and seed_res['status'] == 'ambiguous' else [],
            'quantity': qty or None,
            'rate': float(rate) if rate else None,
            'total_amount': float((qty or 0) * (float(rate) if rate else 0)),
            'driver_name': parse_driver_name(text_clean),
            'vehicle_no': parse_vehicle_number(text_clean),
            'stock_warning': None
        }

        session = VoiceDraftSession.objects.create(
            user=user,
            doc_type=doc_type,
            draft_data=draft_data,
            transcript_history=[{'user': text_clean, 'time': str(timezone.now())}]
        )

        question = get_next_missing_question(draft_data)
        if question:
            return {
                'session_id': session.id,
                'status': 'DRAFT_PENDING',
                'response_text': question,
                'draft': draft_data
            }

        summary = build_draft_summary_response(draft_data)
        return {
            'session_id': session.id,
            'status': 'DRAFT_PENDING',
            'response_text': summary,
            'draft': draft_data
        }

    # 6. CONVERSATIONAL UPDATE TO EXISTING ACTIVE SESSION
    if session:
        draft = session.draft_data
        
        if intent == 'CREATE_SALES' or 'sales' in text_norm or 'sale' in text_norm:
            draft['doc_type'] = 'SALES_INVOICE'
            session.doc_type = 'SALES_INVOICE'
        elif intent == 'CREATE_PURCHASE' or 'purchase' in text_norm or 'khareed' in text_norm:
            draft['doc_type'] = 'PURCHASE_INVOICE'
            session.doc_type = 'PURCHASE_INVOICE'
        elif intent == 'CREATE_GATEPASS' or 'gate' in text_norm or 'pass' in text_norm:
            draft['doc_type'] = 'GATE_PASS'
            session.doc_type = 'GATE_PASS'

        doc_type = draft.get('doc_type') or 'PURCHASE_INVOICE'

        # Check for payment status toggle
        if 'paid' in text_norm or 'payment ho gayi' in text_norm:
            draft['payment_status'] = 'Paid'
        elif 'unpaid' in text_norm or 'pending' in text_norm:
            draft['payment_status'] = 'Unpaid'

        seed_res = match_seed(text_clean)
        if seed_res['status'] == 'high_confidence':
            draft['seed_id'] = seed_res['match'].id
            draft['seed_name'] = seed_res['match'].name
            draft['seed_variety'] = seed_res['match'].variety or ''
            draft['seed_ambiguous'] = []
            qty_turn, rate_turn = parse_voice_numbers(text_clean)
            if rate_turn:
                draft['rate'] = float(rate_turn)
            else:
                s_obj = seed_res['match']
                if doc_type == 'SALES_INVOICE':
                    draft['rate'] = float(s_obj.retail_price) if s_obj.retail_price else 3000.0
                elif doc_type == 'PURCHASE_INVOICE':
                    draft['rate'] = float(s_obj.purchase_price) if s_obj.purchase_price else 2500.0
        elif seed_res['status'] == 'ambiguous':
            draft['seed_ambiguous'] = seed_res['choices']

        party_query = strip_seed_words_from_query(text_clean)
        if doc_type == 'PURCHASE_INVOICE':
            supp_res = match_supplier(party_query)
            if supp_res['status'] == 'high_confidence':
                draft['party_id'] = supp_res['match'].id
                draft['party_name'] = supp_res['match'].name
                draft['party_company'] = supp_res['match'].company_name or ''
                draft['party_ambiguous'] = []
                draft['is_new_party'] = False
            elif supp_res['status'] == 'ambiguous' and not draft.get('party_id'):
                draft['party_ambiguous'] = supp_res['choices']
            elif supp_res['status'] == 'new_entity' and not draft.get('party_id'):
                draft['party_id'] = None
                draft['party_name'] = supp_res['new_name']
                draft['party_company'] = f"{supp_res['new_name']} (New Supplier)"
                draft['party_ambiguous'] = []
                draft['is_new_party'] = True
        elif doc_type == 'SALES_INVOICE':
            cust_res = match_customer(party_query)
            if cust_res['status'] == 'high_confidence':
                draft['party_id'] = cust_res['match'].id
                draft['party_name'] = cust_res['match'].name
                draft['party_company'] = cust_res['match'].company_name or ''
                draft['party_ambiguous'] = []
                draft['is_new_party'] = False
            elif cust_res['status'] == 'ambiguous' and not draft.get('party_id'):
                draft['party_ambiguous'] = cust_res['choices']
            elif cust_res['status'] == 'new_entity' and not draft.get('party_id'):
                draft['party_id'] = None
                draft['party_name'] = cust_res['new_name']
                draft['party_company'] = f"{cust_res['new_name']} (New Customer)"
                draft['party_ambiguous'] = []
                draft['is_new_party'] = True
        elif doc_type in ('TRADING_SALES', 'TRADING_PURCHASE'):
            # For trading, just take spoken name verbatim
            t_party = parse_trading_party_name(text_clean)
            if t_party:
                draft['party_name'] = t_party
            # Update trading-specific fields
            crop_name, crop_weight, rate_40kg = parse_trading_fields(text_clean)
            if crop_name:
                draft['crop_name'] = crop_name
            if crop_weight:
                draft['crop_weight'] = crop_weight
            if rate_40kg:
                draft['rate_per_40kg'] = rate_40kg
            # Recalculate total
            cw = draft.get('crop_weight', 0) or 0
            r40 = draft.get('rate_per_40kg', 0) or 0
            if cw > 0 and r40 > 0:
                draft['total_amount'] = float((cw / 40.0) * r40)
        qty, rate = parse_voice_numbers(text_clean)
        if qty and not draft.get('linked_invoice_number'):
            draft['quantity'] = qty
        if rate:
            draft['rate'] = float(rate)

        # DRIVER NAME AND VEHICLE NUMBER CONVERSATIONAL UPDATES
        v_num = parse_vehicle_number(text_clean)
        if v_num:
            draft['vehicle_no'] = v_num
        elif doc_type == 'GATE_PASS' and not draft.get('vehicle_no'):
            fb_v = parse_fallback_vehicle(text_clean)
            if fb_v:
                draft['vehicle_no'] = fb_v
        
        d_name = parse_driver_name(text_clean)
        if d_name:
            draft['driver_name'] = d_name
        elif doc_type == 'GATE_PASS' and not draft.get('driver_name'):
            fb_d = parse_fallback_driver(text_clean)
            if fb_d:
                draft['driver_name'] = fb_d

        t_qty = draft.get('quantity', 0) or 0
        u_rate = draft.get('rate', 0) or 0
        draft['total_amount'] = float(t_qty * u_rate)

        if doc_type == 'SALES_INVOICE' and draft.get('seed_id'):
            batches = SeedBatch.objects.filter(seed_id=draft['seed_id'])
            avail_stock = sum(b.current_qty for b in batches)
            if t_qty > avail_stock:
                draft['stock_warning'] = f"Available stock ({avail_stock} bags) se zyada quantity select ki hai."
            else:
                draft['stock_warning'] = None

        print("\n" + "="*50)
        print("VOICE ASSISTANT (CONVERSATIONAL UPDATE) DEBUG LOG")
        print(f"Raw transcript: {text_clean}")
        print(f"Party ID: {draft.get('party_id')}")
        print(f"Party Name: {draft.get('party_name')}")
        print(f"Seed ID: {draft.get('seed_id')}")
        print(f"Seed Name: {draft.get('seed_name')}")
        print(f"Quantity: {draft.get('quantity')}")
        print(f"Rate: {draft.get('rate')}")
        print(f"Total: {draft.get('total_amount')}")
        print("="*50 + "\n")

        session.draft_data = draft
        session.transcript_history.append({'user': text_clean, 'time': str(timezone.now())})
        session.save()

        question = get_next_missing_question(draft)
        if question:
            return {
                'session_id': session.id,
                'status': 'DRAFT_PENDING',
                'response_text': question,
                'draft': draft
            }

        summary = build_draft_summary_response(draft)
        return {
            'session_id': session.id,
            'status': 'DRAFT_PENDING',
            'response_text': summary,
            'draft': draft
        }

    # 7. INITIAL NEW COMMAND PARSING
    if intent in ['CREATE_PURCHASE', 'CREATE_SALES', 'CREATE_GATEPASS', 'UNKNOWN']:
        doc_type = 'PURCHASE_INVOICE'
        if intent == 'CREATE_SALES':
            doc_type = 'SALES_INVOICE'
        elif intent == 'CREATE_GATEPASS':
            doc_type = 'GATE_PASS'
        elif 'se' in text_norm:
            doc_type = 'PURCHASE_INVOICE'
        elif 'ko' in text_norm:
            doc_type = 'SALES_INVOICE'

        party_res = None
        party_query = strip_seed_words_from_query(text_clean)
        if doc_type == 'PURCHASE_INVOICE':
            party_res = match_supplier(party_query)
        elif doc_type == 'SALES_INVOICE':
            party_res = match_customer(party_query)

        seed_res = match_seed(text_clean)
        qty, rate = parse_voice_numbers(text_clean)
        v_num = parse_vehicle_number(text_clean)
        d_name = parse_driver_name(text_clean)

        party_obj = party_res['match'] if party_res and party_res['status'] == 'high_confidence' else None
        new_party_name = party_res.get('new_name') if party_res and party_res['status'] == 'new_entity' else None
        is_new = bool(party_res and party_res['status'] == 'new_entity')
        seed_obj = seed_res['match'] if seed_res and seed_res['status'] == 'high_confidence' else None

        party_name_val = party_obj.name if party_obj else (new_party_name if new_party_name else None)
        party_comp_val = (party_obj.company_name or '') if party_obj else (f"{new_party_name} (New Party)" if new_party_name else '')

        if not rate and seed_obj:
            if doc_type == 'SALES_INVOICE':
                rate = float(seed_obj.retail_price) if seed_obj.retail_price else 3000.0
            elif doc_type == 'PURCHASE_INVOICE':
                rate = float(seed_obj.purchase_price) if seed_obj.purchase_price else 2500.0

        draft_data = {
            'doc_type': doc_type,
            'payment_status': 'Unpaid',
            'linked_invoice_number': None,
            'party_id': party_obj.id if party_obj else None,
            'party_name': party_name_val,
            'party_company': party_comp_val,
            'is_new_party': is_new,
            'party_ambiguous': party_res['choices'] if party_res and party_res['status'] == 'ambiguous' else [],
            'seed_id': seed_obj.id if seed_obj else None,
            'seed_name': seed_obj.name if seed_obj else None,
            'seed_variety': seed_obj.variety if seed_obj else None,
            'seed_ambiguous': seed_res['choices'] if seed_res and seed_res['status'] == 'ambiguous' else [],
            'quantity': qty,
            'rate': float(rate) if rate else None,
            'total_amount': float((qty or 0) * (float(rate) if rate else 0)),
            'vehicle_no': v_num,
            'driver_name': d_name,
            'stock_warning': None,
        }

        print("\n" + "="*50)
        print("VOICE ASSISTANT (NEW DRAFT) DEBUG LOG")
        print(f"Raw transcript: {text_clean}")
        print(f"Detected customer/supplier query: {party_query}")
        print(f"Matched entity: {party_obj.name if party_obj else (new_party_name or 'None')}")
        print(f"Customer/Supplier DB ID: {party_obj.id if party_obj else 'None'}")
        print(f"Doc Type: {doc_type}")
        print(f"Seed: {seed_obj.name if seed_obj else 'None'}")
        print(f"Quantity: {qty}")
        print(f"Rate: {rate}")
        print("="*50 + "\n")

        if doc_type == 'SALES_INVOICE' and seed_obj:
            batches = SeedBatch.objects.filter(seed=seed_obj)
            avail_stock = sum(b.current_qty for b in batches)
            if qty and qty > avail_stock:
                draft_data['stock_warning'] = f"Available stock ({avail_stock} bags) se zyada quantity select ki hai."

        session = VoiceDraftSession.objects.create(
            user=user,
            doc_type=doc_type,
            draft_data=draft_data,
            transcript_history=[{'user': text_clean, 'time': str(timezone.now())}]
        )

        question = get_next_missing_question(draft_data)
        if question:
            return {
                'session_id': session.id,
                'status': 'DRAFT_PENDING',
                'response_text': question,
                'draft': draft_data
            }

        summary = build_draft_summary_response(draft_data)
        return {
            'session_id': session.id,
            'status': 'DRAFT_PENDING',
            'response_text': summary,
            'draft': draft_data
        }

    # 8. TRADING (MIAN TRADERS) INVOICE CREATION
    if intent in ['CREATE_TRADING_SALES', 'CREATE_TRADING_PURCHASE']:
        doc_type = 'TRADING_SALES' if intent == 'CREATE_TRADING_SALES' else 'TRADING_PURCHASE'

        # For trading, just take the spoken party name verbatim — NO DB lookup
        party_name = parse_trading_party_name(text_clean)
        crop_name, crop_weight, rate_40kg = parse_trading_fields(text_clean)

        total_amt = 0.0
        if crop_weight and rate_40kg:
            total_amt = float((crop_weight / 40.0) * rate_40kg)

        draft_data = {
            'doc_type': doc_type,
            'payment_status': 'Unpaid',
            'party_name': party_name,
            'party_company': 'Mian Traders',
            'crop_name': crop_name,
            'crop_weight': crop_weight,
            'rate_per_40kg': rate_40kg,
            'total_amount': total_amt,
            'party_ambiguous': [],
            'seed_ambiguous': [],
        }

        session = VoiceDraftSession.objects.create(
            user=user,
            doc_type=doc_type,
            draft_data=draft_data,
            transcript_history=[{'user': text_clean, 'time': str(timezone.now())}]
        )

        question = get_next_missing_question(draft_data)
        if question:
            return {
                'session_id': session.id,
                'status': 'DRAFT_PENDING',
                'response_text': question,
                'draft': draft_data
            }

        summary = build_draft_summary_response(draft_data)
        return {
            'session_id': session.id,
            'status': 'DRAFT_PENDING',
            'response_text': summary,
            'draft': draft_data
        }

    return {
        'session_id': None,
        'status': 'UNKNOWN',
        'response_text': "Samajh nahi aaya. Please command dein.",
        'draft': None
    }


# ---------------------------------------------------------------------------
# MISSING REQUIRED FIELDS QUESTION GENERATOR
# ---------------------------------------------------------------------------
def check_missing_required_fields(draft):
    doc_type = draft.get('doc_type')
    if not doc_type:
        return "Document type select karain."

    if doc_type == 'PURCHASE_INVOICE':
        if not draft.get('party_name'):
            return "Supplier ka naam bata dein."
        if not draft.get('seed_name'):
            return "Seed product name bata dein."
        if not draft.get('quantity'):
            return "Quantity bata dein."
        if not draft.get('rate'):
            return "Rate per bag bata dein."

    elif doc_type == 'SALES_INVOICE':
        if not draft.get('party_name'):
            return "Customer ka naam bata dein."
        if not draft.get('seed_name'):
            return "Seed product name bata dein."
        if not draft.get('quantity'):
            return "Quantity bata dein."
        if not draft.get('rate'):
            return "Rate per bag bata dein."

    elif doc_type == 'GATE_PASS':
        if not draft.get('linked_invoice_number') and not draft.get('is_manual'):
            if not draft.get('seed_name'):
                return "Seed product name bata dein."
            if not draft.get('quantity'):
                return "Quantity bata dein."
        if not draft.get('driver_name'):
            return "Driver ka naam bata dein."
        if not draft.get('vehicle_no'):
            return "Vehicle number bata dein."

    elif doc_type in ('TRADING_SALES', 'TRADING_PURCHASE'):
        party_label = "Customer" if doc_type == 'TRADING_SALES' else "Supplier"
        if not draft.get('party_name'):
            return f"{party_label} ka naam bata dein."
        if not draft.get('crop_name'):
            return "Crop ka naam bata dein (wheat, rice, cotton etc)."
        if not draft.get('crop_weight'):
            return "Crop weight kitna hai (kg mein bata dein)?"
        if not draft.get('rate_per_40kg'):
            return "Rate per 40 kg (per maund) kya hai?"

    return None


def get_next_missing_question(draft):
    doc_type = draft.get('doc_type')

    if not doc_type:
        return "Aap Purchase Invoice, Sales Invoice ya Gate Pass banana chahte hain?"

    if doc_type == 'PURCHASE_INVOICE':
        if draft.get('party_ambiguous'):
            names = ", ".join([c['name'] for c in draft['party_ambiguous']])
            return f"Multiple suppliers milay hain: {names}. Select karein."
        if not draft.get('party_name'):
            return "Supplier ka naam bata dein."
        if draft.get('seed_ambiguous'):
            seeds = ", ".join([c['name'] for c in draft['seed_ambiguous']])
            return f"Multiple seeds milay hain: {seeds}. Select karein."
        if not draft.get('seed_name'):
            return f"{draft['party_name']} ke liye seed product name bata dein."
        if not draft.get('quantity'):
            return f"Kitnay bags {draft['seed_name']} purchase karne hain?"
        if not draft.get('rate'):
            return f"Rate per bag kya hai?"

    elif doc_type == 'SALES_INVOICE':
        if draft.get('party_ambiguous'):
            names = ", ".join([c['name'] for c in draft['party_ambiguous']])
            return f"Multiple customers milay hain: {names}. Select karein."
        if not draft.get('party_name'):
            return "Customer ka naam bata dein."
        if draft.get('seed_ambiguous'):
            seeds = ", ".join([c['name'] for c in draft['seed_ambiguous']])
            return f"Multiple seeds milay hain: {seeds}. Select karein."
        if not draft.get('seed_name'):
            return f"{draft['party_name']} ko kaunsa seed sale karna hai?"
        if not draft.get('quantity'):
            return f"Kitnay bags {draft['seed_name']} sale karne hain?"
        if not draft.get('rate'):
            return f"Rate per bag kya hai?"

    elif doc_type == 'GATE_PASS':
        linked = f"Invoice #{draft['linked_invoice_number']}" if draft.get('linked_invoice_number') else "Gate Pass"
        
        if not draft.get('linked_invoice_number') and not draft.get('is_manual'):
            if draft.get('seed_ambiguous'):
                seeds = ", ".join([c['name'] for c in draft['seed_ambiguous']])
                return f"Multiple seeds milay hain: {seeds}. Select karein."
            if not draft.get('seed_name'):
                return "Seed product name bata dein."
            if not draft.get('quantity'):
                return "Quantity bata dein."
        
        if not draft.get('driver_name') and not draft.get('vehicle_no'):
            return f"{linked} ke Outward Gate Pass ke liye Driver aur Vehicle number bata dein."
        if not draft.get('driver_name'):
            return f"{linked} ke liye Driver ka naam bata dein."
        if not draft.get('vehicle_no'):
            return f"Driver {draft['driver_name']} ke gaari ka vehicle number bata dein."

    elif doc_type in ('TRADING_SALES', 'TRADING_PURCHASE'):
        party_label = "Customer" if doc_type == 'TRADING_SALES' else "Supplier"
        if not draft.get('party_name'):
            return f"{party_label} ka naam bata dein."
        if not draft.get('crop_name'):
            return f"{draft['party_name']} ke liye crop ka naam bata dein (wheat, rice, cotton etc)."
        if not draft.get('crop_weight'):
            return f"{draft['crop_name']} ka weight kitna hai? (kg mein bata dein)"
        if not draft.get('rate_per_40kg'):
            return f"{draft['crop_name']} ka rate per 40 kg (per maund) kya hai?"

    return None


def build_draft_summary_response(draft):
    doc_type = draft.get('doc_type')

    if doc_type == 'PURCHASE_INVOICE':
        p_status = draft.get('payment_status', 'Unpaid')
        return f"Purchase Invoice ({p_status}) draft ready hai. Approve karain?"
    elif doc_type == 'SALES_INVOICE':
        p_status = draft.get('payment_status', 'Unpaid')
        return f"Sales Invoice ({p_status}) draft ready hai. Approve karain?"
    elif doc_type == 'GATE_PASS':
        linked = f"Invoice #{draft['linked_invoice_number']} ka " if draft.get('linked_invoice_number') else ""
        return f"{linked}Outward Gate Pass draft ready hai. Approve karain?"
    elif doc_type in ('TRADING_SALES', 'TRADING_PURCHASE'):
        p_status = draft.get('payment_status', 'Unpaid')
        t_label = "Trading Sales" if doc_type == 'TRADING_SALES' else "Trading Purchase"
        crop = draft.get('crop_name', 'Crop')
        weight = draft.get('crop_weight', 0)
        return f"Mian Traders {t_label} Invoice - {crop} {weight} Kg ({p_status}) draft ready hai. Approve karain?"

    return "Draft ready hai. Approve karain?"


# ---------------------------------------------------------------------------
# FINALIZATION ENGINE (SAVING REAL DB RECORDS ONLY UPON EXPLICIT APPROVAL)
# ---------------------------------------------------------------------------
def finalize_voice_draft(session):
    draft = session.draft_data
    doc_type = session.doc_type
    user = session.user

    try:
        with transaction.atomic():
            today = timezone.now().date()

            # DEFAULT PAYMENT STATUS = UNPAID (PENDING) UNLESS EXPLICITLY PAID
            pay_status_str = draft.get('payment_status', 'Unpaid')
            is_paid = (pay_status_str == 'Paid')
            payment_status_val = 'Paid' if is_paid else 'Pending'

            # 1. PURCHASE INVOICE
            if doc_type == 'PURCHASE_INVOICE':
                supp_id = draft.get('party_id')
                seed_id = draft.get('seed_id')
                qty = int(draft.get('quantity', 0) or 0)
                rate = Decimal(str(draft.get('rate', 0) or 0))

                supplier = None
                if supp_id:
                    supplier = Supplier.objects.filter(id=supp_id).first()
                if not supplier and draft.get('party_name'):
                    p_name = draft['party_name'].strip()
                    supplier = Supplier.objects.filter(name__iexact=p_name).first() or \
                               Supplier.objects.filter(company_name__iexact=p_name).first() or \
                               Supplier.objects.filter(name__icontains=p_name).first()
                if not supplier and draft.get('party_name') and draft.get('is_new_party'):
                    raw_p_name = str(draft['party_name']).strip().title()
                    supplier = Supplier.objects.create(
                        name=raw_p_name,
                        company_name=raw_p_name,
                        phone='0300-0000000'
                    )
                if not supplier:
                    supplier = Supplier.objects.first()

                seed = Seed.objects.filter(id=seed_id).first() if seed_id else (Seed.objects.filter(name__icontains=draft.get('seed_name', '')).first() if draft.get('seed_name') else Seed.objects.first())
                if not seed:
                    seed = Seed.objects.first()

                tot = Decimal(str(qty)) * rate
                paid_amt = tot if is_paid else Decimal('0.00')

                inv = PurchaseInvoice.objects.create(
                    supplier=supplier,
                    date=today,
                    subtotal=tot,
                    grand_total=tot,
                    paid_amount=paid_amt,
                    payment_status=payment_status_val,
                    notes='Created via AI Voice Assistant',
                    created_by=user
                )

                print("\n" + "="*50)
                print("FINALIZE PURCHASE INVOICE DEBUG LOG")
                print(f"Raw transcript: {session.transcript_history[-1]['user'] if session.transcript_history else 'N/A'}")
                print(f"Detected supplier: {draft.get('party_name')}")
                print(f"Matched supplier: {supplier.name}")
                print(f"Supplier ID: {supplier.id}")
                print(f"Invoice supplier ID: {inv.supplier_id}")
                print(f"Invoice supplier name: {inv.supplier.name}")
                print("="*50 + "\n")

                batch = SeedBatch.objects.filter(seed=seed).order_by('-id').first()
                if not batch:
                    batch = SeedBatch.objects.create(
                        seed=seed,
                        batch_number=f"VOICE-{inv.invoice_number}",
                        lot_number="LOT-VOICE",
                        manufacturing_date=today,
                        expiry_date=today + timedelta(days=365),
                        initial_qty=qty,
                        current_qty=qty,
                        purchase_price=rate,
                        sale_price=seed.retail_price if seed and seed.retail_price else Decimal('0.00')
                    )
                else:
                    batch.current_qty += qty
                    batch.save()

                PurchaseItem.objects.create(
                    purchase_invoice=inv,
                    seed=seed,
                    batch=batch,
                    quantity=qty,
                    unit_price=rate,
                    subtotal=tot
                )

                return inv.invoice_number, f"/purchases/{inv.pk}/print/", None

            # 2. SALES INVOICE
            elif doc_type == 'SALES_INVOICE':
                cust_id = draft.get('party_id')
                seed_id = draft.get('seed_id')
                qty = int(draft.get('quantity', 0) or 0)
                rate = Decimal(str(draft.get('rate', 0) or 0))

                customer = None
                if cust_id:
                    customer = Customer.objects.filter(id=cust_id).first()
                if not customer and draft.get('party_name'):
                    p_name = draft['party_name'].strip()
                    customer = Customer.objects.filter(name__iexact=p_name).first() or \
                               Customer.objects.filter(company_name__iexact=p_name).first() or \
                               Customer.objects.filter(name__icontains=p_name).first()
                if not customer and draft.get('party_name') and draft.get('is_new_party'):
                    raw_p_name = str(draft['party_name']).strip().title()
                    customer = Customer.objects.create(
                        name=raw_p_name,
                        company_name=raw_p_name,
                        phone='0300-0000000'
                    )
                if not customer:
                    customer = Customer.objects.first()

                seed = Seed.objects.filter(id=seed_id).first() if seed_id else (Seed.objects.filter(name__icontains=draft.get('seed_name', '')).first() if draft.get('seed_name') else Seed.objects.first())
                if not seed:
                    seed = Seed.objects.first()

                tot = Decimal(str(qty)) * rate
                paid_amt = tot if is_paid else Decimal('0.00')

                inv = SalesInvoice.objects.create(
                    customer=customer,
                    date=today,
                    subtotal=tot,
                    grand_total=tot,
                    paid_amount=paid_amt,
                    payment_status=payment_status_val,
                    notes='Created via AI Voice Assistant',
                    created_by=user
                )

                print("\n" + "="*50)
                print("FINALIZE SALES INVOICE DEBUG LOG")
                print(f"Raw transcript: {session.transcript_history[-1]['user'] if session.transcript_history else 'N/A'}")
                print(f"Detected customer: {draft.get('party_name')}")
                print(f"Matched customer: {customer.name}")
                print(f"Customer ID: {customer.id}")
                print(f"Invoice customer ID: {inv.customer_id}")
                print(f"Invoice customer name: {inv.customer.name}")
                print("="*50 + "\n")

                batch = SeedBatch.objects.filter(seed=seed, current_qty__gt=0).order_by('-id').first()
                if not batch:
                    batch = SeedBatch.objects.filter(seed=seed).order_by('-id').first()

                if batch:
                    batch.current_qty = max(0, batch.current_qty - qty)
                    batch.save()

                SalesItem.objects.create(
                    sales_invoice=inv,
                    seed=seed,
                    batch=batch,
                    quantity=qty,
                    unit_price=rate,
                    subtotal=tot
                )

                return inv.invoice_number, f"/sales/{inv.pk}/print/", None

            # 3. GATE PASS (OUTWARD FOR SALES, INWARD FOR PURCHASE, MANUAL FOR GENERAL CARGO)
            elif doc_type == 'GATE_PASS':
                party_name = draft.get('party_name') or ''
                seed_name = draft.get('seed_name') or 'Wheat Seed'
                qty = int(draft.get('quantity', 0) or 0)
                vehicle = draft.get('vehicle_no') or 'LES-1234'
                driver = draft.get('driver_name') or 'Driver'
                linked_inv = draft.get('linked_invoice_number') or ''
                is_manual = draft.get('is_manual', False)

                if is_manual or not linked_inv:
                    pass_type = 'MANUAL'
                elif linked_inv.startswith('INV-') or linked_inv.startswith('TSL-'):
                    pass_type = 'SALES'
                elif linked_inv.startswith('PUR-') or linked_inv.startswith('TPR-'):
                    pass_type = 'PURCHASE'
                else:
                    pass_type = 'MANUAL'

                rem = f"Party: {party_name} | Seed: {seed_name}"
                if linked_inv:
                    rem += f" | Linked Invoice: #{linked_inv}"
                rem += " (Created via AI Voice Assistant)"

                gp = GatePass.objects.create(
                    pass_type=pass_type,
                    invoice_reference=linked_inv if linked_inv else None,
                    vehicle_number=vehicle,
                    driver_name=driver,
                    driver_cnic=draft.get('driver_cnic', '') or '',
                    driver_mobile=draft.get('driver_mobile', '') or '',
                    total_bags=qty,
                    total_weight_kg=Decimal(str(qty * 50)),
                    remarks=rem,
                    created_by=user
                )

                return gp.pass_number, f"/gatepass/{gp.pk}/print/", None

            # 4. TRADING SALES INVOICE (MIAN TRADERS)
            elif doc_type == 'TRADING_SALES':
                party_name = draft.get('party_name') or 'Customer'
                crop_name = draft.get('crop_name') or 'Wheat / Agricultural Crop'
                crop_weight = Decimal(str(draft.get('crop_weight', 0) or 0))
                rate_40kg = Decimal(str(draft.get('rate_per_40kg', 0) or 0))
                pay_status_str = draft.get('payment_status', 'Unpaid')
                is_paid = (pay_status_str == 'Paid')

                inv = TradingSalesInvoice.objects.create(
                    date=today,
                    customer_name=party_name,
                    crop_name=crop_name,
                    crop_weight=crop_weight,
                    rate_per_40kg=rate_40kg,
                    paid_amount=(crop_weight / Decimal('40.0') * rate_40kg) if is_paid and crop_weight > 0 and rate_40kg > 0 else Decimal('0.00'),
                    remarks='Created via AI Voice Assistant (Mian Traders)',
                    created_by=user
                )

                return inv.invoice_number, f"/trading/sales/{inv.pk}/", None

            # 5. TRADING PURCHASE INVOICE (MIAN TRADERS)
            elif doc_type == 'TRADING_PURCHASE':
                party_name = draft.get('party_name') or 'Supplier'
                crop_name = draft.get('crop_name') or 'Wheat / Agricultural Crop'
                crop_weight = Decimal(str(draft.get('crop_weight', 0) or 0))
                rate_40kg = Decimal(str(draft.get('rate_per_40kg', 0) or 0))
                pay_status_str = draft.get('payment_status', 'Unpaid')
                is_paid = (pay_status_str == 'Paid')

                inv = TradingPurchaseInvoice.objects.create(
                    date=today,
                    supplier_name=party_name,
                    crop_name=crop_name,
                    crop_weight=crop_weight,
                    rate_per_40kg=rate_40kg,
                    paid_amount=(crop_weight / Decimal('40.0') * rate_40kg) if is_paid and crop_weight > 0 and rate_40kg > 0 else Decimal('0.00'),
                    remarks='Created via AI Voice Assistant (Mian Traders)',
                    created_by=user
                )

                return inv.invoice_number, f"/trading/purchases/{inv.pk}/", None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, None, str(e)

    return None, None, "Unknown Document Type"
