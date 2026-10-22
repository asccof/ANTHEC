from django.http import Http404
from django.utils.translation import get_language
from wagtail import hooks


@hooks.register("before_serve_page")
def require_published_requested_locale(page, request, *args, **kwargs):
    # Wagtail otherwise falls back to the source root when a translation is absent.
    # Never serve AR content under a FR/EN URL after unpublication.
    if page.locale.language_code != get_language():
        raise Http404("No published content in the requested language.")


# This directory contains approved public names and never grants administrative roles.
# Keep mutations primary-only, independently of Django superuser/snippet permissions.
from wagtail.permission_policies.base import BasePermissionPolicy
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail.snippets.models import register_snippet
from .models import PublicLeader


class LeadershipPermissionPolicy(BasePermissionPolicy):
    def user_has_permission(self, user, action):
        from governance.models import Authority
        return bool(user.is_authenticated and user.is_active and user.is_staff
                    and Authority.objects.filter(pk=1, primary=user).exists())

    def user_has_any_permission(self, user, actions):
        return bool(actions) and self.user_has_permission(user, "change")

    def users_with_any_permission(self, actions):
        from django.contrib.auth import get_user_model
        from governance.models import Authority
        users = get_user_model().objects.filter(is_active=True, is_staff=True,
            pk__in=Authority.objects.filter(pk=1).values("primary_id"))
        return users if actions else users.none()


class LeadershipViewSet(SnippetViewSet):
    model = PublicLeader
    icon = "group"
    from django.utils.functional import lazy
    menu_label = lazy(lambda: {"ar": "هيكلة الجمعية", "fr": "Gouvernance de l’association", "en": "Association leadership"}.get(get_language().split("-")[0], "Association leadership"), str)()
    menu_name = "public_leadership"
    add_to_admin_menu = True
    menu_order = 205
    list_display = ("name_ar", "name_latin", "role", "published", "sort_order")
    list_filter = ("role", "published", "founder")
    search_fields = ("name_ar", "name_latin")

    @property
    def permission_policy(self):
        return LeadershipPermissionPolicy(self.model)


register_snippet(LeadershipViewSet)
