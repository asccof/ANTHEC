"""Scoped Wagtail adapter. Unknown admin endpoints are primary-only."""

from django.core.exceptions import PermissionDenied
from .capabilities import enforce


def synchronize_cms_group(user, row):
    from django.contrib.auth.models import Group, Permission
    from wagtail.models import (
        GroupPagePermission,
        GroupCollectionPermission,
        Page,
        Collection,
    )

    group, _ = Group.objects.get_or_create(name=f"ANTHEC scoped delegate {row.pk}")
    user.groups.remove(*Group.objects.filter(name="ANTHEEC operational directors"))
    group.permissions.clear()
    GroupPagePermission.objects.filter(group=group).delete()
    GroupCollectionPermission.objects.filter(group=group).delete()
    if not row.active:
        user.groups.remove(group)
        return
    user.groups.add(group)
    group.permissions.add(
        Permission.objects.get(
            content_type__app_label="wagtailadmin", codename="access_admin"
        )
    )
    scopes = set(row.capabilities)
    page_actions = {
        "create": "add_page",
        "edit": "change_page",
        "publish": "publish_page",
        "unpublish": "publish_page",
        "lock": "lock_page",
        "unlock": "unlock_page",
        "delete": "delete_page",
        "view": "change_page",
    }
    for action, codename in page_actions.items():
        if f"content.{action}" in scopes:
            permission = Permission.objects.get(
                content_type__app_label="wagtailcore", codename=codename
            )
            GroupPagePermission.objects.get_or_create(
                group=group, page=Page.get_first_root_node(), permission=permission
            )
    for scope, app, model in (
        ("media_image", "wagtailimages", "image"),
        ("media_document", "wagtaildocs", "document"),
    ):
        for action, codename in {
            "view": f"change_{model}",
            "upload": f"add_{model}",
            "edit": f"change_{model}",
            "delete": f"delete_{model}",
        }.items():
            if f"{scope}.{action}" in scopes:
                permission = Permission.objects.get(
                    content_type__app_label=app, codename=codename
                )
                GroupCollectionPermission.objects.get_or_create(
                    group=group,
                    collection=Collection.get_first_root_node(),
                    permission=permission,
                )
    if "contact.view" in scopes:
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="content", codename="change_publiccontact"
            )
        )


def check_admin_route(request, match):
    """Allowlist resolved names, then exact mutation. Never trust Django groups alone."""
    name = match.view_name
    write = request.method not in {"GET", "HEAD", "OPTIONS"}
    required = None
    if name in {
        "wagtailadmin_home",
        "wagtailadmin_login",
        "wagtailadmin_logout",
        "wagtailadmin_javascript_catalog",
        "wagtailadmin_sprite",
    }:
        required = ()
    elif name in {
        "wagtailadmin_explore_root",
        "wagtailadmin_explore",
        "wagtailadmin_explore_results",
    }:
        if not write:
            required = ("content.view",)
    elif name.startswith("wagtailadmin_pages:"):
        action = name.split(":")[-1]
        reads = {
            "edit",
            "add",
            "add_subpage",
            "choose_parent",
            "search",
            "search_results",
            "usage",
            "type_use",
            "type_use_results",
            "view_draft",
            "revisions_index",
            "revisions_view",
            "revisions_compare",
            "history",
            "history_results",
            "unpublish",
            "delete",
            "lock",
            "unlock",
        }
        mutations = {
            "add": "create",
            "edit": "edit",
            "unpublish": "unpublish",
            "delete": "delete",
            "lock": "lock",
            "unlock": "unlock",
        }
        if not write and action in reads:
            required = ("content.view",)
        if write and action in mutations:
            required = ["content.view", "content." + mutations[action]]
            if any(
                key.startswith("action-")
                and key not in {"action-publish", "action-save", "action-save-draft"}
                for key in request.POST
            ):
                raise PermissionDenied("Unknown publishing action")
            # Workflows, aliases, moving/copying, scheduling and revision reverts
            # are not silently folded into edit/publish rights.
            if any(
                k.startswith("workflow-")
                or k
                in {
                    "action-submit",
                    "action-restart-workflow",
                    "action-cancel-workflow",
                }
                for k in request.POST
            ):
                raise PermissionDenied("Workflow management is primary-only")
            if action == "edit":
                from wagtail.models import Page

                page = Page.objects.get(pk=match.kwargs["page_id"])
                if (
                    page.go_live_at
                    or page.expire_at
                    or (
                        page.current_workflow_state
                        and page.current_workflow_state.status == "in_progress"
                    )
                ):
                    raise PermissionDenied(
                        "Active schedules and workflows are primary-only"
                    )
            if request.POST.get("go_live_at") or request.POST.get("expire_at"):
                raise PermissionDenied("Scheduled publishing is primary-only")
            if request.POST.get("action-publish"):
                required.append("content.publish")
        if action in {"preview_on_edit", "preview_on_add"}:
            required = [
                "content.view",
                "content.edit" if action == "preview_on_edit" else "content.create",
            ]
    elif (
        name.startswith("wagtailadmin_api:")
        and not write
        and name.split(":")[-1] in {"listing", "detail", "find"}
    ):
        domain = {
            "pages": "content",
            "images": "media_image",
            "documents": "media_document",
        }.get(name.split(":")[1])
        if domain:
            required = [domain + ".view"]
    elif (
        name == "wagtailsettings:edit"
        and match.kwargs.get("app_name") == "content"
        and match.kwargs.get("model_name") == "publiccontact"
    ):
        required = ["contact.view"] + (["contact.edit"] if write else [])
    else:
        for namespace, scope in (
            ("wagtailimages", "media_image"),
            ("wagtaildocs", "media_document"),
        ):
            if name.startswith(namespace + ":"):
                action = name.split(":")[-1]
                reads = {
                    "index",
                    "index_results",
                    "edit",
                    "image_usage",
                    "document_usage",
                    "delete",
                    "preview",
                }
                mutations = {"add": "upload", "edit": "edit", "delete": "delete"}
                if not write and action in reads | {"add"}:
                    required = [scope + ".view"]
                if write and action in mutations:
                    required = [scope + ".view", scope + "." + mutations[action]]
            if name.startswith(namespace + "_chooser:"):
                action = name.split(":")[-1]
                if not write and action in {
                    "choose",
                    "choose_results",
                    "chosen",
                    "chosen_multiple",
                    "select_format",
                }:
                    required = [scope + ".view"]
    if required is None:
        raise PermissionDenied("This admin route is not delegated")
    enforce(request, *required, recent=write)
