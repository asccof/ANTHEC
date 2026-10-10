import base64
import uuid
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .member_views import context, localized
from .institutional_views import read_authority
from .models import Portrait
from .portrait_labels import LABELS
from . import portraits, services


def ctx(request):
    data = context(request)
    data["photo_labels"] = LABELS[data["language"]]
    return data


@never_cache
@login_required(login_url="/members/login/")
@require_http_methods(["GET", "POST"])
@localized
def upload(request):
    data = ctx(request)
    labels = data["photo_labels"]

    class UploadForm(forms.Form):
        key = forms.UUIDField(initial=uuid.uuid4, widget=forms.HiddenInput)
        person_id = forms.ModelChoiceField(
            queryset=portraits.owned_people(request.user), label=labels["person"]
        )
        photo = forms.FileField(label=labels["photo"])
        consent = forms.BooleanField(label=labels["consent"])

    form = UploadForm(
        request.POST if request.method == "POST" else None, request.FILES or None
    )
    status = 200
    if request.method == "POST":
        status = 400
        if form.is_valid():
            try:
                clean = portraits.normalize(form.cleaned_data["photo"])
                portraits.upload_portrait(
                    request.user,
                    key=str(form.cleaned_data["key"]),
                    person_id=form.cleaned_data["person_id"].pk,
                    image_data=base64.b64encode(clean).decode(),
                    consent=form.cleaned_data["consent"],
                )
                return redirect(
                    reverse("portrait_upload") + "?lang=" + data["language"]
                )
            except (ValidationError, PermissionDenied, ObjectDoesNotExist):
                form.add_error(None, labels["error"])
    data.update(
        form=form,
        portraits=Portrait.objects.filter(
            person__in=portraits.owned_people(request.user)
        ).order_by("-pk")[:20],
    )
    for photo in data["portraits"]:
        photo.state_label = labels[photo.state]
    return render(request, "governance/portrait_upload.html", data, status=status)


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def review(request):
    read_authority(request)
    data = ctx(request)
    labels = data["photo_labels"]

    class ReviewForm(forms.Form):
        key = forms.UUIDField(initial=uuid.uuid4, widget=forms.HiddenInput)
        portrait_id = forms.ModelChoiceField(
            queryset=Portrait.objects.filter(state="pending"), label=labels["photo"]
        )
        decision = forms.ChoiceField(
            choices=[(k, labels[k]) for k in ("approved", "rejected")],
            label=labels["decision"],
        )
        reason = forms.CharField(max_length=1000, label=labels["reason"])

    form = ReviewForm(request.POST if request.method == "POST" else None)
    status = 200
    if request.method == "POST":
        status = 400
        if form.is_valid():
            try:
                portraits.review_portrait(
                    request,
                    key=str(form.cleaned_data["key"]),
                    portrait_id=form.cleaned_data["portrait_id"].pk,
                    decision=form.cleaned_data["decision"],
                    reason=form.cleaned_data["reason"],
                )
                return redirect(
                    reverse("portrait_review") + "?lang=" + data["language"]
                )
            except PermissionDenied:
                form.add_error(None, labels["error"])
                status = 403
            except (ValidationError, ObjectDoesNotExist):
                form.add_error(None, labels["error"])
    data.update(
        form=form,
        portraits=Portrait.objects.filter(state="pending")
        .select_related("person")
        .order_by("pk")[:100],
    )
    return render(request, "governance/portrait_review.html", data, status=status)


@never_cache
@login_required(login_url="/members/login/")
@require_http_methods(["GET"])
def image(request, serial):
    row = get_object_or_404(Portrait, serial=serial)
    if not portraits.owned_people(request.user).filter(pk=row.person_id).exists():
        try:
            with transaction.atomic():
                services.authorize(request, recent=False)
        except (PermissionDenied, ObjectDoesNotExist):
            return HttpResponse(status=404)
    services.audit(request.user, "portrait.viewed", row.serial)
    response = HttpResponse(portraits.portrait_bytes(row), content_type="image/jpeg")
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    response["X-Content-Type-Options"] = "nosniff"
    return response
