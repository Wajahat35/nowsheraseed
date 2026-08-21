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

# Helper for string normalization
def normalize_str(s):
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r'[^\w\s]', ' ', s)
    return re.sub(r'\s+', ' ', s)

COMMON_STOP_WORDS = set([
    'seed', 'seeds', 'banao', 'bana', 'invoice', 'purchase', 'sales', 'sale', 
    'gate', 'pass', 'gatepass', 'rate', 'bags', 'bag', 'boray', 'bori', 'rupay', 
    'rs', 'rupees', 'se', 'ko', 'hai', 'ka', 'ki', 'ke', 'aur', 'do', 'wala', 
    'bhejni', 'karo', 'kar', 'dein', 'bata', 'karini', 'hain', 'naam', 'driver', 
    'vehicle', 'gaari', 'gari', 'number', 'bana'
])

# ---------------------------------------------------------------------------
# DATABASE ENTITY MATCHERS (STOP-WORD FILTERED WORD OVERLAP + LEVENSHTEIN)
# ---------------------------------------------------------------------------
def match_supplier(query):
    if not query:
        return {'status': 'not_found', 'match': None, 'choices': []}
    
    q_norm = normalize_str(query)
    q_words = set(w for w in q_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)
    suppliers = Supplier.objects.all()
    if not suppliers.exists() or not q_words:
        return {'status': 'not_found', 'match': None, 'choices': []}

    matches = []
    for s in suppliers:
        name_norm = normalize_str(s.name)
        comp_norm = normalize_str(s.company_name or "")
        full_norm = f"{name_norm} {comp_norm}"
        s_words = set(w for w in full_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)

        # 1. Check word overlap
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

    if best_score >= 0.70:
        if len(matches) > 1 and matches[1][0] >= 0.70 and (best_score - matches[1][0]) < 0.10:
            candidates = [m[1] for m in matches if m[0] >= 0.50][:4]
            return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'company': c.company_name or ''} for c in candidates]}
        return {'status': 'high_confidence', 'match': best_supplier, 'choices': []}
    elif best_score >= 0.35:
        candidates = [m[1] for m in matches if m[0] >= 0.30][:4]
        return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'company': c.company_name or ''} for c in candidates]}
    
    return {'status': 'not_found', 'match': None, 'choices': []}


def match_customer(query):
    if not query:
        return {'status': 'not_found', 'match': None, 'choices': []}
    
    q_norm = normalize_str(query)
    q_words = set(w for w in q_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)
    customers = Customer.objects.all()
    if not customers.exists() or not q_words:
        return {'status': 'not_found', 'match': None, 'choices': []}

    matches = []
    for c in customers:
        name_norm = normalize_str(c.name)
        comp_norm = normalize_str(c.company_name or "")
        full_norm = f"{name_norm} {comp_norm}"
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

    if best_score >= 0.70:
        if len(matches) > 1 and matches[1][0] >= 0.70 and (best_score - matches[1][0]) < 0.10:
            candidates = [m[1] for m in matches if m[0] >= 0.50][:4]
            return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'company': c.company_name or ''} for c in candidates]}
        return {'status': 'high_confidence', 'match': best_cust, 'choices': []}
    elif best_score >= 0.35:
        candidates = [m[1] for m in matches if m[0] >= 0.30][:4]
        return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'company': c.company_name or ''} for c in candidates]}
    
    return {'status': 'not_found', 'match': None, 'choices': []}


