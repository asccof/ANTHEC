import base64
import uuid
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError, ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .member_views import context, localized
from .models import CertificateAsset
from . import certificate_assets as assets, services as s

WORDS = {
    "ar": ["التوقيع والطابع المحميان", "نوع العنصر", "توقيع الرئيس", "طابع الجمعية", "صورة PNG أو JPEG أصلية", "سبب موثق", "رفع للمراجعة", "قرار المراجعة", "موافقة", "رفض", "حفظ القرار", "تعذر الإجراء؛ تحقق من الصلاحية والملف والحالة.", "لإدارة الجمعية الرئيسية فقط. استعمل الصور الأصلية المصرح بها؛ لا توقيع مقلد. الاستبدال لا يغيّر الوثائق الصادرة؛ يلزم إعادة إصدار رسمية.", "قيد المراجعة", "معتمد", "مرفوض"],
    "fr": ["Signature et cachet protégés", "Type", "Signature du Président", "Cachet de l’association", "Image authentique PNG ou JPEG", "Motif documenté", "Déposer pour révision", "Décision", "Approuver", "Rejeter", "Enregistrer", "Action impossible : vérifiez autorisation, fichier et état.", "Administration principale uniquement. Images authentiques autorisées, sans imitation. Le remplacement ne modifie pas les documents émis ; réémission formelle requise.", "En attente", "Approuvé", "Rejeté"],
    "en": ["Protected signature and stamp", "Type", "President’s signature", "Association stamp", "Authentic PNG or JPEG image", "Documented reason", "Upload for review", "Review decision", "Approve", "Reject", "Save decision", "Action unavailable: check authorization, file and state.", "Primary administration only. Authorized authentic images, no imitation. Replacement never rewrites issued documents; formal reissuance required.", "Pending", "Approved", "Rejected"],
}


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def manage(request):
    with transaction.atomic():
        s.authorize(request, primary_only=True, recent=False)
    data = context(request)
    labels = WORDS[data["language"]]
    visible_ids = list(CertificateAsset.objects.order_by("-pk").values_list("pk", flat=True)[:100])
    visible = CertificateAsset.objects.filter(pk__in=visible_ids).order_by("-pk")

    class UploadForm(forms.Form):
        key = forms.UUIDField(initial=uuid.uuid4, widget=forms.HiddenInput)
        kind = forms.ChoiceField(choices=[("signature", labels[2]), ("stamp", labels[3])], label=labels[1])
        image = forms.FileField(label=labels[4])
        reason = forms.CharField(max_length=1000, label=labels[5])

    class ReviewForm(forms.Form):
        key = forms.UUIDField(initial=uuid.uuid4, widget=forms.HiddenInput)
        asset_id = forms.ModelChoiceField(queryset=visible.filter(state="pending"), label=labels[0])
        decision = forms.ChoiceField(choices=[("approved", labels[8]), ("rejected", labels[9])], label=labels[7])
        reason = forms.CharField(max_length=1000, label=labels[5])

    action = request.POST.get("action") if request.method == "POST" else None
    upload = UploadForm(request.POST if action == "upload" else None, request.FILES if action == "upload" else None)
    review = ReviewForm(request.POST if action == "review" else None)
    review.fields["asset_id"].label_from_instance = (
        lambda asset: f"{labels[2] if asset.kind == 'signature' else labels[3]} — {asset.serial}"
    )
    status = 200
    if request.method == "POST":
        status = 400
        form = upload if action == "upload" else review if action == "review" else None
        if form and form.is_valid():
            try:
                values = form.cleaned_data
                if action == "upload":
                    # Service checks the bounded decoded image again.
                    image = values["image"].read(assets.MAX_BYTES + 1)
                    assets.upload_asset(request, key=str(values["key"]), kind=values["kind"], image_data=base64.b64encode(image).decode(), reason=values["reason"])
                else:
                    assets.review_asset(request, key=str(values["key"]), asset_id=values["asset_id"].pk, decision=values["decision"], reason=values["reason"])
                return redirect(reverse("certificate_assets")+"?lang="+data["language"])
            except PermissionDenied:
                form.add_error(None, labels[11]); status = 403
            except (ValidationError, ObjectDoesNotExist):
                form.add_error(None, labels[11])
    for row in visible:
        row.kind_label = labels[2] if row.kind == "signature" else labels[3]
        row.state_label = labels[{"pending": 13, "approved": 14, "rejected": 15}[row.state]]
    data.update(asset_words=labels, upload_form=upload, review_form=review, assets=visible, has_pending_assets=review.fields["asset_id"].queryset.exists())
    response = render(request, "governance/certificate_assets.html", data, status=status)
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET"])
@transaction.atomic
def image(request, serial):
    try:
        s.authorize(request, primary_only=True, recent=False)
    except (PermissionDenied, ObjectDoesNotExist):
        return HttpResponse(status=404)
    row = get_object_or_404(CertificateAsset, serial=serial)
    data = assets.asset_bytes(row)
    s.audit(request.user, "certificate.asset.viewed", row.serial)
    response = HttpResponse(data, content_type="image/png")
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    response["X-Content-Type-Options"] = "nosniff"
    return response
