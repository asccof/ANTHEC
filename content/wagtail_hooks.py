from django.http import Http404
from django.utils.translation import get_language
from wagtail import hooks


@hooks.register("before_serve_page")
def require_published_requested_locale(page, request, *args, **kwargs):
    # Wagtail otherwise falls back to the source root when a translation is absent.
    # Never serve AR content under a FR/EN URL after unpublication.
    if page.locale.language_code != get_language():
        raise Http404("No published content in the requested language.")
