from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.utils.dateparse import parse_date
from apps.sales.models import SalesInvoice
from apps.purchases.models import PurchaseInvoice
from apps.seeds.models import Seed, SeedBatch
from apps.customers.models import Customer
from apps.suppliers.models import Supplier
from apps.gatepass.models import GatePass
from apps.expenses.models import Expense
from .pdf_generator import render_to_pdf
from .excel_generator import render_to_excel

class ReportsDashboardView(LoginRequiredMixin, View):
    template_name = 'reports/reports_dashboard.html'

    def get(self, request):
        return render(request, self.template_name)

class SalesReportView(LoginRequiredMixin, View):
    template_name = 'reports/sales_report.html'

    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        qs = SalesInvoice.objects.select_related('customer').all()

        if start_date:
            s_date = parse_date(start_date)
            if s_date:
                qs = qs.filter(date__gte=s_date)

        if end_date:
            e_date = parse_date(end_date)
            if e_date:
                qs = qs.filter(date__lte=e_date)

        invoices = qs.order_by('-date')

        export_fmt = request.GET.get('export')
        if export_fmt == 'pdf':
            headers = ['Invoice #', 'Customer', 'Date', 'Type', 'Grand Total (PKR)', 'Paid (PKR)', 'Status']
            rows = [[i.invoice_number, i.customer.name, str(i.date), i.sales_type, f"PKR {i.grand_total}", f"PKR {i.paid_amount}", i.payment_status] for i in invoices]
            return render_to_pdf("sales_report.pdf", "Date-Wise Sales Report", headers, rows)
        elif export_fmt == 'excel':
            headers = ['Invoice #', 'Customer', 'Date', 'Type', 'Grand Total', 'Paid Amount', 'Status']
            rows = [[i.invoice_number, i.customer.name, str(i.date), i.sales_type, float(i.grand_total), float(i.paid_amount), i.payment_status] for i in invoices]
            return render_to_excel("sales_report.xlsx", "SalesReport", headers, rows)

        return render(request, self.template_name, {
            'invoices': invoices,
            'start_date': start_date,
            'end_date': end_date
        })

class PurchaseReportView(LoginRequiredMixin, View):
    template_name = 'reports/purchase_report.html'

    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        qs = PurchaseInvoice.objects.select_related('supplier').all()

        if start_date:
            s_date = parse_date(start_date)
            if s_date:
                qs = qs.filter(date__gte=s_date)

        if end_date:
            e_date = parse_date(end_date)
            if e_date:
                qs = qs.filter(date__lte=e_date)

        invoices = qs.order_by('-date')

        export_fmt = request.GET.get('export')
        if export_fmt == 'pdf':
            headers = ['Bill #', 'Supplier', 'Date', 'Grand Total (PKR)', 'Paid (PKR)', 'Status']
            rows = [[i.invoice_number, i.supplier.name, str(i.date), f"PKR {i.grand_total}", f"PKR {i.paid_amount}", i.payment_status] for i in invoices]
            return render_to_pdf("purchase_report.pdf", "Date-Wise Purchase Procurement Report", headers, rows)
        elif export_fmt == 'excel':
            headers = ['Bill #', 'Supplier', 'Date', 'Grand Total', 'Paid Amount', 'Status']
            rows = [[i.invoice_number, i.supplier.name, str(i.date), float(i.grand_total), float(i.paid_amount), i.payment_status] for i in invoices]
            return render_to_excel("purchase_report.xlsx", "PurchaseReport", headers, rows)

        return render(request, self.template_name, {
            'invoices': invoices,
            'start_date': start_date,
            'end_date': end_date
        })

class CustomerReportView(LoginRequiredMixin, View):
    template_name = 'reports/customer_report.html'

    def get(self, request):
        customers = Customer.objects.all().order_by('name')

        export_fmt = request.GET.get('export')
        if export_fmt == 'pdf':
            headers = ['Code', 'Customer Name', 'Phone', 'City', 'Credit Limit (PKR)', 'Current Balance (PKR)']
            rows = [[c.code, c.name, c.phone, c.city, f"PKR {c.debit_limit}", f"PKR {c.get_current_balance()}"] for c in customers]
            return render_to_pdf("customer_report.pdf", "Customer Ledger & Receivables Summary", headers, rows)
        elif export_fmt == 'excel':
            headers = ['Code', 'Customer Name', 'Company Name', 'Phone', 'City', 'Credit Limit', 'Current Balance']
            rows = [[c.code, c.name, c.company_name or "", c.phone, c.city, float(c.debit_limit), float(c.get_current_balance())] for c in customers]
            return render_to_excel("customer_report.xlsx", "CustomerSummary", headers, rows)

        return render(request, self.template_name, {'customers': customers})

