"""Explicit administrative capabilities. Unknown or malformed grants fail closed."""

from django.core.exceptions import PermissionDenied, ValidationError

GROUPS = [
    (
        "membership",
        "العضوية",
        "Adhésions",
        "Membership",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("approve", "الموافقة", "Approuver", "Approve"),
            ("reject", "الرفض", "Refuser", "Reject"),
            ("suspend", "التعليق", "Suspendre", "Suspend"),
            ("cancel", "الإلغاء", "Annuler", "Cancel"),
            ("activate", "إعادة التفعيل", "Réactiver", "Reactivate"),
        ],
    ),
    (
        "identity",
        "ربط الحسابات",
        "Rattachement des comptes",
        "Account linking",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("link", "ربط السجل بالحساب", "Rattacher le dossier", "Link record"),
        ],
    ),
    (
        "portrait",
        "الصور الشخصية",
        "Portraits",
        "Portraits",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("approve", "القبول", "Approuver", "Approve"),
            ("reject", "الرفض", "Refuser", "Reject"),
        ],
    ),
    (
        "finance",
        "الشؤون المالية",
        "Finances",
        "Finance",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("verify", "التحقق من الأداء", "Vérifier le paiement", "Verify payment"),
            ("exempt", "الإعفاء", "Exonérer", "Exempt"),
            (
                "refund_approve",
                "الموافقة على الاسترجاع",
                "Approuver le remboursement",
                "Approve refund",
            ),
            (
                "refund_reject",
                "رفض الاسترجاع",
                "Refuser le remboursement",
                "Reject refund",
            ),
        ],
    ),
    (
        "pricing",
        "الأسعار",
        "Tarifs",
        "Pricing",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("edit", "التعديل", "Modifier", "Edit"),
        ],
    ),
    (
        "institutional",
        "البطاقات المؤسسية",
        "Cartes institutionnelles",
        "Institutional cards",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            (
                "grant",
                "تسجيل الصفة وإصدار البطاقة",
                "Enregistrer et délivrer",
                "Grant and issue",
            ),
            ("suspend", "التعليق", "Suspendre", "Suspend"),
            ("cancel", "الإلغاء", "Annuler", "Cancel"),
            ("activate", "إعادة التفعيل", "Réactiver", "Reactivate"),
            ("terminate", "إنهاء المنصب", "Terminer le mandat", "Terminate office"),
        ],
    ),
    (
        "accreditation",
        "الاعتماد المستقل",
        "Accréditation indépendante",
        "Independent accreditation",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("create", "إنشاء الملف", "Créer le dossier", "Create case"),
            ("edit", "تعديل المسودة", "Modifier le brouillon", "Edit draft"),
            (
                "reopen",
                "إعادة الملف إلى المسودة",
                "Rouvrir le brouillon",
                "Reopen draft",
            ),
            ("review", "إتمام المراجعة", "Valider la révision", "Complete review"),
            ("reject", "رفض الملف", "Refuser le dossier", "Reject case"),
            (
                "approve",
                "الموافقة والإصدار",
                "Approuver et délivrer",
                "Approve and issue",
            ),
            ("suspend", "التعليق", "Suspendre", "Suspend"),
            ("cancel", "الإلغاء", "Annuler", "Cancel"),
            ("activate", "إعادة التفعيل", "Réactiver", "Reactivate"),
        ],
    ),
    (
        "document",
        "الوثائق",
        "Documents",
        "Documents",
        [
            (
                "view",
                "الاطلاع والمعاينة",
                "Consulter et prévisualiser",
                "View and preview",
            ),
            ("download", "التنزيل", "Télécharger", "Download"),
            ("generate", "توليد PDF", "Générer le PDF", "Generate PDF"),
            ("reissue", "إعادة الإصدار", "Réémettre", "Reissue"),
        ],
    ),
    (
        "activity",
        "الأنشطة",
        "Activités",
        "Activities",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("create", "الإنشاء", "Créer", "Create"),
            ("edit", "التعديل", "Modifier", "Edit"),
            ("publish", "نشر النشاط", "Publier l’activité", "Publish activity"),
            ("hide", "إخفاء النشاط", "Masquer l’activité", "Hide activity"),
            ("image_upload", "رفع صور النشاط", "Ajouter des images", "Upload activity images"),
            ("image_remove", "سحب صور النشاط", "Retirer des images", "Remove activity images"),
        ],
    ),
    (
        "registration",
        "تسجيلات الأنشطة",
        "Inscriptions aux activités",
        "Activity registrations",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("approve", "الموافقة", "Approuver", "Approve"),
            ("reject", "الرفض", "Refuser", "Reject"),
            ("cancel", "الإلغاء", "Annuler", "Cancel"),
        ],
    ),
    (
        "attendance",
        "الحضور",
        "Présence",
        "Attendance",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("checkin", "تسجيل الحضور", "Enregistrer la présence", "Check in"),
        ],
    ),
    (
        "partner",
        "الشراكات",
        "Partenariats",
        "Partnerships",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("approve", "الموافقة", "Approuver", "Approve"),
            ("reject", "الرفض", "Refuser", "Reject"),
            ("edit", "تعديل البيانات", "Modifier les données", "Edit details"),
            ("publish", "النشر", "Publier", "Publish"),
            ("hide", "إخفاء العرض العام", "Masquer", "Hide public listing"),
            ("suspend", "التعليق", "Suspendre", "Suspend"),
            ("cancel", "الإلغاء", "Annuler", "Cancel"),
            ("activate", "إعادة التفعيل", "Réactiver", "Reactivate"),
        ],
    ),
    (
        "signing",
        "التوقيع والطابع",
        "Signature et cachet",
        "Signature and stamp",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("upload", "رفع بديل", "Déposer un remplacement", "Upload replacement"),
            ("approve", "القبول", "Approuver", "Approve"),
            ("reject", "الرفض", "Refuser", "Reject"),
        ],
    ),
    (
        "content",
        "صفحات الموقع",
        "Pages du site",
        "Website pages",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("create", "الإنشاء", "Créer", "Create"),
            ("edit", "تعديل المسودة", "Modifier le brouillon", "Edit draft"),
            ("publish", "النشر", "Publier", "Publish"),
            ("unpublish", "إلغاء النشر", "Dépublier", "Unpublish"),
            ("lock", "القفل", "Verrouiller", "Lock"),
            ("unlock", "فك القفل", "Déverrouiller", "Unlock"),
            ("delete", "الحذف", "Supprimer", "Delete"),
        ],
    ),
    (
        "media_image",
        "صور الموقع العامة",
        "Images publiques",
        "Public site images",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("upload", "الرفع", "Déposer", "Upload"),
            ("edit", "التعديل", "Modifier", "Edit"),
            ("delete", "الحذف", "Supprimer", "Delete"),
        ],
    ),
    (
        "media_document",
        "ملفات الموقع العامة",
        "Fichiers publics",
        "Public site files",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("upload", "الرفع", "Déposer", "Upload"),
            ("edit", "التعديل", "Modifier", "Edit"),
            ("delete", "الحذف", "Supprimer", "Delete"),
        ],
    ),
    (
        "contact",
        "بيانات التواصل العامة",
        "Coordonnées publiques",
        "Public contact",
        [
            ("view", "الاطلاع", "Consulter", "View"),
            ("edit", "التعديل", "Modifier", "Edit"),
        ],
    ),
]
CATALOG = {
    f"{group}.{key}": (names, captions)
    for group, *names, actions in GROUPS
    for key, *captions in actions
}
ALL_CAPABILITIES = tuple(CATALOG)


