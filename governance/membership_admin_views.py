from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError, ObjectDoesNotExist
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from . import services as s, membership_admin_services as admin
from .member_views import context, localized
from .institutional_views import read_authority
from .membership_admin_forms import (
    ReasonForm,
    PaymentForm,
    RefundForm,
    StateForm,
    DocumentForm,
    LinkForm,
)
from .models import Application, Document, Audit, Membership, Refund


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET"])
@localized
def register(request):
    read_authority(request)
    ctx = context(request)
    apps = Application.objects.select_related("person").order_by("-pk")[:100]
    ctx["applications"] = [
        {
            "app": a,
            "tier": ctx["labels"][a.tier],
            "state": ctx["labels"].get(a.state, a.state),
        }
        for a in apps
    ]
    return render(request, "governance/membership_admin_register.html", ctx)


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def identities(request):
    read_authority(request)
    ctx = context(request)
    form = LinkForm(
        request.POST if request.method == "POST" else None, labels=ctx["labels"]
    )
    status = 200
    if request.method == "POST":
        if form.is_valid():
            data = form.cleaned_data
            try:
                admin.link_person(
                    request,
                    key=str(data["key"]),
                    person_id=data["person_id"].pk,
                    user_id=data["user_id"].pk,
                    reason=data["reason"],
                )
                return redirect(
                    reverse("membership_identities") + "?lang=" + ctx["language"]
                )
            except PermissionDenied:
                form.add_error(None, ctx["labels"]["reauth"])
                status = 403
            except (ValidationError, ObjectDoesNotExist):
                form.add_error(None, ctx["labels"]["error"])
                status = 400
        else:
            status = 400
    return render(
        request,
        "governance/membership_admin_identities.html",
        {**ctx, "form": form},
        status=status,
    )


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def detail(request, application_id):
    read_authority(request)
    app = get_object_or_404(
        Application.objects.select_related("person", "previous"), pk=application_id
    )
    ctx = context(request)
    payments = app.payment_set.order_by("pk")
    term = Membership.objects.filter(application=app).first()
    documents = (
        Document.objects.filter(Q(membership=term) | Q(accreditation__membership=term))
        if term
        else Document.objects.none()
    )
    constructors = {
        "approve": (ReasonForm, {}),
        "reject": (ReasonForm, {}),
        "payment": (PaymentForm, {}),
        "exempt": (ReasonForm, {}),
        "refund": (RefundForm, {"payments": payments}),
        "state": (StateForm, {"initial": {"state": term.state} if term else {}}),
        "replace": (DocumentForm, {"documents": documents}),
    }
    forms = {
        name: cls(labels=ctx["labels"], **options)
        for name, (cls, options) in constructors.items()
    }
    status = 200
    if request.method == "POST":
        action = request.POST.get("action")
        if action not in constructors:
            status = 400
        else:
            cls, options = constructors[action]
            form = forms[action] = cls(request.POST, labels=ctx["labels"], **options)
            if form.is_valid():
                data = form.cleaned_data
                common = {"key": str(data["key"])}
                try:
                    if action in ("approve", "reject", "exempt"):
                        fn = {
                            "approve": s.approve_membership,
                            "reject": admin.reject,
                            "exempt": s.exempt_fee,
                        }[action]
                        fn(
                            request,
                            application_id=app.pk,
                            reason=data["reason"],
                            **common
                        )
                    elif action == "payment":
                        s.verify_payment(
                            request,
                            application_id=app.pk,
                            amount=str(data["amount"]),
                            method=data["method"],
                            proof_reference=data["proof_reference"],
                            **common
                        )
                    elif action == "refund":
                        s.decide_refund(
                            request,
                            payment_id=data["payment_id"].pk,
                            amount=str(data["amount"]),
                            approved=data["approved"] == "yes",
                            reason=data["reason"],
                            **common
                        )
                    elif action == "state":
                        if not term:
                            raise ValidationError("No approved membership")
                        s.change_state(
                            request,
                            model="membership",
                            object_id=term.pk,
                            state=data["state"],
                            reason=data["reason"],
                            **common
                        )
                    else:
                        s.replace_document(
                            request,
                            document_id=data["document_id"].pk,
                            reason=data["reason"],
                            **common
                        )
                    return redirect(
                        reverse("membership_admin_detail", args=[app.pk])
                        + "?lang="
                        + ctx["language"]
                    )
                except PermissionDenied:
                    form.add_error(None, ctx["labels"]["reauth"])
                    status = 403
                except (ValidationError, ObjectDoesNotExist):
                    form.add_error(None, ctx["labels"]["error"])
                    status = 400
            else:
                status = 400
    refunds = (
        Refund.objects.filter(payment__application=app)
        .select_related("payment")
        .order_by("pk")
    )
    # Exemption is one-to-one; query explicitly, do not expose unrelated same-ID audits.
    from .models import Exemption

    exemption_ids = [
        str(pk)
        for pk in Exemption.objects.filter(application=app).values_list("pk", flat=True)
    ]
    history = Audit.objects.filter(
        Q(
            action__in=[
                "member.application.submitted",
                "member.renewal.submitted",
                "membership.rejected",
            ],
            subject=str(app.pk),
        )
        | Q(action="payment.verified", subject__in=[str(p.pk) for p in payments])
        | Q(action="refund.decided", subject__in=[str(r.pk) for r in refunds])
        | Q(action="fee.exempted", subject__in=exemption_ids)
        | Q(
            action__in=[
                "membership.approved",
                "membership.active",
                "membership.suspended",
                "membership.cancelled",
            ],
            subject=str(term.pk) if term else "",
        )
        | Q(action="document.replaced", subject__in=[str(d.pk) for d in documents])
    ).order_by("pk")
    ctx.update(
        declared_capacity=ctx["labels"].get(
            (
                "capacity_option_other"
                if app.applicant_capacity == "other"
                else "capacity_" + app.applicant_capacity
            ),
            "—",
        ),
        app=app,
        term=term,
        tier=ctx["labels"][app.tier],
        state=ctx["labels"].get(app.state, app.state),
        forms=forms,
        payments=payments,
        refunds=refunds,
        history=history,
        payment_rows=[
            {"payment": p, "method": ctx["labels"][p.method]} for p in payments
        ],
        paid=payments.aggregate(total=Sum("amount"))["total"] or 0,
        refunded=refunds.filter(approved=True).aggregate(total=Sum("amount"))["total"]
        or 0,
        documents=[
            {
                "doc": d,
                "label": ctx["labels"].get(d.kind, d.kind),
                "status": ctx["labels"].get(s.document_status(d), s.document_status(d)),
            }
            for d in documents
        ],
    )
    return render(
        request, "governance/membership_admin_detail.html", ctx, status=status
    )