class SupplierReportView(LoginRequiredMixin, View):
    template_name = 'reports/supplier_report.html'

    def get(self, request):
        suppliers = Supplier.objects.all().order_by('name')

        export_fmt = request.GET.get('export')
        if export_fmt == 'pdf':
            headers = ['Code', 'Grower Name', 'Farm / Company Name', 'Phone', 'City', 'Payable Balance (PKR)']
            rows = [[s.code, s.name, s.company_name or "-", s.phone, s.city, f"PKR {s.get_current_balance()}"] for s in suppliers]
            return render_to_pdf("grower_report.pdf", "Grower Payables & Intake Audit Report", headers, rows)
        elif export_fmt == 'excel':
            headers = ['Code', 'Grower Name', 'Farm / Company Name', 'Phone', 'City', 'Payable Balance']
            rows = [[s.code, s.name, s.company_name or "", s.phone, s.city, float(s.get_current_balance())] for s in suppliers]
            return render_to_excel("grower_report.xlsx", "GrowerSummary", headers, rows)

        return render(request, self.template_name, {'suppliers': suppliers})

class SeedReportView(LoginRequiredMixin, View):
    template_name = 'reports/seed_report.html'

    def get(self, request):
        seeds = Seed.objects.select_related('crop_type', 'category', 'brand').all().order_by('name')

        export_fmt = request.GET.get('export')
        if export_fmt == 'pdf':
            headers = ['Code', 'Seed Name', 'Variety', 'Crop Type', 'Packing Size', 'Retail Price (PKR)', 'Stock On Hand']
            rows = [[s.code, s.name, s.variety, s.crop_type.name if s.crop_type else "-", s.packing_size, f"PKR {s.retail_price}", str(s.get_total_stock())] for s in seeds]
            return render_to_pdf("seed_catalog_report.pdf", "Seed Catalog Directory Report", headers, rows)
        elif export_fmt == 'excel':
            headers = ['Code', 'Seed Name', 'Variety', 'Crop Type', 'Category', 'Brand', 'Packing Size', 'Purchase Price', 'Retail Price', 'Stock On Hand']
            rows = [[s.code, s.name, s.variety, s.crop_type.name if s.crop_type else "", s.category.name if s.category else "", s.brand.name if s.brand else "", s.packing_size, float(s.purchase_price), float(s.retail_price), s.get_total_stock()] for s in seeds]
            return render_to_excel("seed_catalog_report.xlsx", "SeedCatalog", headers, rows)

        return render(request, self.template_name, {'seeds': seeds})

class StockReportView(LoginRequiredMixin, View):
    template_name = 'reports/stock_report.html'

    def get(self, request):
        seeds = Seed.objects.prefetch_related('batches').all()
        
        export_fmt = request.GET.get('export')
        if export_fmt == 'pdf':
            headers = ['Code', 'Seed Name', 'Variety', 'Available Stock', 'Retail Price', 'Status']
            rows = [[s.code, s.name, s.variety, str(s.get_total_stock()), f"PKR {s.retail_price}", s.status] for s in seeds]
            return render_to_pdf("stock_report.pdf", "Inventory Stock Audit Report", headers, rows)
        elif export_fmt == 'excel':
            headers = ['Code', 'Seed Name', 'Variety', 'Total Stock', 'Retail Price', 'Purchase Price', 'Status']
            rows = [[s.code, s.name, s.variety, s.get_total_stock(), float(s.retail_price), float(s.purchase_price), s.status] for s in seeds]
            return render_to_excel("stock_report.xlsx", "StockReport", headers, rows)

        return render(request, self.template_name, {'seeds': seeds})

