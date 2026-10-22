from django.http import Http404
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from .privacy_notice import enabled, snapshot, WORDS
from .public_presentation import labels


@never_cache
@require_safe
def notice(request):
    if not enabled():
        raise Http404
    language = request.GET.get('lang', 'ar')
    language = language if language in WORDS else 'ar'
    return render(request, 'governance/privacy_notice.html', {
        'language': language, 'direction': 'rtl' if language == 'ar' else 'ltr',
        'public_labels': labels(language), 'notice': snapshot(language),
    })
