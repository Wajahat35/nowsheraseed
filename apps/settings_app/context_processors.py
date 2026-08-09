from .models import CompanyProfile

def company_context(request):
    try:
        company = CompanyProfile.get_instance()
    except Exception:
        company = None
    return {'company': company}
