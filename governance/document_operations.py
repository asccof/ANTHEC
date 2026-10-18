"""Scoped document registry, independent of membership/finance access."""

import uuid
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .capabilities import enforce
from .member_views import context, localized
from .membership_admin_forms import ReasonForm
from .models import Document
from .pdf_views import document_person
from . import services


def rows():
    return Document.objects.select_related(
        "membership__application__person",
        "accreditation__person",
        "institutional_role__person",
        "registration__person",
    ).order_by("-pk")


def item(doc, labels):
    person = document_person(doc)
    return dict(
        doc=doc,
        holder=(
            person.full_name
            if person
            else (doc.accreditation.subject_name if doc.accreditation_id else "—")
        ),
        caption=labels.get(doc.kind, doc.kind),
        state=labels.get(services.document_status(doc), services.document_status(doc)),
    )


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET"])
@localized
def listing(request):
    enforce(request, "document.view")
    ctx = context(request)
    ctx["document_rows"] = [item(doc, ctx["labels"]) for doc in rows()[:100]]
    return render(request, "governance/document_operations.html", ctx)


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def detail(request, document_id):
    enforce(request, "document.view")
    ctx = context(request)
    doc = get_object_or_404(rows(), pk=document_id)
    form = ReasonForm(
        request.POST if request.method == "POST" else None,
        labels=ctx["labels"],
        initial={"key": uuid.uuid4()},
    )
    status = 200
    if request.method == "POST":
        if form.is_valid():
            try:
                services.replace_document(
                    request,
                    key=str(form.cleaned_data["key"]),
                    document_id=doc.pk,
                    reason=form.cleaned_data["reason"],
                )
                return redirect("delegated_documents")
            except PermissionDenied:
                form.add_error(None, ctx["labels"]["reauth"])
                status = 403
            except ValidationError:
                form.add_error(None, ctx["labels"]["error"])
                status = 400
        else:
            status = 400
    ctx.update(
        document_rows=[item(doc, ctx["labels"])], form=form, selected_document=doc
    )
    return render(request, "governance/document_operations.html", ctx, status=status)
