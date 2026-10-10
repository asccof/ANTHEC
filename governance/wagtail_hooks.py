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
