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
    labels["_language"] = language
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
    from .capabilities import GROUPS, label, prerequisites
    target = None
    if request.method == "GET" and request.GET.get("user", "").isdigit():
        from django.contrib.auth import get_user_model
        target = get_user_model().objects.filter(pk=request.GET['user'], is_superuser=False).first()
    existing = Delegation.objects.filter(user=target).first() if target else None
    initial = {"key": uuid.uuid4(), "user": target, "capabilities": existing.capabilities if existing else [],
               "expected_epoch": existing.epoch if existing else 0, "decision": "grant"}
    form = DirectorForm(request.POST if request.method == "POST" else None, labels=ctx["labels"], initial=initial)
    status = 200
    if request.method == "POST":
        if form.is_valid():
            data = form.cleaned_data
            try:
                services.delegate(request, key=str(data["key"]), user_id=data["user"].pk,
                                  active=data["decision"] == "grant", reason=data["reason"], capabilities=data["capabilities"], expected_epoch=data["expected_epoch"])
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
        row.display_capabilities = [label(key, ctx['language'], full=True) for key in row.capabilities]
    selected = form['capabilities'].value() or []
    capability_groups = []
    for group, *names, actions in GROUPS:
        fields = []
        for key, *_ in actions:
            code = group + '.' + key
            fields.append(dict(code=code, caption=label(code, ctx['language']), selected=code in selected,
                               prerequisites=[label(p, ctx['language'], full=True) for p in sorted(prerequisites(code))]))
        capability_groups.append(dict(title=names[('ar','fr','en').index(ctx['language'])], fields=fields))
    value = str(form['user'].value() or '')
    selected_account = form.fields['user'].queryset.filter(pk=value).first() if value.isdigit() else None
    history = list(Audit.objects.filter(action="delegation.changed").select_related('actor').order_by("-pk")[:100])
    for event in history:
        event.before_labels = [label(key, ctx['language'], full=True) for key in event.details.get('before', {}).get('capabilities', [])]
        event.after_labels = [label(key, ctx['language'], full=True) for key in event.details.get('capabilities', [])]
    ctx.update(form=form, rows=rows, capability_groups=capability_groups, selected_account=selected_account,
               primary=Authority.objects.select_related("primary").get(pk=1).primary, history=history)
    return render(request, "governance/directors.html", ctx, status=status)

@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
@timezone.override("UTC")
def pricing(request):
    with transaction.atomic():
        services.authorize(request, recent=False, capability="pricing.view")
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


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET"])
@localized
def workspace(request):
    from .capabilities import enforce, allows
    enforce(request)
    ctx = context(request)
    links = [("membership.view", "membership_admin_register", "administration"),
             ("identity.view", "membership_identities", "identities"),
             ("portrait.view", "portrait_review", "manage_portrait"),
             ("document.view", "delegated_documents", "documents"),
             ("pricing.view", "pricing_register", "pricing"),
             ("institutional.view", "institutional_register", "title")]
    ctx['workspace_links'] = [(reverse(route), ctx['labels'][caption]) for cap, route, caption in links if allows(request, cap)]
    for cap, route, caption in [("accreditation.view", "accreditation_register", "الاعتماد / Accréditation / Accreditation"),
                                ("activity.view", "activity_admin_register", "الأنشطة / Activités / Activities"),
                                ("partner.view", "partnership_register", "الشراكات / Partenariats / Partnerships"),
                                ("signing.view", "certificate_assets", "التوقيع والطابع / Signature et cachet / Signature and stamp")]:
        if allows(request, cap): ctx['workspace_links'].append((reverse(route), caption))
    for cap, url, caption in [("content.view", "/operations/content/", "الصفحات / Pages"),
                              ("media_image.view", "/admin/images/", "الصور / Images"),
                              ("media_document.view", "/admin/documents/", "الملفات / Documents"),
                              ("contact.view", "/admin/settings/content/publiccontact/", "التواصل / Contact")]:
        if allows(request, cap): ctx['workspace_links'].append((url, caption))
    return render(request, "governance/delegated_workspace.html", ctx)
