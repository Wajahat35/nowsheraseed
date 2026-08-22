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

# ---------------------------------------------------------------------------
# DATABASE ENTITY MATCHERS
# ---------------------------------------------------------------------------
def match_supplier(query):
    if not query:
        return {'status': 'not_found', 'match': None, 'choices': []}
    
    q_norm = normalize_str(query)
    suppliers = Supplier.objects.all()
    if not suppliers.exists():
        return {'status': 'not_found', 'match': None, 'choices': []}

    matches = []
    for s in suppliers:
        name_norm = normalize_str(s.name)
        comp_norm = normalize_str(s.company_name or "")
        full_norm = f"{name_norm} {comp_norm}"
        
        if q_norm and (q_norm in name_norm or name_norm in q_norm or (comp_norm and comp_norm in q_norm)):
            return {'status': 'high_confidence', 'match': s, 'choices': []}

        q_words = set(w for w in q_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)
        s_words = set(w for w in full_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)
        common = q_words.intersection(s_words)
        if common:
            score = 0.80 + (0.10 * len(common))
            matches.append((score, s))
        else:
            ratio_name = difflib.SequenceMatcher(None, q_norm, name_norm).ratio()
            ratio_full = difflib.SequenceMatcher(None, q_norm, full_norm).ratio()
            matches.append((max(ratio_name, ratio_full), s))

    matches.sort(key=lambda x: x[0], reverse=True)
    best_score, best_supplier = matches[0]

    if best_score >= 0.60:
        if len(matches) > 1 and matches[1][0] >= 0.60 and (best_score - matches[1][0]) < 0.10:
            candidates = [m[1] for m in matches if m[0] >= 0.40][:4]
            return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'company': c.company_name or ''} for c in candidates]}
        return {'status': 'high_confidence', 'match': best_supplier, 'choices': []}
    elif best_score >= 0.30:
        candidates = [m[1] for m in matches if m[0] >= 0.25][:4]
        return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'company': c.company_name or ''} for c in candidates]}
    
    return {'status': 'not_found', 'match': None, 'choices': []}


def match_customer(query):
    if not query:
        return {'status': 'not_found', 'match': None, 'choices': []}
    
    q_norm = normalize_str(query)
    customers = Customer.objects.all()
    if not customers.exists():
        return {'status': 'not_found', 'match': None, 'choices': []}

    matches = []
    for c in customers:
        name_norm = normalize_str(c.name)
        comp_norm = normalize_str(c.company_name or "")
        full_norm = f"{name_norm} {comp_norm}"

        if q_norm and (q_norm in name_norm or name_norm in q_norm or (comp_norm and comp_norm in q_norm)):
            return {'status': 'high_confidence', 'match': c, 'choices': []}

        q_words = set(w for w in q_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)
        c_words = set(w for w in full_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)
        common = q_words.intersection(c_words)
        if common:
            score = 0.80 + (0.10 * len(common))
            matches.append((score, c))
        else:
            ratio_name = difflib.SequenceMatcher(None, q_norm, name_norm).ratio()
            ratio_full = difflib.SequenceMatcher(None, q_norm, full_norm).ratio()
            matches.append((max(ratio_name, ratio_full), c))

    matches.sort(key=lambda x: x[0], reverse=True)
    best_score, best_cust = matches[0]

    if best_score >= 0.60:
        if len(matches) > 1 and matches[1][0] >= 0.60 and (best_score - matches[1][0]) < 0.10:
            candidates = [m[1] for m in matches if m[0] >= 0.40][:4]
            return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'company': c.company_name or ''} for c in candidates]}
        return {'status': 'high_confidence', 'match': best_cust, 'choices': []}
    elif best_score >= 0.30:
        candidates = [m[1] for m in matches if m[0] >= 0.25][:4]
        return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'company': c.company_name or ''} for c in candidates]}
    
    return {'status': 'not_found', 'match': None, 'choices': []}