def match_seed(query):
    if not query:
        return {'status': 'not_found', 'match': None, 'choices': []}
    
    q_norm = normalize_str(query)
    q_words = set(w for w in q_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)
    seeds = Seed.objects.all()
    if not seeds.exists() or not q_words:
        return {'status': 'not_found', 'match': None, 'choices': []}

    matches = []
    for s in seeds:
        name_norm = normalize_str(s.name)
        var_norm = normalize_str(s.variety or "")
        full_norm = f"{name_norm} {var_norm}"
        s_words = set(w for w in full_norm.split() if len(w) > 2 and w not in COMMON_STOP_WORDS)

        common = q_words.intersection(s_words)
        if common:
            score = 0.80 + (0.10 * len(common))
            matches.append((score, s))
        else:
            ratio_full = difflib.SequenceMatcher(None, q_norm, full_norm).ratio()
            ratio_name = difflib.SequenceMatcher(None, q_norm, name_norm).ratio()
            matches.append((max(ratio_full, ratio_name), s))

    matches.sort(key=lambda x: x[0], reverse=True)
    best_score, best_seed = matches[0]

    if best_score >= 0.70:
        if len(matches) > 1 and matches[1][0] >= 0.70 and (best_score - matches[1][0]) < 0.10:
            candidates = [m[1] for m in matches if m[0] >= 0.50][:4]
            return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'variety': c.variety or ''} for c in candidates]}
        return {'status': 'high_confidence', 'match': best_seed, 'choices': []}
    elif best_score >= 0.35:
        candidates = [m[1] for m in matches if m[0] >= 0.30][:4]
        return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'variety': c.variety or ''} for c in candidates]}
    
    return {'status': 'not_found', 'match': None, 'choices': []}


# ---------------------------------------------------------------------------
# NUMERIC & ENTITY PARSER
# ---------------------------------------------------------------------------
def parse_voice_numbers(text):
    """Extracts numbers, quantities, rates, and amounts from spoken text."""
    numbers = [int(n) for n in re.findall(r'\b\d+\b', text)]
    
    qty = None
    rate = None

    qty_match = re.search(r'(\d+)\s*(?:bag|bags|boray|bori|bora|kg|pack|kilo)', text, re.IGNORECASE)
    if qty_match:
        qty = int(qty_match.group(1))

    rate_match = re.search(r'(?:rate|price|rupay|rs|rupees|per bag|rate ka)?\s*(\d+)\s*(?:rupay|rs|rupees|per bag)?', text, re.IGNORECASE)
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
    """Extracts vehicle/truck numbers like LEA-1234, LES 4890, etc."""
    m = re.search(r'([a-z]{2,4}[-\s]?\d{3,4})', text, re.IGNORECASE)
    if m:
        return m.group(1).upper().replace(' ', '-')
    return None


