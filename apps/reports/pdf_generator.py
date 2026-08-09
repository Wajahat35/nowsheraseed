import io
import os
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from apps.settings_app.models import CompanyProfile

def render_to_pdf(filename, title, data_headers, data_rows):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []

    styles = getSampleStyleSheet()
    
    # Try adding logo if available
    try:
        company = CompanyProfile.get_instance()
        logo_path = None
        if company.logo and os.path.exists(company.logo.path):
            logo_path = company.logo.path
        elif os.path.exists('static/icon.png'):
            logo_path = 'static/icon.png'
            
        if logo_path:
            img = Image(logo_path, width=45, height=45)
            story.append(img)
            story.append(Spacer(1, 5))
    except Exception:
        pass

    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=15,
        alignment=1
    )

    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 10))

    table_data = [data_headers] + data_rows
    t = Table(table_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))

    story.append(t)
    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response