class LowStockReportView(LoginRequiredMixin, View):
    template_name = 'reports/low_stock_report.html'

    def get(self, request):
        all_seeds = Seed.objects.prefetch_related('batches').all()
        low_stock_seeds = [s for s in all_seeds if s.get_total_stock() <= s.min_stock_alert]
        return render(request, self.template_name, {'seeds': low_stock_seeds})

class ExpiredStockReportView(LoginRequiredMixin, View):
    template_name = 'reports/expired_stock_report.html'

    def get(self, request):
        batches = SeedBatch.objects.select_related('seed').all()
        expired_batches = [b for b in batches if b.is_expired()]
        return render(request, self.template_name, {'batches': expired_batches})


class ProcessingRecoveryReportView(LoginRequiredMixin, View):
    template_name = 'reports/processing_recovery_report.html'

    def get(self, request):
        from decimal import Decimal
        from apps.inventory.models import SeedProcessing
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        qs = SeedProcessing.objects.select_related('grower', 'seed', 'wastage_type').all()
        if start_date:
            s_d = parse_date(start_date)
            if s_d:
                qs = qs.filter(date__gte=s_d)
        if end_date:
            e_d = parse_date(end_date)
            if e_d:
                qs = qs.filter(date__lte=e_d)

        runs = qs.order_by('-date', '-id')

        # Totals
        tot_raw = sum((r.raw_input_kg for r in runs), Decimal('0.00'))
        tot_clean = sum((r.clean_seed_kg for r in runs), Decimal('0.00'))
        tot_wst = sum((r.wastage_kg for r in runs), Decimal('0.00'))
        avg_recovery = (tot_clean / tot_raw * 100) if tot_raw > 0 else Decimal('0.00')

        export_fmt = request.GET.get('export')
        if export_fmt == 'excel':
            headers = ['Batch #', 'Date', 'Grower', 'Seed Variety', 'Raw Input (KG)', 'Usable Seed Recovered (KG)', 'Wastage Generated (KG)', 'Dust/Moisture Loss (KG)', 'Recovery %', 'Wastage %']
            rows = [
                [
                    r.batch_number,
                    str(r.date),
                    r.grower.name if r.grower else 'N/A',
                    r.seed.name if r.seed else 'N/A',
                    float(r.raw_input_kg),
                    float(r.clean_seed_kg),
                    float(r.wastage_kg),
                    float(r.moisture_dust_loss_kg),
                    float(r.recovery_rate),
                    float(r.wastage_rate),
                ]
                for r in runs
            ]
            return render_to_excel("processing_recovery_report.xlsx", "ProcessingRecovery", headers, rows)
        elif export_fmt == 'pdf':
            headers = ['Batch #', 'Date', 'Grower', 'Seed', 'Raw Input KG', 'Usable Seed KG', 'Wastage KG', 'Recovery %', 'Wastage %']
            rows = [
                [
                    r.batch_number,
                    str(r.date),
                    r.grower.name[:16] if r.grower else 'N/A',
                    r.seed.name[:15] if r.seed else 'N/A',
                    f"{r.raw_input_kg:,.1f}",
                    f"{r.clean_seed_kg:,.1f}",
                    f"{r.wastage_kg:,.1f}",
                    f"{r.recovery_rate}%",
                    f"{r.wastage_rate}%",
                ]
                for r in runs
            ]
            return render_to_pdf("processing_recovery_report.pdf", "Seed Processing & Recovery Audit Report", headers, rows)

        context = {
            'runs': runs,
            'tot_raw': tot_raw,
            'tot_clean': tot_clean,
            'tot_wst': tot_wst,
            'avg_recovery': avg_recovery,
            'start_date': start_date or '',
            'end_date': end_date or '',
        }
        return render(request, self.template_name, context)