def parse_driver_name(text):
    """Extracts driver name from text."""
    m = re.search(r'(?:driver|gari wala|driver ka naam|driver hai)\s+([a-z\s]+)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip().title()
        name = re.sub(r'\b(hai|aur|ko|ka|ki|ke|bano|banao|bana|do)\b', '', name, flags=re.IGNORECASE).strip()
        if len(name) > 2:
            return name
    return None


def detect_intent(text):
    t_norm = normalize_str(text)

    if any(k in t_norm for k in ['cancel', 'band kar', 'khatam kar', 'reject']):
        return 'CANCEL'
    elif any(k in t_norm for k in ['haan', 'han', 'theek hai', 'approve', 'yes', 'save kar do', 'bilkul sahi', 'ok', 'confirm', 'sahi hai']):
        return 'APPROVE'
    elif any(k in t_norm for k in ['purchase', 'khareed', 'khareedna', 'khareedi', 'buy', 'khareedari']):
        return 'CREATE_PURCHASE'
    elif any(k in t_norm for k in ['sale', 'bechna', 'bech', 'bicho', 'sell', 'bikri', 'sales']):
        return 'CREATE_SALES'
    elif any(k in t_norm for k in ['gate pass', 'gatepass', 'bhejni', 'bahar bhej', 'inward', 'outward', 'truck']):
        return 'CREATE_GATEPASS'
    elif any(k in t_norm for k in ['quantity', 'rate', 'price', 'supplier', 'customer', 'driver', 'vehicle', 'gaari', 'change', 'update', 'kar do', 'nahi']):
        return 'EDIT_DRAFT'
    elif any(k in t_norm for k in ['invoice', 'document', 'banao', 'bana do', 'bana', 'bag', 'bags', 'wheat', 'rice', 'seed']):
        return 'UNCLEAR_DOC_TYPE'
    return 'UNKNOWN'


# ---------------------------------------------------------------------------
# MAIN CONVERSATIONAL STATE MACHINE
# ---------------------------------------------------------------------------
def process_voice_command(user, text, session_id=None):
    text_clean = text.strip()
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
            'response_text': "Ji, draft cancel kar di gayi hai. Aap nayi voice command de sakte hain.",
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

        doc_num, err = finalize_voice_draft(session)
        if err:
            return {
                'session_id': session.id,
                'status': 'DRAFT_PENDING',
                'response_text': f"Validation error: {err}. Please correct the field.",
                'draft': draft
            }
        session.status = 'APPROVED'
        session.save()
        return {
            'session_id': None,
            'status': 'APPROVED',
            'response_text': f"Document successfully create ho gaya hai! Reference Number: {doc_num}.",
            'draft': draft,
            'final_doc_number': doc_num
        }

    # 3. UNCLEAR DOCUMENT TYPE
    if intent == 'UNCLEAR_DOC_TYPE' and not session:
        qty, rate = parse_voice_numbers(text_clean)
        seed_res = match_seed(text_clean)
        
        draft_data = {
            'doc_type': None,
            'party_id': None,
            'party_name': None,
            'party_company': None,
            'party_ambiguous': [],
            'seed_id': seed_res['match'].id if seed_res and seed_res['status'] == 'high_confidence' else None,
            'seed_name': seed_res['match'].name if seed_res and seed_res['status'] == 'high_confidence' else None,
            'seed_ambiguous': seed_res['choices'] if seed_res and seed_res['status'] == 'ambiguous' else [],
            'quantity': qty or None,
            'rate': float(rate) if rate else None,
            'total_amount': float((qty or 0) * (rate or 0)),
            'driver_name': parse_driver_name(text_clean),
            'vehicle_no': parse_vehicle_number(text_clean),
            'stock_warning': None
        }

        session = VoiceDraftSession.objects.create(
            user=user,
            doc_type='PURCHASE_INVOICE',
            draft_data=draft_data,
            transcript_history=[{'user': text_clean, 'time': str(timezone.now())}]
        )

        return {
            'session_id': session.id,
            'status': 'DRAFT_PENDING',
            'response_text': "Aap Purchase Invoice, Sales Invoice ya Gate Pass banana chahte hain?",
            'draft': draft_data
        }

    # 4. CONVERSATIONAL UPDATE TO EXISTING ACTIVE SESSION
    if session:
        draft = session.draft_data
        
        if not draft.get('doc_type') or any(k in text_clean.lower() for k in ['purchase', 'sale', 'sales', 'gate', 'pass']):
            if intent == 'CREATE_SALES':
                draft['doc_type'] = 'SALES_INVOICE'
                session.doc_type = 'SALES_INVOICE'
            elif intent == 'CREATE_PURCHASE':
                draft['doc_type'] = 'PURCHASE_INVOICE'
                session.doc_type = 'PURCHASE_INVOICE'
            elif intent == 'CREATE_GATEPASS':
                draft['doc_type'] = 'GATE_PASS'
                session.doc_type = 'GATE_PASS'

        doc_type = draft.get('doc_type') or 'PURCHASE_INVOICE'

        qty, rate = parse_voice_numbers(text_clean)
        if qty:
            draft['quantity'] = qty
        if rate:
            draft['rate'] = float(rate)

        v_num = parse_vehicle_number(text_clean)
        if v_num:
            draft['vehicle_no'] = v_num
        
        d_name = parse_driver_name(text_clean)
        if d_name:
            draft['driver_name'] = d_name
        elif doc_type == 'GATE_PASS' and not draft.get('driver_name'):
            if not qty and not rate and not v_num and len(text_clean) < 30 and not any(k in text_clean.lower() for k in ['pass', 'gate', 'invoice']):
                draft['driver_name'] = text_clean.title()

        # Match party (Supplier vs Customer)
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

        # Match Seed if missing
        if not draft.get('seed_name'):
            seed_res = match_seed(text_clean)
            if seed_res['status'] == 'high_confidence':
                draft['seed_id'] = seed_res['match'].id
                draft['seed_name'] = seed_res['match'].name
                draft['seed_variety'] = seed_res['match'].variety or ''
                draft['seed_ambiguous'] = []
            elif seed_res['status'] == 'ambiguous':
                draft['seed_ambiguous'] = seed_res['choices']

        # Recalculate totals
        t_qty = draft.get('quantity', 0) or 0
        u_rate = draft.get('rate', 0) or 0
        draft['total_amount'] = float(t_qty * u_rate)

        # Stock check for Sales
        if doc_type == 'SALES_INVOICE' and draft.get('seed_id'):
            batches = SeedBatch.objects.filter(seed_id=draft['seed_id'])
            avail_stock = sum(b.current_qty for b in batches)
            if t_qty > avail_stock:
                draft['stock_warning'] = f"Is seed ({draft.get('seed_name')}) ka available stock {avail_stock} bags hai, lekin aap ne {t_qty} bags sale karne ko kaha hai."
            else:
                draft['stock_warning'] = None

        session.draft_data = draft
        session.transcript_history.append({'user': text_clean, 'time': str(timezone.now())})
        session.save()

        # Check missing required fields
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

    # 5. INITIAL NEW COMMAND PARSING
    if intent in ['CREATE_PURCHASE', 'CREATE_SALES', 'CREATE_GATEPASS']:
        doc_type = 'PURCHASE_INVOICE'
        if intent == 'CREATE_SALES':
            doc_type = 'SALES_INVOICE'
        elif intent == 'CREATE_GATEPASS':
            doc_type = 'GATE_PASS'

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

        draft_data = {
            'doc_type': doc_type,
            'party_id': party_obj.id if party_obj else None,
            'party_name': party_obj.name if party_obj else None,
            'party_company': party_obj.company_name if party_obj and hasattr(party_obj, 'company_name') else '',
            'party_ambiguous': party_res['choices'] if party_res and party_res['status'] == 'ambiguous' else [],
            'seed_id': seed_obj.id if seed_obj else None,
            'seed_name': seed_obj.name if seed_obj else None,
            'seed_variety': seed_obj.variety if seed_obj else None,
            'seed_ambiguous': seed_res['choices'] if seed_res and seed_res['status'] == 'ambiguous' else [],
            'quantity': qty,
            'rate': float(rate) if rate else (float(seed_obj.purchase_price) if seed_obj and seed_obj.purchase_price and doc_type == 'PURCHASE_INVOICE' else None),
            'total_amount': float((qty or 0) * (float(rate) if rate else 0)),
            'vehicle_no': v_num,
            'driver_name': d_name,
            'stock_warning': None,
        }

        if doc_type == 'SALES_INVOICE' and seed_obj:
            batches = SeedBatch.objects.filter(seed=seed_obj)
            avail_stock = sum(b.current_qty for b in batches)
            if qty and qty > avail_stock:
                draft_data['stock_warning'] = f"Is seed ({seed_obj.name}) ka available stock {avail_stock} bags hai, lekin aap ne {qty} bags sale karne ko kaha hai."

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
        'response_text': "Samajh nahi aaya. Please Purchase Invoice, Sales Invoice, ya Gate Pass ki command dein.",
        'draft': None
    }


