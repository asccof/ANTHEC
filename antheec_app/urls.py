from django.conf.urls.i18n import i18n_patterns
from django.http import JsonResponse
from django.urls import include, path
from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls


def health(request):
    return JsonResponse({"project": "ANTHEEC", "mode": "development", "status": "ok"})


urlpatterns = [path("health/", health), path("admin/", include(wagtailadmin_urls))]
# No public document/media serving route and no public administrative API.
urlpatterns += i18n_patterns(path("", include(wagtail_urls)), prefix_default_language=True)