def prerequisites(capability):
    group, action = capability.split(".")
    required = set() if action == "view" else {group + ".view"}
    if group == "finance":
        required.add("membership.view")
    if group == "registration":
        required.add("activity.view")
    if group == "attendance":
        required.update({"registration.view", "activity.view"})
    return required


def validate_capabilities(values, *, active=True):
    if (
        not isinstance(values, list)
        or len(values) > len(CATALOG)
        or any(not isinstance(v, str) or v not in CATALOG for v in values)
        or len(values) != len(set(values))
    ):
        raise ValidationError("Select explicit known capabilities")
    if not active:
        return []
    selected = set(values)
    if active and not selected:
        raise ValidationError("Select at least one capability")
    for value in selected:
        if not prerequisites(value) <= selected:
            raise ValidationError("Explicit view prerequisites must also be selected")
    return sorted(selected) if active else []


def label(key, language="ar", *, full=False):
    index = {"ar": 0, "fr": 1, "en": 2}.get(language, 0)
    if key not in CATALOG:
        return key
    names, captions = CATALOG[key]
    return (names[index] + " — " if full else "") + captions[index]


def allows(request, capability):
    """UI hint only. Transactional services recheck the current grant and epoch."""
    from .models import Authority, Delegation

    user = getattr(request, "user", None)
    if (
        not user
        or not user.is_authenticated
        or not user.is_active
    ):
        return False
    if not hasattr(request, "_display_capabilities"):
        if Authority.objects.filter(pk=1, primary=user).exists():
            request._display_capabilities = (
                set(ALL_CAPABILITIES) if user.is_verified() and request.session.get("authority_epoch") == 0 else set()
            )
        else:
            row = Delegation.objects.filter(user=user, active=True).first()
            try:
                values = (
                    validate_capabilities(row.capabilities)
                    if row and request.session.get("authority_epoch") == row.epoch
                    else []
                )
            except ValidationError:
                values = []
            request._display_capabilities = set(values)
    return capability in request._display_capabilities