# ---------------------------------------------------------------------------
# MISSING REQUIRED FIELDS QUESTION GENERATOR
# ---------------------------------------------------------------------------
def check_missing_required_fields(draft):
    doc_type = draft.get('doc_type')
    if not doc_type:
        return "Document type select nahi hua (Purchase Invoice, Sales Invoice ya Gate Pass)."

    if doc_type == 'PURCHASE_INVOICE':
        if not draft.get('party_name'):
            return "Supplier ka naam missing hai. Please supplier ka naam bata dein."
        if not draft.get('seed_name'):
            return "Seed product name missing hai."
        if not draft.get('quantity'):
            return "Quantity missing hai."
        if not draft.get('rate'):
            return "Rate per bag missing hai."

    elif doc_type == 'SALES_INVOICE':
        if not draft.get('party_name'):
            return "Customer ka naam missing hai. Please customer ka naam bata dein."
        if not draft.get('seed_name'):
            return "Seed product name missing hai."
        if not draft.get('quantity'):
            return "Quantity missing hai."
        if not draft.get('rate'):
            return "Rate per bag missing hai."

    elif doc_type == 'GATE_PASS':
        if not draft.get('seed_name'):
            return "Seed product missing hai."
        if not draft.get('quantity'):
            return "Quantity missing hai."
        if not draft.get('driver_name'):
            return "Driver ka naam missing hai. Please driver ka naam bata dein."
        if not draft.get('vehicle_no'):
            return "Vehicle number missing hai. Please vehicle number bata dein."

    return None