class SeedInventoryPackagingReportView(LoginRequiredMixin, View):
    template_name = 'reports/seed_inventory_packaging_report.html'

    def get(self, request):
        from decimal import Decimal
        seeds = Seed.objects.prefetch_related('batches').all().order_by('name')

        report_rows = []
        tot_all_kg = Decimal('0.00')
        tot_all_bags = 0

        for s in seeds:
            kg = s.get_total_stock_kg()
            bags = s.get_total_available_bags()
            pack_wgt = Decimal(str(s.weight_kg or 50.0))
            loose_kg = kg % pack_wgt if pack_wgt > Decimal('0') else Decimal('0')

            tot_all_kg += kg
            tot_all_bags += bags

            report_rows.append({
                'seed': s,
                'total_kg': kg,
                'pack_wgt': pack_wgt,
                'available_bags': bags,
                'loose_kg': loose_kg,
                'dual_display': s.stock_dual_display(),
            })

        export_fmt = request.GET.get('export')
        if export_fmt == 'excel':
            headers = ['Code', 'Seed Variety', 'Pack Size (KG/Bag)', 'Total Clean Stock (KG)', 'Available Packaged Bags', 'Loose Weight (KG)']
            rows = [
                [
                    r['seed'].code,
                    r['seed'].name,
                    float(r['pack_wgt']),
                    float(r['total_kg']),
                    r['available_bags'],
                    float(r['loose_kg']),
                ]
                for r in report_rows
            ]
            return render_to_excel("seed_inventory_packaging_report.xlsx", "SeedPackaging", headers, rows)
        elif export_fmt == 'pdf':
            headers = ['Code', 'Seed Variety', 'Pack Size', 'Total Stock KG', 'Available Bags', 'Loose KG']
            rows = [
                [
                    r['seed'].code,
                    r['seed'].name[:20],
                    f"{r['pack_wgt']:g} KG",
                    f"{r['total_kg']:,.1f}",
                    str(r['available_bags']),
                    f"{r['loose_kg']:,.1f}",
                ]
                for r in report_rows
            ]
            return render_to_pdf("seed_inventory_packaging_report.pdf", "Seed Inventory & Packaging Potential Report", headers, rows)

        context = {
            'report_rows': report_rows,
            'tot_all_kg': tot_all_kg,
            'tot_all_bags': tot_all_bags,
        }
        return render(request, self.template_name, context)


class WastageStockMovementReportView(LoginRequiredMixin, View):
    template_name = 'reports/wastage_stock_report.html'

    def get(self, request):
        from decimal import Decimal
        from apps.wastage.models import WastageType, WastageStock, WastageMovement

        types = WastageType.objects.prefetch_related('stock', 'movements').all().order_by('name')

        report_data = []
        grand_inward = Decimal('0.00')
        grand_sold = Decimal('0.00')
        grand_balance = Decimal('0.00')

        for t in types:
            stock = t.stock.current_stock_kg if hasattr(t, 'stock') else Decimal('0.00')
            movements = t.movements.all()

            inward_processing = sum(
                (m.quantity_kg for m in movements if m.movement_type == 'INTAKE_PROCESSING'),
                Decimal('0.00')
            )
            sold_dispatch = abs(sum(
                (m.quantity_kg for m in movements if m.movement_type == 'SALES_DISPATCH'),
                Decimal('0.00')
            ))
            adjustments = sum(
                (m.quantity_kg for m in movements if m.movement_type in ('ADJUSTMENT', 'RETURN')),
                Decimal('0.00')
            )

            # Opening stock derived: balance - inward + sold - adjustments
            derived_opening = max(Decimal('0.00'), stock - inward_processing + sold_dispatch - adjustments)

            grand_inward += inward_processing
            grand_sold += sold_dispatch
            grand_balance += stock

            report_data.append({
                'type': t,
                'opening_kg': derived_opening,
                'inward_kg': inward_processing,
                'sold_kg': sold_dispatch,
                'balance_kg': stock,
                'rate_per_kg': t.price_per_kg,
                'stock_value': stock * t.price_per_kg,
            })

        export_fmt = request.GET.get('export')
        if export_fmt == 'excel':
            headers = ['Wastage Grade', 'Opening Stock (KG)', 'Generated from Processing (KG)', 'Sold Wastage (KG)', 'Current Balance (KG)', 'Rate / KG (PKR)', 'Valuation (PKR)']
            rows = [
                [
                    d['type'].name,
                    float(d['opening_kg']),
                    float(d['inward_kg']),
                    float(d['sold_kg']),
                    float(d['balance_kg']),
                    float(d['rate_per_kg']),
                    float(d['stock_value']),
                ]
                for d in report_data
            ]
            return render_to_excel("wastage_stock_movement_report.xlsx", "WastageStock", headers, rows)
        elif export_fmt == 'pdf':
            headers = ['Grade', 'Opening KG', 'Processing KG', 'Sold KG', 'Balance KG', 'Rate/KG', 'Value (PKR)']
            rows = [
                [
                    d['type'].name[:18],
                    f"{d['opening_kg']:,.1f}",
                    f"{d['inward_kg']:,.1f}",
                    f"{d['sold_kg']:,.1f}",
                    f"{d['balance_kg']:,.1f}",
                    f"PKR {d['rate_per_kg']:,.0f}",
                    f"PKR {d['stock_value']:,.0f}",
                ]
                for d in report_data
            ]
            return render_to_pdf("wastage_stock_movement_report.pdf", "Wastage Stock & Movement Audit Report", headers, rows)

        context = {
            'report_data': report_data,
            'grand_inward': grand_inward,
            'grand_sold': grand_sold,
            'grand_balance': grand_balance,
        }
        return render(request, self.template_name, context)


