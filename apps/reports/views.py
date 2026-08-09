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
            headers = ['Code', 'Supplier Name', 'Company Name', 'Phone', 'City', 'Payable Balance (PKR)']
            rows = [[s.code, s.name, s.company_name or "-", s.phone, s.city, f"PKR {s.get_current_balance()}"] for s in suppliers]
            return render_to_pdf("supplier_report.pdf", "Supplier Payables Summary Report", headers, rows)
        elif export_fmt == 'excel':
            headers = ['Code', 'Supplier Name', 'Company Name', 'Phone', 'City', 'Payable Balance']
            rows = [[s.code, s.name, s.company_name or "", s.phone, s.city, float(s.get_current_balance())] for s in suppliers]
            return render_to_excel("supplier_report.xlsx", "SupplierSummary", headers, rows)

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
