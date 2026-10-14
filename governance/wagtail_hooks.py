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
