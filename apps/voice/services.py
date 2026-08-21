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

# ---------------------------------------------------------------------------
# DATABASE ENTITY MATCHERS
# ---------------------------------------------------------------------------
def match_supplier(query):
    if not query:
        return {'status': 'not_found', 'match': None, 'choices': []}
    
    q_norm = normalize_str(query)
    suppliers = Supplier.objects.filter(is_active=True)
    if not suppliers.exists():
        return {'status': 'not_found', 'match': None, 'choices': []}

    matches = []
    for s in suppliers:
        name_norm = normalize_str(s.name)
        comp_norm = normalize_str(s.company_name or "")
        
        ratio_name = difflib.SequenceMatcher(None, q_norm, name_norm).ratio()
        ratio_comp = difflib.SequenceMatcher(None, q_norm, comp_norm).ratio()
        
        boost = 0.0
        if q_norm in name_norm or name_norm in q_norm or (comp_norm and q_norm in comp_norm):
            boost = 0.35
            
        score = max(ratio_name, ratio_comp) + boost
        matches.append((score, s))

    matches.sort(key=lambda x: x[0], reverse=True)
    best_score, best_supplier = matches[0]

    if best_score >= 0.75:
        if len(matches) > 1 and matches[1][0] >= 0.70 and abs(best_score - matches[1][0]) < 0.10:
            candidates = [m[1] for m in matches if m[0] >= 0.55][:4]
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
    customers = Customer.objects.filter(is_active=True)
    if not customers.exists():
        return {'status': 'not_found', 'match': None, 'choices': []}

    matches = []
    for c in customers:
        name_norm = normalize_str(c.name)
        comp_norm = normalize_str(c.company_name or "")
        
        ratio_name = difflib.SequenceMatcher(None, q_norm, name_norm).ratio()
        ratio_comp = difflib.SequenceMatcher(None, q_norm, comp_norm).ratio()
        
        boost = 0.0
        if q_norm in name_norm or name_norm in q_norm or (comp_norm and q_norm in comp_norm):
            boost = 0.35
            
        score = max(ratio_name, ratio_comp) + boost
        matches.append((score, c))

    matches.sort(key=lambda x: x[0], reverse=True)
    best_score, best_cust = matches[0]

    if best_score >= 0.75:
        if len(matches) > 1 and matches[1][0] >= 0.70 and abs(best_score - matches[1][0]) < 0.10:
            candidates = [m[1] for m in matches if m[0] >= 0.55][:4]
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
    seeds = Seed.objects.filter(status='Active')
    if not seeds.exists():
        return {'status': 'not_found', 'match': None, 'choices': []}

    matches = []
    for s in seeds:
        name_norm = normalize_str(s.name)
        var_norm = normalize_str(s.variety or "")
        code_norm = normalize_str(s.code or "")
        full_norm = f"{name_norm} {var_norm}"
        
        ratio_full = difflib.SequenceMatcher(None, q_norm, full_norm).ratio()
        ratio_name = difflib.SequenceMatcher(None, q_norm, name_norm).ratio()
        ratio_var = difflib.SequenceMatcher(None, q_norm, var_norm).ratio()
        
        boost = 0.0
        if q_norm in full_norm or name_norm in q_norm or var_norm in q_norm:
            boost = 0.35
            
        score = max(ratio_full, ratio_name, ratio_var) + boost
        matches.append((score, s))

    matches.sort(key=lambda x: x[0], reverse=True)
    best_score, best_seed = matches[0]

    if best_score >= 0.70:
        if len(matches) > 1 and matches[1][0] >= 0.65 and abs(best_score - matches[1][0]) < 0.10:
            candidates = [m[1] for m in matches if m[0] >= 0.50][:4]
            return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'variety': c.variety or ''} for c in candidates]}
        return {'status': 'high_confidence', 'match': best_seed, 'choices': []}
    elif best_score >= 0.35:
        candidates = [m[1] for m in matches if m[0] >= 0.30][:4]
        return {'status': 'ambiguous', 'match': None, 'choices': [{'id': c.id, 'name': c.name, 'variety': c.variety or ''} for c in candidates]}
    
    return {'status': 'not_found', 'match': None, 'choices': []}


# ---------------------------------------------------------------------------
# INTENT & NUMERIC PARSER
# ---------------------------------------------------------------------------
def parse_voice_numbers(text):
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