def enforce(request, *capabilities, recent=False):
    from django.db import transaction
    from .services import authorize

    with transaction.atomic():
        return authorize(request, capability=capabilities, recent=recent)


def action_capabilities(action, payload):
    """Resolve the exact decision, never a combined approve/reject permission."""
    static = {
        "content.publish": "content.publish",
        "membership.approve": "membership.approve",
        "membership.reject": "membership.reject",
        "person.link": "identity.link",
        "institutional.grant": "institutional.grant",
        "price.change": "pricing.edit",
        "payment.verify": "finance.verify",
        "fee.exempt": "finance.exempt",
        "accreditation.approve": "accreditation.approve",
        "document.replace": "document.reissue",
        "registration.cancel": "registration.cancel",
        "attendance.checkin": "attendance.checkin",
        "activity.publish": "activity.publish",
        "activity.hide": "activity.hide",
        "activity.image.upload": "activity.image_upload",
        "activity.image.remove": "activity.image_remove",
        "activity.create": "activity.create",
        "activity.update": "activity.edit",
        "accreditation.case.create": "accreditation.create",
        "accreditation.case.approve": "accreditation.approve",
        "certificate.asset.upload": "signing.upload",
    }
    if action in static:
        required = [static[action]]
        if action in {'activity.update', 'activity.image.upload'}:
            from .models import Activity
            if Activity.objects.select_for_update().get(pk=payload.get('activity_id')).is_published:
                required.append('activity.publish')
        if action == "institutional.grant" and payload.get("replaces_role_id"):
            required.append("institutional.terminate")
        return required
    if action in {"right.state", "institutional.state"}:
        group = (
            "institutional" if action == "institutional.state" else payload.get("model")
        )
        suffix = {
            "active": "activate",
            "suspended": "suspend",
            "cancelled": "cancel",
            "terminated": "terminate",
        }.get(payload.get("state"))
        return [f"{group}.{suffix}"]
    if action == "refund.decide":
        return [
            (
                "finance.refund_approve"
                if payload.get("approved") is True
                else "finance.refund_reject"
            )
        ]
    if action == "registration.decide":
        return [
            (
                "registration.approve"
                if payload.get("accept") is True
                else "registration.reject"
            )
        ]
    if action in {"portrait.review", "certificate.asset.review", "partnership.decide"}:
        group = {
            "portrait.review": "portrait",
            "certificate.asset.review": "signing",
            "partnership.decide": "partner",
        }[action]
        return [
            group
            + "."
            + {"approved": "approve", "rejected": "reject"}.get(
                payload.get("decision"), "invalid"
            )
        ]
    if action == "accreditation.case.review":
        from .models import AccreditationCase
        from .accreditation_services import private_data
        from .services import decrypt

        row = AccreditationCase.objects.select_for_update().get(
            pk=payload.get("case_id")
        )
        previous = decrypt(row.private_payload)
        decision = payload.get("decision")
        scope = (
            "reopen"
            if decision == "draft" and row.state == "reviewed"
            else {"draft": "edit", "reviewed": "review", "rejected": "reject"}.get(
                decision, "invalid"
            )
        )
        required = ["accreditation." + scope]
        proposed = private_data(
            payload.get("criteria"), payload.get("assessment"), payload.get("fee")
        )
        if any(
            proposed.get(key) != previous.get(key)
            for key in ("criteria", "assessment", "fee")
        ):
            required.append("accreditation.edit")
        return required
    if action == "partner.update":
        from .models import Partner

        row = Partner.objects.select_for_update().get(pk=payload.get("partner_id"))
        required = []
        fields = (
            "name_ar",
            "name_fr",
            "name_en",
            "summary_ar",
            "summary_fr",
            "summary_en",
            "website",
        )
        if any(payload.get(f) != getattr(row, f) for f in fields):
            required.append("partner.edit")
        state = payload.get("state")
        if state != row.state:
            required.append(
                "partner."
                + {
                    "active": "activate",
                    "suspended": "suspend",
                    "cancelled": "cancel",
                }.get(state, "invalid")
            )
        visible = payload.get("public_visible") if state == "active" else False
        if visible != row.public_visible:
            required.append("partner.publish" if visible else "partner.hide")
        return required or ["partner.edit"]
    return None  # No unregistered operation is ever implicitly delegated.


def restrict_choices(request, form, field, mapping):
    form.fields[field].choices = [
        (value, caption)
        for value, caption in form.fields[field].choices
        if value and allows(request, mapping.get(value, ""))
    ]