def get_next_missing_question(draft):
    doc_type = draft.get('doc_type')

    if not doc_type:
        return "Aap Purchase Invoice, Sales Invoice ya Gate Pass banana chahte hain?"

    if doc_type == 'PURCHASE_INVOICE':
        if draft.get('party_ambiguous'):
            names = ", ".join([c['name'] for c in draft['party_ambiguous']])
            return f"Mujhe multiple suppliers milay hain: {names}. Please select karein."
        if not draft.get('party_name'):
            return "Please supplier ka naam bata dein."
        if draft.get('seed_ambiguous'):
            seeds = ", ".join([c['name'] for c in draft['seed_ambiguous']])
            return f"Mujhe multiple seeds milay hain: {seeds}. Please select karein."
        if not draft.get('seed_name'):
            return f"Ji, {draft['party_name']} ki purchase invoice ke liye seed product name bata dein."
        if not draft.get('quantity'):
            return f"Kitnay bags {draft['seed_name']} purchase karne hain?"
        if not draft.get('rate'):
            return f"Rate per bag kya hai?"

    elif doc_type == 'SALES_INVOICE':
        if draft.get('party_ambiguous'):
            names = ", ".join([c['name'] for c in draft['party_ambiguous']])
            return f"Mujhe multiple customers milay hain: {names}. Please select karein."
        if not draft.get('party_name'):
            q_str = f"{draft.get('quantity')} bags {draft.get('seed_name')}" if draft.get('quantity') and draft.get('seed_name') else "sales invoice"
            return f"Ji, {q_str} ki sales invoice bana raha hoon. Customer ka naam bata dein."
        if draft.get('seed_ambiguous'):
            seeds = ", ".join([c['name'] for c in draft['seed_ambiguous']])
            return f"Mujhe multiple seeds milay hain: {seeds}. Please select karein."
        if not draft.get('seed_name'):
            return f"{draft['party_name']} ko kaunsa seed sale karna hai?"
        if not draft.get('quantity'):
            return f"Kitnay bags {draft['seed_name']} sale karne hain?"
        if not draft.get('rate'):
            return f"Rate per bag kya hai?"

    elif doc_type == 'GATE_PASS':
        if draft.get('seed_ambiguous'):
            seeds = ", ".join([c['name'] for c in draft['seed_ambiguous']])
            return f"Mujhe multiple seeds milay hain: {seeds}. Please select karein."
        if not draft.get('seed_name'):
            return "Kaunsa seed dispatch karna hai?"
        if not draft.get('quantity'):
            return f"Kitnay bags {draft['seed_name']} ka gate pass banana hai?"
        if not draft.get('driver_name'):
            q_str = f"{draft['quantity']} bags {draft['seed_name']}" if draft.get('quantity') and draft.get('seed_name') else "gate pass"
            return f"Ji, {q_str} ka gate pass bana raha hoon. Driver ka naam bata dein."
        if not draft.get('vehicle_no'):
            return f"Driver {draft['driver_name']} ke truck/gaari ka vehicle number bata dein."

    return None


