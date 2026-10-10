import json
from decimal import InvalidOperation
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.debug import sensitive_post_parameters
from . import services
from .models import Document, RateBucket, Person, Activity
from .documents import printable


@never_cache
@sensitive_post_parameters("token", "code")
@require_http_methods(["GET", "POST"])
def verify(request):
    if request.method == "GET":
        return render(request, "governance/verify.html")
    # No forwarded headers trusted; fixed 10-minute IP bucket, hashed and bounded.
    bucket = services.digest(
        f'verify:{request.META.get("REMOTE_ADDR","")}:{int(timezone.now().timestamp()//600)}'
    )
    with transaction.atomic():
        row, _ = RateBucket.objects.get_or_create(key=bucket)
        row = RateBucket.objects.select_for_update().get(pk=bucket)
        row.count += 1
        row.save(update_fields=["count"])
        if row.count > 30:
            return JsonResponse({"error": "Try again later"}, status=429)
    data = services.lookup_document(
        token=request.POST.get("token"),
        serial=request.POST.get("serial"),
        code=request.POST.get("code"),
    )
    response = JsonResponse(
        data if data else {"error": "Document not found"}, status=200 if data else 404
    )
    response["Cache-Control"] = "no-store"
    return response


ACTIONS = {
    "delegate": services.delegate,
    "price.change": services.change_price,
    "payment.verify": services.verify_payment,
    "fee.exempt": services.exempt_fee,
    "membership.approve": services.approve_membership,
    "accreditation.approve": services.approve_accreditation,
    "right.state": services.change_state,
    "document.replace": services.replace_document,
    "refund.decide": services.decide_refund,
    "registration.decide": services.decide_registration,
    "registration.cancel": services.cancel_registration,
    "attendance.checkin": services.check_in,
}


@never_cache
@login_required(login_url="/admin/login/")
@require_POST
def operation(request, action):
    if action not in ACTIONS:
        return JsonResponse({"error": "Unknown action"}, status=404)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError()
        result = ACTIONS[action](request, **payload)
        return JsonResponse(result)
    except PermissionDenied:
        return JsonResponse(
            {"error": "Not authorized or recent MFA required"}, status=403
        )
    except services.Conflict:
        return JsonResponse({"error": "Conflicting command"}, status=409)
    except (ValidationError, ValueError, TypeError, InvalidOperation):
        return JsonResponse({"error": "Invalid command"}, status=400)
    except ObjectDoesNotExist:
        return JsonResponse({"error": "Object not found"}, status=404)


@never_cache
@login_required(login_url="/admin/login/")
def download(request, document_id):
    doc = Document.objects.filter(pk=document_id).first()
    if doc is None:
        return HttpResponse(status=404)
    person = (
        doc.membership.application.person
        if doc.membership_id
        else (
            doc.accreditation.person
            if doc.accreditation_id
            else doc.registration.person
        )
    )
    own = person and (
        person.user_id == request.user.pk
        or person.minor
        and person.guardian_id == request.user.pk
    )
    if not own:
        try:
            with transaction.atomic():
                services.authorize(request)
        except (PermissionDenied, ObjectDoesNotExist):
            return HttpResponse(status=404)
    html = printable(doc)
    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="ANTHEEC-{doc.serial}.html"'
    )
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


@never_cache
@login_required(login_url="/admin/login/")
@require_POST
def registration_request(request):
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError()
        for field in ["person_id", "activity_id"]:
            if (
                not isinstance(payload.get(field), int)
                or isinstance(payload.get(field), bool)
                or payload[field] <= 0
            ):
                raise ValueError()
        person = Person.objects.get(pk=payload["person_id"])
        activity = Activity.objects.get(pk=payload["activity_id"])
        row = services.register(
            activity,
            person,
            request.user,
            guardian_name=payload.get("guardian_name", ""),
            guardian_capacity=payload.get("guardian_capacity", ""),
            consent=payload.get("consent", False),
        )
        return JsonResponse({"registration": row.pk, "state": row.state}, status=201)
    except PermissionDenied:
        return JsonResponse({"error": "Not authorized"}, status=403)
    except services.Conflict:
        return JsonResponse({"error": "Already registered"}, status=409)
    except (ValidationError, ValueError, KeyError, TypeError):
        return JsonResponse({"error": "Invalid request"}, status=400)
    except ObjectDoesNotExist:
        return JsonResponse({"error": "Object not found"}, status=404)
