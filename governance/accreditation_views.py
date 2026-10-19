import uuid
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .institutional_views import read_authority
from .member_views import localized
from .member_labels import vocabulary as member_vocabulary
from .accreditation_labels import vocabulary
from .accreditation_forms import CaseForm, ReviewForm, ApprovalForm
from .models import AccreditationCase, Audit
from .services import decrypt
from . import accreditation_services as service


def context(request):
    language, extra = vocabulary(request.GET.get("lang", "ar"))
    labels = dict(member_vocabulary(language)[1]); labels.update(extra)
    return dict(language=language, labels=labels, direction="rtl" if language=="ar" else "ltr",
        owner_testing=getattr(settings,"ANTHEEC_OWNER_TESTING",False))


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def register(request):
    read_authority(request, "accreditation.view")
    ctx = context(request)
    form = CaseForm(request.POST if request.method=="POST" else None, labels=ctx["labels"], initial={"key":uuid.uuid4()})
    status = 200
    if request.method=="POST":
        if form.is_valid():
            data=form.cleaned_data
            try:
                result=service.create(request, key=str(data["key"]), kind=data["kind"], person_id=data["person"].pk if data["person"] else None,
                    subject_name=data["subject"], starts_on=data["start"].isoformat(), ends_on=data["end"].isoformat(),
                    criteria=data["criteria"], assessment=data["assessment"], fee=str(data["fee"]) if data["fee"] is not None else "", reason=data["reason"])
                return redirect(reverse("accreditation_case",args=[result["case"]])+"?lang="+ctx["language"])
            except PermissionDenied: form.add_error(None,ctx["labels"]["error"]); status=403
            except ValidationError: form.add_error(None,ctx["labels"]["error"]); status=400
        else: status=400
    rows=list(AccreditationCase.objects.select_related("person").order_by("-pk")[:100])
    for row in rows:
        row.display_subject=row.person.full_name if row.person else row.subject_name
        row.display_state=ctx["labels"][row.state]
    ctx.update(form=form,rows=rows)
    return render(request,"governance/accreditation_register.html",ctx,status=status)


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def detail(request,case_id):
    read_authority(request, "accreditation.view")
    ctx=context(request)
    row=get_object_or_404(AccreditationCase.objects.select_related("person"),pk=case_id)
    private=decrypt(row.private_payload)
    initial={**private,"decision":row.state if row.state in {"draft","reviewed"} else "draft","key":uuid.uuid4()}
    approving=request.method=="POST" and request.POST.get("operation")=="approve"
    form=ReviewForm(request.POST if request.method=="POST" and not approving else None,labels=ctx["labels"],initial=initial)
    approval=ApprovalForm(request.POST if approving else None,labels=ctx["labels"],initial={"key":uuid.uuid4()})
    from .capabilities import allows
    if not allows(request, "accreditation.edit"):
        for name in ('criteria', 'assessment', 'fee'): form.fields[name].disabled = True
    status=200
    active=approval if approving else form
    if request.method=="POST":
        if active.is_valid():
            data=dict(active.cleaned_data); key=str(data.pop("key"))
            if not approving: data["fee"]=str(data["fee"]) if data["fee"] is not None else ""
            try:
                (service.approve if approving else service.review)(request,key=key,case_id=row.pk,**data)
                return redirect(reverse("accreditation_case",args=[row.pk])+"?lang="+ctx["language"])
            except PermissionDenied: active.add_error(None,ctx["labels"]["error"]); status=403
            except ValidationError: active.add_error(None,ctx["labels"]["error"]); status=400
        else: status=400
    history=list(Audit.objects.filter(subject=str(row.pk),action__startswith="accreditation.case.").order_by("pk"))
    for event in history:
        event.private_reason=decrypt(event.details["private_payload"]).get("reason", "") if event.details.get("private_payload") else ""
    from .capabilities import restrict_choices
    restrict_choices(request, form, "decision", {"draft": "accreditation.reopen" if row.state == "reviewed" else "accreditation.edit", "reviewed": "accreditation.review", "rejected": "accreditation.reject"})
    ctx.update(row=row,private=private,form=form,approval=approval,display_state=ctx["labels"][row.state],
        display_subject=row.person.full_name if row.person else row.subject_name,
        display_kind=ctx["labels"][row.kind], history=history)
    return render(request,"governance/accreditation_case.html",ctx,status=status)
