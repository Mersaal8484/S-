from django.http import HttpResponseRedirect
from django.utils import translation
from django.urls import reverse

def set_language(request, lang):
    translation.activate(lang)
    request.session['django_language'] = lang
    
    if 'HTTP_REFERER' in request.META:
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    return HttpResponseRedirect(reverse('billing_index'))