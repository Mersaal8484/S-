from django.utils import translation
from django.conf import settings

def language_context(request):
    lang = getattr(request, 'session', {}).get('django_language', 'ar')
    if not lang:
        lang = 'ar'
    return {
        'LANGUAGE_CODE': lang,
        'LANGUAGE_NAME': 'العربية' if lang == 'ar' else 'English'
    }