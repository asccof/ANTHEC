from django.urls import reverse
from django.utils.functional import lazy
from django.utils.translation import get_language
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from .institutional_labels import vocabulary


@hooks.register("register_admin_menu_item")
def institutional_menu():
    label = lazy(lambda: vocabulary(get_language().split("-")[0])[1]["title"], str)()
    return MenuItem(
        label, reverse("institutional_register"), icon_name="user", order=900
    )


@hooks.register("register_admin_menu_item")
def membership_menu():
    from .member_labels import vocabulary as labels

    label = lazy(
        lambda: labels(get_language().split("-")[0])[1]["administration"], str
    )()
    return MenuItem(
        label, reverse("membership_admin_register"), icon_name="group", order=910
    )


@hooks.register("register_admin_menu_item")
def return_to_website_menu():
    # Wagtail caches menu items; resolve locale when the item is rendered.
    def locale():
        language = get_language().split("-")[0]
        return language if language in {"ar", "fr", "en"} else "ar"

    label = lazy(lambda: {
        "ar": "العودة إلى واجهة الموقع",
        "fr": "Retour au site",
        "en": "Return to website",
    }[locale()], str)()
    url = lazy(lambda: "/" + locale() + "/", str)()
    return MenuItem(label, url, icon_name="home", order=100)


@hooks.register("register_admin_menu_item")
def partnership_menu():
    from .partner_labels import vocabulary as partner_vocabulary
    label=lazy(lambda: partner_vocabulary(get_language().split("-")[0])[1]["administration"], str)()
    return MenuItem(label, reverse("partnership_register"), icon_name="group", order=920)


@hooks.register("register_admin_menu_item")
def accreditation_menu():
    from .accreditation_labels import vocabulary as case_vocabulary
    label = lazy(lambda: case_vocabulary(get_language().split("-")[0])[1]["title"], str)()
    return MenuItem(label, reverse("accreditation_register"), icon_name="doc-full", order=930)


@hooks.register("register_admin_menu_item")
def activity_menu():
    from .activity_labels import vocabulary as activity_vocabulary
    label=lazy(lambda:activity_vocabulary(get_language().split("-")[0])[1]["administration"],str)()
    return MenuItem(label,reverse("activity_admin_register"),icon_name="date",order=940)


class PrimaryDirectorMenuItem(MenuItem):
    def is_shown(self, request):
        from .models import Authority
        return request.user.is_authenticated and Authority.objects.filter(pk=1, primary_id=request.user.pk).exists()

@hooks.register("register_admin_menu_item")
def director_menu():
    from .operations_labels import vocabulary as operations_vocabulary
    label = lazy(lambda: operations_vocabulary(get_language().split("-")[0])[1]["directors"], str)()
    return PrimaryDirectorMenuItem(label, reverse("director_register"), icon_name="group", order=950)

@hooks.register("register_admin_menu_item")
def pricing_menu():
    from .operations_labels import vocabulary as operations_vocabulary
    label = lazy(lambda: operations_vocabulary(get_language().split("-")[0])[1]["pricing"], str)()
    return MenuItem(label, reverse("pricing_register"), icon_name="list-ul", order=960)


@hooks.register('construct_page_action_menu')
def scoped_page_actions(menu_items, request, context):
    from .models import Authority
    from .capabilities import allows
    if Authority.objects.filter(pk=1, primary=request.user).exists(): return
    editing = 'content.create' if context.get('view') == 'create' else 'content.edit'
    needed = {'action-save-draft': (editing,), 'action-publish': (editing, 'content.publish'),
              'action-unpublish': ('content.unpublish',)}
    menu_items[:] = [item for item in menu_items if getattr(item, 'name', None) in needed
                     and all(allows(request, key) for key in needed[item.name])]


@hooks.register('construct_main_menu')
def scoped_admin_menu(request, menu_items):
    from .models import Authority
    from .capabilities import allows
    if Authority.objects.filter(pk=1, primary=request.user).exists(): return
    by_url = {reverse('institutional_register'): 'institutional.view',
              reverse('membership_admin_register'): 'membership.view',
              reverse('partnership_register'): 'partner.view',
              reverse('accreditation_register'): 'accreditation.view',
              reverse('activity_admin_register'): 'activity.view',
              reverse('pricing_register'): 'pricing.view'}
    by_name = {'explorer': 'content.view', 'images': 'media_image.view',
               'documents': 'media_document.view', 'settings': 'contact.view'}
    menu_items[:] = [item for item in menu_items
                     if str(getattr(item, 'url', '')).startswith(('/ar/', '/fr/', '/en/'))
                     or allows(request, by_url.get(str(getattr(item, 'url', '')), by_name.get(getattr(item, 'name', ''), '')))]