class WastageSalesRevenueReportView(LoginRequiredMixin, View):
    template_name = 'reports/wastage_sales_report.html'

    def get(self, request):
        from decimal import Decimal
        from apps.wastage.models import WastageInvoice, WastageInvoiceItem

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        qs = WastageInvoice.objects.prefetch_related('items__wastage_type').all()
        if start_date:
            s_d = parse_date(start_date)
            if s_d:
                qs = qs.filter(date__gte=s_d)
        if end_date:
            e_d = parse_date(end_date)
            if e_d:
                qs = qs.filter(date__lte=e_d)

        invoices = qs.order_by('-date', '-id')

        total_kg_sold = sum((inv.total_weight_kg for inv in invoices), Decimal('0.00'))
        total_revenue = sum((inv.grand_total for inv in invoices), Decimal('0.00'))
        total_collected = sum((inv.paid_amount for inv in invoices), Decimal('0.00'))
        total_receivables = max(Decimal('0.00'), total_revenue - total_collected)
        avg_rate_per_kg = (total_revenue / total_kg_sold) if total_kg_sold > Decimal('0') else Decimal('0.00')

        export_fmt = request.GET.get('export')
        if export_fmt == 'excel':
            headers = ['Invoice #', 'Date', 'Buyer Name', 'Contact', 'Total KG Sold', 'Subtotal', 'Grand Total (PKR)', 'Paid (PKR)', 'Balance (PKR)', 'Status']
            rows = [
                [
                    inv.invoice_number,
                    str(inv.date),
                    inv.buyer_name,
                    inv.buyer_phone or '-',
                    float(inv.total_weight_kg),
                    float(inv.subtotal),
                    float(inv.grand_total),
                    float(inv.paid_amount),
                    float(inv.due_amount),
                    inv.payment_status
                ]
                for inv in invoices
            ]
            return render_to_excel("wastage_sales_revenue_report.xlsx", "WastageRevenue", headers, rows)
        elif export_fmt == 'pdf':
            headers = ['Invoice #', 'Date', 'Buyer', 'KG Sold', 'Revenue (PKR)', 'Collected', 'Pending Due', 'Status']
            rows = [
                [
                    inv.invoice_number,
                    str(inv.date),
                    inv.buyer_name[:18],
                    f"{inv.total_weight_kg:,.1f}",
                    f"PKR {inv.grand_total:,.0f}",
                    f"PKR {inv.paid_amount:,.0f}",
                    f"PKR {inv.due_amount:,.0f}",
                    inv.payment_status
                ]
                for inv in invoices
            ]
            return render_to_pdf("wastage_sales_revenue_report.pdf", "Wastage Sales & Revenue Summary Report", headers, rows)

        context = {
            'invoices': invoices,
            'total_kg_sold': total_kg_sold,
            'total_revenue': total_revenue,
            'total_collected': total_collected,
            'total_receivables': total_receivables,
            'avg_rate_per_kg': avg_rate_per_kg,
            'start_date': start_date or '',
            'end_date': end_date or '',
        }
        return render(request, self.template_name, context)