def detect_intent(text):
    t_norm = normalize_str(text)

    if any(k in t_norm for k in ['cancel', 'band kar', 'khatam kar', 'reject']):
        return 'CANCEL'
    elif any(k in t_norm for k in ['haan', 'han', 'theek hai', 'approve', 'yes', 'save kar do', 'bilkul sahi', 'ok', 'confirm', 'sahi hai']):
        return 'APPROVE'
    elif any(k in t_norm for k in ['purchase', 'khareed', 'khareedna', 'khareedi', 'buy']):
        return 'CREATE_PURCHASE'
    elif any(k in t_norm for k in ['sale', 'bechna', 'bech', 'bicho', 'sell']):
        return 'CREATE_SALES'
    elif any(k in t_norm for k in ['gate pass', 'gatepass', 'bhejni', 'bahar bhej', 'inward', 'outward', 'truck']):
        return 'CREATE_GATEPASS'
    elif any(k in t_norm for k in ['quantity', 'rate', 'price', 'supplier', 'customer', 'change', 'update', 'kar do', 'nahi']):
        return 'EDIT_DRAFT'
    return 'UNKNOWN'


# ---------------------------------------------------------------------------
# MAIN CONVERSATIONAL ENGINE
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
            'response_text': "Ji, draft invoice cancel kar di gayi hai. Aap nayi voice command de sakte hain.",
            'draft': None
        }

    # 2. APPROVE INTENT
    if intent == 'APPROVE' and session and session.draft_data:
        doc_num, err = finalize_voice_draft(session)
        if err:
            return {
                'session_id': session.id,
                'status': 'DRAFT_PENDING',
                'response_text': f"Validation error: {err}. Please correct the field.",
                'draft': session.draft_data
            }
        session.status = 'APPROVED'
        session.save()
        return {
            'session_id': None,
            'status': 'APPROVED',
            'response_text': f"Invoice successfully create ho gayi hai! Reference Number: {doc_num}.",
            'draft': session.draft_data,
            'final_doc_number': doc_num
        }

    # 3. IF EDIT INTENT OR CONVERSATIONAL UPDATE TO EXISTING SESSION
    if session and (intent == 'EDIT_DRAFT' or intent == 'UNKNOWN'):
        draft = session.draft_data
        qty, rate = parse_voice_numbers(text_clean)

        updated_field = None
        if qty:
            draft['quantity'] = qty
            updated_field = f"Quantity {qty} bags"
        if rate:
            draft['rate'] = float(rate)
            updated_field = f"Rate PKR {rate}"

        if 'supplier' in text_clean.lower() or 'party' in text_clean.lower():
            supp_res = match_supplier(text_clean)
            if supp_res['status'] == 'high_confidence':
                draft['party_id'] = supp_res['match'].id
                draft['party_name'] = supp_res['match'].name
                updated_field = f"Supplier {supp_res['match'].name}"

        tot_qty = draft.get('quantity', 0) or 0
        u_rate = draft.get('rate', 0) or 0
        draft['total_amount'] = float(tot_qty * u_rate)

        session.draft_data = draft
        session.transcript_history.append({'user': text_clean, 'time': str(timezone.now())})
        session.save()

        summary_msg = f"{updated_field} update ho gaya hai. Total amount PKR {draft['total_amount']:,.2f} hai. Kya invoice approve karni hai?"
        return {
            'session_id': session.id,
            'status': 'DRAFT_PENDING',
            'response_text': summary_msg,
            'draft': draft
        }

    # 4. INITIAL COMMAND PARSING & CREATION OF NEW DRAFT
    if intent in ['CREATE_PURCHASE', 'CREATE_SALES', 'CREATE_GATEPASS', 'UNKNOWN']:
        doc_type = 'PURCHASE_INVOICE'
        if intent == 'CREATE_SALES':
            doc_type = 'SALES_INVOICE'
        elif intent == 'CREATE_GATEPASS':
            doc_type = 'GATE_PASS'

        party_res = None
        if doc_type == 'PURCHASE_INVOICE':
            party_res = match_supplier(text_clean)
        else:
            party_res = match_customer(text_clean)

        seed_res = match_seed(text_clean)
        qty, rate = parse_voice_numbers(text_clean)

        # Fallback to default party or seed if missing
        fallback_party = None
        if not party_res or party_res['status'] == 'not_found':
            if doc_type == 'PURCHASE_INVOICE':
                fallback_party = Supplier.objects.first()
            else:
                fallback_party = Customer.objects.first()

        fallback_seed = None
        if not seed_res or seed_res['status'] == 'not_found':
            fallback_seed = Seed.objects.first()

        party_obj = party_res['match'] if party_res and party_res['status'] == 'high_confidence' else fallback_party
        seed_obj = seed_res['match'] if seed_res and seed_res['status'] == 'high_confidence' else fallback_seed

        draft_data = {
            'doc_type': doc_type,
            'party_id': party_obj.id if party_obj else None,
            'party_name': party_obj.name if party_obj else None,
            'party_ambiguous': party_res['choices'] if party_res and party_res['status'] == 'ambiguous' else [],
            'seed_id': seed_obj.id if seed_obj else None,
            'seed_name': seed_obj.name if seed_obj else None,
            'seed_variety': seed_obj.variety if seed_obj else None,
            'seed_ambiguous': seed_res['choices'] if seed_res and seed_res['status'] == 'ambiguous' else [],
            'quantity': qty or 100,
            'rate': float(rate) if rate else (float(seed_obj.purchase_price) if seed_obj and seed_obj.purchase_price else 2500.0),
            'total_amount': float((qty or 100) * (float(rate) if rate else (float(seed_obj.purchase_price) if seed_obj and seed_obj.purchase_price else 2500.0))),
            'stock_warning': None,
            'vehicle_no': 'LES-1234' if doc_type == 'GATE_PASS' else '',
            'driver_name': 'Driver' if doc_type == 'GATE_PASS' else '',
        }

        if doc_type == 'SALES_INVOICE' and seed_obj:
            batches = SeedBatch.objects.filter(seed=seed_obj)
            avail_stock = sum(b.current_qty for b in batches)
            if qty and qty > avail_stock:
                draft_data['stock_warning'] = f"Is seed ({seed_obj.name}) ka available stock {avail_stock} bags hai, lekin aap ne {qty} bags sale karne ko kaha hai."

        if session:
            session.doc_type = doc_type
            session.draft_data = draft_data
            session.save()
        else:
            session = VoiceDraftSession.objects.create(
                user=user,
                doc_type=doc_type,
                draft_data=draft_data,
                transcript_history=[{'user': text_clean, 'time': str(timezone.now())}]
            )

        resp_parts = []
        if party_res and party_res['status'] == 'ambiguous':
            names_str = ", ".join([c['name'] for c in party_res['choices']])
            resp_parts.append(f"Mujhe multiple party names milay hain: {names_str}. Please select karein.")

        if seed_res and seed_res['status'] == 'ambiguous':
            seeds_str = ", ".join([c['name'] for c in seed_res['choices']])
            resp_parts.append(f"Mujhe multiple seeds milay hain: {seeds_str}. Please select karein.")

        if not resp_parts:
            p_type_label = "Purchase Invoice" if doc_type == 'PURCHASE_INVOICE' else ("Sales Invoice" if doc_type == 'SALES_INVOICE' else "Gate Pass")
            resp_parts.append(f"{p_type_label} draft ready hai. Supplier/Party: {draft_data['party_name']}, Seed: {draft_data['seed_name']}, Quantity: {draft_data['quantity']} bags, Total Amount: PKR {draft_data['total_amount']:,.2f}. Kya invoice bilkul theek hai?")

        return {
            'session_id': session.id,
            'status': 'DRAFT_PENDING',
            'response_text': " ".join(resp_parts),
            'draft': draft_data
        }