def build_draft_summary_response(draft):
    doc_type = draft.get('doc_type')
    qty = draft.get('quantity', 0)
    seed = draft.get('seed_name', '')
    tot = draft.get('total_amount', 0)

    if doc_type == 'PURCHASE_INVOICE':
        supp = draft.get('party_name', '')
        return f"Purchase Invoice draft ready hai. Supplier: {supp}, Seed: {seed}, Quantity: {qty} bags, Rate: PKR {draft.get('rate'):,.2f}, Total Amount: PKR {tot:,.2f}. Kya Purchase Invoice bilkul theek hai?"
    elif doc_type == 'SALES_INVOICE':
        cust = draft.get('party_name', '')
        return f"Sales Invoice draft ready hai. Customer: {cust}, Seed: {seed}, Quantity: {qty} bags, Rate: PKR {draft.get('rate'):,.2f}, Total Amount: PKR {tot:,.2f}. Kya Sales Invoice bilkul theek hai?"
    elif doc_type == 'GATE_PASS':
        driver = draft.get('driver_name', '')
        vehicle = draft.get('vehicle_no', '')
        return f"Gate Pass draft ready hai. Seed: {seed}, Quantity: {qty} bags, Driver: {driver}, Vehicle: {vehicle}. Kya Gate Pass bilkul theek hai?"

    return "Draft ready hai. Kya approve karni hai?"


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

            # 1. PURCHASE INVOICE
            if doc_type == 'PURCHASE_INVOICE':
                supp_id = draft.get('party_id')
                seed_id = draft.get('seed_id')
                qty = int(draft.get('quantity', 0) or 0)
                rate = Decimal(str(draft.get('rate', 0) or 0))

                supplier = Supplier.objects.filter(id=supp_id).first() if supp_id else Supplier.objects.filter(name__icontains=draft.get('party_name', '')).first()
                if not supplier:
                    supplier = Supplier.objects.first()

                seed = Seed.objects.filter(id=seed_id).first() if seed_id else Seed.objects.filter(name__icontains=draft.get('seed_name', '')).first()
                if not seed:
                    seed = Seed.objects.first()

                tot = Decimal(str(qty)) * rate

                inv = PurchaseInvoice.objects.create(
                    supplier=supplier,
                    date=today,
                    subtotal=tot,
                    grand_total=tot,
                    paid_amount=tot,
                    payment_status='Paid',
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

                return inv.invoice_number, None

            # 2. SALES INVOICE
            elif doc_type == 'SALES_INVOICE':
                cust_id = draft.get('party_id')
                seed_id = draft.get('seed_id')
                qty = int(draft.get('quantity', 0) or 0)
                rate = Decimal(str(draft.get('rate', 0) or 0))

                customer = Customer.objects.filter(id=cust_id).first() if cust_id else Customer.objects.filter(name__icontains=draft.get('party_name', '')).first()
                if not customer:
                    customer = Customer.objects.first()

                seed = Seed.objects.filter(id=seed_id).first() if seed_id else Seed.objects.filter(name__icontains=draft.get('seed_name', '')).first()
                if not seed:
                    seed = Seed.objects.first()

                tot = Decimal(str(qty)) * rate

                inv = SalesInvoice.objects.create(
                    customer=customer,
                    date=today,
                    subtotal=tot,
                    grand_total=tot,
                    paid_amount=tot,
                    payment_status='Paid',
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

                return inv.invoice_number, None

            # 3. GATE PASS
            elif doc_type == 'GATE_PASS':
                party_name = draft.get('party_name') or ''
                seed_name = draft.get('seed_name') or 'Wheat Seed'
                qty = int(draft.get('quantity', 0) or 0)
                vehicle = draft.get('vehicle_no') or 'LES-1234'
                driver = draft.get('driver_name') or 'Driver'

                gp = GatePass.objects.create(
                    pass_type='MANUAL',
                    vehicle_number=vehicle,
                    driver_name=driver,
                    driver_cnic='35201-1234567-1',
                    driver_mobile='0300-1234567',
                    total_bags=qty,
                    total_weight_kg=Decimal(str(qty * 50)),
                    remarks=f"Party: {party_name} | Seed: {seed_name} (Created via AI Voice Assistant)",
                    created_by=user
                )

                return gp.pass_number, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, str(e)

    return None, "Unknown Document Type"
