"""Publish an existing saved revision without implicitly granting edit rights."""

import uuid
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from content.models import InstitutionalPage
from . import services
from .capabilities import enforce
from .member_views import context, localized


@services.command("content.publish")
def publish_saved(*, actor, page_id, revision_id, reason):
    page = InstitutionalPage.objects.select_for_update().get(pk=page_id)
    if page.latest_revision_id != revision_id or not reason.strip():
        raise ValidationError("Saved revision changed; reload before publication")
    revision = page.latest_revision
    candidate = revision.as_object()
    if (
        candidate.go_live_at
        or candidate.expire_at
        or (
            page.current_workflow_state
            and page.current_workflow_state.status == "in_progress"
        )
    ):
        raise ValidationError("Scheduling and workflows require the primary director")
    revision.publish(user=actor)
    services.audit(actor, "content.published", page.pk, reason, revision=revision.pk)
    return {"page": page.pk, "revision": revision.pk}


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET"])
@localized
def listing(request):
    enforce(request, "content.view")
    data = context(request)
    data["pages"] = InstitutionalPage.objects.select_related("locale").order_by("-pk")[
        :100
    ]
    return render(request, "governance/content_operations.html", data)


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def publish(request, page_id):
    enforce(request, "content.publish")
    page = get_object_or_404(InstitutionalPage, pk=page_id)
    data = context(request)

    class PublicationForm(forms.Form):
        key = forms.UUIDField(widget=forms.HiddenInput)
        revision_id = forms.IntegerField(widget=forms.HiddenInput)
        reason = forms.CharField(max_length=3000, label=data["labels"]["reason"])
        confirm = forms.BooleanField(label=data["labels"]["publish_confirm"])

    form = PublicationForm(
        request.POST if request.method == "POST" else None,
        initial={"key": uuid.uuid4(), "revision_id": page.latest_revision_id},
    )
    status = 200
    if request.method == "POST":
        if form.is_valid():
            from django.core.exceptions import PermissionDenied

            try:
                values = form.cleaned_data
                publish_saved(
                    request,
                    key=str(values["key"]),
                    page_id=page.pk,
                    revision_id=values["revision_id"],
                    reason=values["reason"],
                )
                return redirect("delegated_content")
            except PermissionDenied:
                form.add_error(None, data["labels"]["reauth"])
                status = 403
            except ValidationError:
                form.add_error(None, data["labels"]["error"])
                status = 400
        else:
            status = 400
    data.update(page=page, form=form)
    return render(request, "governance/content_publish.html", data, status=status)