# ---------------------------------------------------------------------------
# FINALIZATION ENGINE (EXECUTED ONLY AFTER EXPLICIT USER APPROVAL)
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

                supplier = Supplier.objects.filter(id=supp_id).first() if supp_id else Supplier.objects.first()
                seed = Seed.objects.filter(id=seed_id).first() if seed_id else Seed.objects.first()

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

                customer = Customer.objects.filter(id=cust_id).first() if cust_id else Customer.objects.first()
                seed = Seed.objects.filter(id=seed_id).first() if seed_id else Seed.objects.first()

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
                party_name = draft.get('party_name') or 'Party'
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
                    remarks=f"Party: {party_name} | Seed: {seed_name} (Via Voice Assistant)",
                    created_by=user
                )

                return gp.pass_number, None

            # 4. TRADING SALES
            elif doc_type == 'TRADING_SALES':
                tot = Decimal(str(draft.get('total_amount', 0)))
                inv = TradingSalesInvoice.objects.create(
                    date=today,
                    customer_name=draft.get('party_name') or 'Trading Customer',
                    total_amount=tot,
                    paid_amount=tot,
                    remarks='Created via AI Voice Assistant',
                    created_by=user
                )
                return inv.invoice_number, None

            # 5. TRADING PURCHASE
            elif doc_type == 'TRADING_PURCHASE':
                tot = Decimal(str(draft.get('total_amount', 0)))
                inv = TradingPurchaseInvoice.objects.create(
                    date=today,
                    supplier_name=draft.get('party_name') or 'Trading Supplier',
                    total_amount=tot,
                    paid_amount=tot,
                    remarks='Created via AI Voice Assistant',
                    created_by=user
                )
                return inv.invoice_number, None

            # 6. TRADING GATEPASS
            elif doc_type == 'TRADING_GATEPASS':
                gp = TradingGatePass.objects.create(
                    pass_type='Inward',
                    date=today,
                    vehicle_no=draft.get('vehicle_no') or 'LES-5566',
                    party_name=draft.get('party_name') or 'Party',
                    seed_item=draft.get('seed_name') or 'Seed Lot',
                    bags_qty=draft.get('quantity', 0),
                    gross_weight=Decimal(str(draft.get('quantity', 0) * 50)),
                    created_by=user
                )
                return gp.pass_number, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, str(e)

    return None, "Unknown Document Type"