def match_seed(query):
    if not query:
        return {'status': 'not_found', 'match': None, 'choices': []}
    
    q_norm = normalize_str(query)
    seeds = Seed.objects.all()
    if not seeds.exists():
        return {'status': 'not_found', 'match': None, 'choices': []}

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

    matches = []
    q_words = set(w for w in q_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)

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
        else:
            ratio_full = difflib.SequenceMatcher(None, q_norm, full_norm).ratio()
            ratio_name = difflib.SequenceMatcher(None, q_norm, name_norm).ratio()
            matches.append((max(ratio_full, ratio_name), s))

    if not matches:
        return {'status': 'not_found', 'match': None, 'choices': []}

    matches.sort(key=lambda x: x[0], reverse=True)
    best_score, best_seed = matches[0]

    if best_score >= 0.50:
        if len(matches) > 1 and matches[1][0] >= 0.50 and (best_score - matches[1][0]) < 0.10:
            candidates = [m[1] for m in matches if m[0] >= 0.35][:4]
            return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'variety': c.variety or ''} for c in candidates]}
        return {'status': 'high_confidence', 'match': best_seed, 'choices': []}
    elif best_score >= 0.25:
        candidates = [m[1] for m in matches if m[0] >= 0.20][:4]
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

    if any(k in t_norm for k in ['cancel', 'band kar', 'khatam kar', 'reject']):
        return 'CANCEL'
    elif any(k in t_norm for k in ['haan', 'han', 'theek hai', 'approve', 'yes', 'save kar do', 'bilkul sahi', 'ok', 'confirm', 'sahi hai']):
        return 'APPROVE'
    elif any(k in t_norm for k in ['general cargo', 'manual gate pass', 'general gate pass']):
        return 'CREATE_MANUAL_GATEPASS'
    elif any(k in t_norm for k in ['purchase', 'khareed', 'khareedna', 'khareedi', 'buy', 'khareedari']):
        return 'CREATE_PURCHASE'
    elif any(k in t_norm for k in ['sale', 'bechna', 'bech', 'bicho', 'sell', 'bikri', 'sales']):
        return 'CREATE_SALES'
    elif any(k in t_norm for k in ['gate pass', 'gatepass', 'bhejni', 'bahar bhej', 'inward', 'outward', 'truck', 'print', 'nikal']):
        return 'CREATE_GATEPASS'
    elif any(k in t_norm for k in ['quantity', 'rate', 'price', 'supplier', 'customer', 'driver', 'vehicle', 'gaari', 'change', 'update', 'nahi']):
        return 'EDIT_DRAFT'
    elif any(k in t_norm for k in ['invoice', 'document', 'banao', 'bana do', 'bana', 'bag', 'bags', 'wheat', 'rice', 'seed']):
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

        if 'purchase' in text_norm or 'khareed' in text_norm or 'pur' in text_norm:
            p_inv = PurchaseInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
            t_p_inv = TradingPurchaseInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
        elif 'sale' in text_norm or 'sales' in text_norm or 'bech' in text_norm:
            s_inv = SalesInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
            t_s_inv = TradingSalesInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
        else:
            s_inv = SalesInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
            p_inv = PurchaseInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
            t_s_inv = TradingSalesInvoice.objects.filter(invoice_number__icontains=inv_ref).first()
            t_p_inv = TradingPurchaseInvoice.objects.filter(invoice_number__icontains=inv_ref).first()

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
            qty = t_s_inv.quantity
        elif t_p_inv:
            linked_inv_no = t_p_inv.invoice_number
            party_name_str = t_p_inv.supplier_name
            qty = t_p_inv.quantity

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
            'seed_name': seed_obj.name if seed_obj else 'Seed Item',
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

        if doc_type == 'PURCHASE_INVOICE':
            supp_res = match_supplier(text_clean)
            if supp_res['status'] == 'high_confidence':
                draft['party_id'] = supp_res['match'].id
                draft['party_name'] = supp_res['match'].name
                draft['party_company'] = supp_res['match'].company_name or ''
                draft['party_ambiguous'] = []
            elif supp_res['status'] == 'ambiguous':
                draft['party_ambiguous'] = supp_res['choices']
        elif doc_type == 'SALES_INVOICE':
            cust_res = match_customer(text_clean)
            if cust_res['status'] == 'high_confidence':
                draft['party_id'] = cust_res['match'].id
                draft['party_name'] = cust_res['match'].name
                draft['party_company'] = cust_res['match'].company_name or ''
                draft['party_ambiguous'] = []
            elif cust_res['status'] == 'ambiguous':
                draft['party_ambiguous'] = cust_res['choices']

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
        if doc_type == 'PURCHASE_INVOICE':
            party_res = match_supplier(text_clean)
        elif doc_type == 'SALES_INVOICE':
            party_res = match_customer(text_clean)

        seed_res = match_seed(text_clean)
        qty, rate = parse_voice_numbers(text_clean)
        v_num = parse_vehicle_number(text_clean)
        d_name = parse_driver_name(text_clean)

        party_obj = party_res['match'] if party_res and party_res['status'] == 'high_confidence' else None
        seed_obj = seed_res['match'] if seed_res and seed_res['status'] == 'high_confidence' else None

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
            'party_name': party_obj.name if party_obj else None,
            'party_company': party_obj.company_name if party_obj and hasattr(party_obj, 'company_name') else '',
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

                supplier = Supplier.objects.filter(id=supp_id).first() if supp_id else (Supplier.objects.filter(name__icontains=draft.get('party_name', '')).first() if draft.get('party_name') else Supplier.objects.first())
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

                customer = Customer.objects.filter(id=cust_id).first() if cust_id else (Customer.objects.filter(name__icontains=draft.get('party_name', '')).first() if draft.get('party_name') else Customer.objects.first())
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
                elif linked_inv.startswith('INV-'):
                    pass_type = 'SALES'
                elif linked_inv.startswith('PUR-'):
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
                    driver_cnic='35201-1234567-1',
                    driver_mobile='0300-1234567',
                    total_bags=qty,
                    total_weight_kg=Decimal(str(qty * 50)),
                    remarks=rem,
                    created_by=user
                )

                return gp.pass_number, f"/gatepass/{gp.pk}/print/", None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, None, str(e)

    return None, None, "Unknown Document Type"
