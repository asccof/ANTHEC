import uuid
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .member_views import localized
from .member_labels import vocabulary as member_vocabulary
from .operations_labels import vocabulary
from .operations_forms import DirectorForm, PriceForm
from .models import Authority, Delegation, Price, Audit
from . import services

def context(request):
    language, extra = vocabulary(request.GET.get("lang", "ar"))
    labels = dict(member_vocabulary(language)[1])
    labels.update(extra)
    return dict(language=language, labels=labels, direction="rtl" if language == "ar" else "ltr",
                owner_testing=getattr(settings, "ANTHEEC_OWNER_TESTING", False))

@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def directors(request):
    # Both reads and writes are primary-only, including forged requests.
    with transaction.atomic():
        services.authorize(request, primary_only=True, recent=False)
    ctx = context(request)
    form = DirectorForm(request.POST if request.method == "POST" else None,
                        labels=ctx["labels"], initial={"key": uuid.uuid4()})
    status = 200
    if request.method == "POST":
        if form.is_valid():
            data = form.cleaned_data
            try:
                services.delegate(request, key=str(data["key"]), user_id=data["user"].pk,
                                  active=data["decision"] == "grant", reason=data["reason"])
                return redirect(reverse("director_register") + "?lang=" + ctx["language"])
            except PermissionDenied:
                form.add_error(None, ctx["labels"]["error"]); status = 403
            except ValidationError:
                form.add_error(None, ctx["labels"]["error"]); status = 400
        else:
            status = 400
    rows = list(Delegation.objects.select_related("user").order_by("-pk")[:100])
    for row in rows:
        row.display_state = ctx["labels"]["active" if row.active else "inactive"]
    ctx.update(form=form, rows=rows, primary=Authority.objects.select_related("primary").get(pk=1).primary,
               history=Audit.objects.filter(action="delegation.changed").order_by("-pk")[:100])
    return render(request, "governance/directors.html", ctx, status=status)

@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
@timezone.override("UTC")
def pricing(request):
    with transaction.atomic():
        services.authorize(request, recent=False)
    ctx = context(request)
    now = timezone.now()
    initial = {"key": uuid.uuid4(), "starts_at": (now + timedelta(days=1)).replace(second=0, microsecond=0)}
    form = PriceForm(request.POST if request.method == "POST" else None, labels=ctx["labels"], initial=initial)
    status = 200
    if request.method == "POST":
        if form.is_valid():
            data = form.cleaned_data
            try:
                services.change_price(request, key=str(data["key"]), tier=data["tier"], amount=str(data["amount"]),
                                      starts_at=data["starts_at"].isoformat(), reason=data["reason"])
                return redirect(reverse("pricing_register") + "?lang=" + ctx["language"])
            except PermissionDenied:
                form.add_error(None, ctx["labels"]["error"]); status = 403
            except ValidationError:
                form.add_error(None, ctx["labels"]["error"]); status = 400
        else:
            status = 400
    current = []
    for tier in ("general", "affiliate", "advanced", "accredited"):
        price = Price.objects.filter(tier=tier, starts_at__lte=now).order_by("-starts_at", "-pk").first()
        current.append({"label": ctx["labels"][tier], "price": price})
    rows = list(Price.objects.order_by("-starts_at", "-pk")[:100])
    for row in rows:
        row.display_tier = ctx["labels"].get(row.tier, row.tier)
    ctx.update(form=form, current=current, rows=rows,
               history=Audit.objects.filter(action="price.changed").order_by("-pk")[:100])
    return render(request, "governance/pricing.html", ctx, status=status)
