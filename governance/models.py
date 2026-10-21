import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Authority(models.Model):
    """One project authority; changing the primary is not a web operation."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    primary = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(id=1), name="single_authority")
        ]


class Delegation(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    active = models.BooleanField(default=True)
    epoch = models.PositiveIntegerField(default=1)
    capabilities = models.JSONField(default=list, blank=True)


class Audit(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True
    )
    action = models.CharField(max_length=60)
    subject = models.CharField(max_length=120)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict)


class Command(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=60)
    key = models.CharField(max_length=120)
    digest = models.CharField(max_length=64)
    result = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["actor", "action", "key"], name="command_replay_scope"
            )
        ]


class Price(models.Model):
    tier = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    starts_at = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0), name="price_nonnegative")
        ]


class Person(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True
    )
    guardian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name="dependants",
    )
    full_name = models.CharField(max_length=200)
    contact = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    profession = models.CharField(max_length=200, blank=True)
    minor = models.BooleanField(default=False)
    directory_consent = models.BooleanField(default=False)
    verification_notice_at = models.DateTimeField(null=True)


class Application(models.Model):
    intake_version = models.PositiveSmallIntegerField(default=0)
    address_category = models.CharField(max_length=16, blank=True)
    correspondence_address = models.TextField(blank=True)
    professional_address = models.TextField(blank=True)
    residential_address = models.TextField(blank=True)
    intake_portrait = models.ForeignKey(
        "Portrait", on_delete=models.PROTECT, null=True, related_name="applications"
    )

    applicant_capacity = models.CharField(max_length=24, blank=True)
    capacity_other = models.CharField(max_length=200, blank=True)
    profession_snapshot = models.CharField(max_length=200, blank=True)
    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    tier = models.CharField(max_length=20)
    state = models.CharField(max_length=20, default="submitted")
    quote = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.ForeignKey(Price, on_delete=models.PROTECT, null=True)
    quoted_on = models.DateField()
    previous = models.ForeignKey(
        "Membership",
        on_delete=models.PROTECT,
        null=True,
        related_name="renewal_applications",
    )


class Payment(models.Model):
    application = models.ForeignKey(Application, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(
        max_length=12, choices=[("cash", "Cash"), ("transfer", "Transfer")]
    )
    receipt = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    proof_reference = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="positive_payment")
        ]


class Exemption(models.Model):
    application = models.OneToOneField(Application, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Membership(models.Model):
    application = models.OneToOneField(Application, on_delete=models.PROTECT)
    starts_on = models.DateField()
    ends_on = models.DateField(null=True)  # exclusive
    state = models.CharField(max_length=20, default="active")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_on__isnull=True)
                | Q(ends_on__gt=models.F("starts_on")),
                name="membership_dates",
            )
        ]


class Accreditation(models.Model):
    membership = models.OneToOneField(Membership, on_delete=models.PROTECT, null=True)
    person = models.ForeignKey(Person, on_delete=models.PROTECT, null=True)
    subject_name = models.CharField(max_length=200, blank=True)
    kind = models.CharField(max_length=20, default="professional")
    starts_on = models.DateField()
    ends_on = models.DateField()
    state = models.CharField(max_length=20, default="active")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_on__gt=models.F("starts_on")),
                name="accreditation_dates",
            )
        ]


class Activity(models.Model):
    presentation = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=False)
    fixture_key = models.CharField(max_length=60, null=True, unique=True)
    title = models.CharField(max_length=200)
    starts_on = models.DateField()
    ends_on = models.DateField()
    capacity = models.PositiveIntegerField()
    allows_minors = models.BooleanField(default=False)
    consent_version = models.CharField(max_length=60, default="v1")
    consent_text = models.TextField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_on__gte=models.F("starts_on")), name="activity_dates"
            )
        ]


class ActivityImage(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT, related_name="editorial_images")
    serial = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    jpeg = models.BinaryField()
    caption = models.CharField(max_length=240, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Registration(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    guardian_name = models.CharField(max_length=200, blank=True)
    guardian_capacity = models.CharField(max_length=100, blank=True)
    consent_at = models.DateTimeField(null=True)
    consent_version = models.CharField(max_length=60, blank=True)
    consent_text = models.TextField(blank=True)
    state = models.CharField(max_length=20, default="requested")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "person"], name="one_participant_per_activity"
            )
        ]


class Attendance(models.Model):
    registration = models.OneToOneField(Registration, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    at = models.DateTimeField(auto_now_add=True)


class InstitutionalRole(models.Model):
    """Recorded institutional eligibility; never an administrative permission."""

    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    role = models.CharField(
        max_length=20,
        choices=[
            ("president", "President"),
            ("vice_president", "Vice-President"),
            ("founder", "Founding Member"),
            ("honorary", "Honorary Member"),
        ],
    )
    starts_on = models.DateField()
    ends_on = models.DateField(null=True)  # exclusive; explicitly recorded legal end
    legal_reference = models.CharField(max_length=120)
    state = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    replaces = models.OneToOneField("self", on_delete=models.PROTECT, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(role__in=["founder", "honorary"], ends_on__isnull=True)
                    | Q(
                        role__in=["president", "vice_president"],
                        ends_on__isnull=False,
                        ends_on__gt=models.F("starts_on"),
                    )
                ),
                name="institutional_recorded_term",
            ),
            models.CheckConstraint(
                condition=Q(
                    state__in=["active", "suspended", "cancelled", "terminated"]
                ),
                name="institutional_valid_state",
            ),
            models.UniqueConstraint(
                fields=["person"],
                condition=Q(role="founder"),
                name="one_founder_designation",
            ),
            models.UniqueConstraint(fields=["person"], condition=Q(role="honorary"), name="one_honorary_designation"),
        ]


class Portrait(models.Model):
    serial = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_portraits",
    )
    image = (
        models.TextField()
    )  # Fernet-encrypted normalized JPEG; no original file/media URL
    state = models.CharField(
        max_length=12,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name="reviewed_portraits",
    )
    reviewed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    state="pending", reviewed_by__isnull=True, reviewed_at__isnull=True
                )
                | Q(
                    state__in=["approved", "rejected"],
                    reviewed_by__isnull=False,
                    reviewed_at__isnull=False,
                ),
                name="portrait_review_evidence",
            )
        ]

    def __str__(self):
        return str(self.serial)


class CertificateAsset(models.Model):
    """Private approved raster artwork; approved rows are immutable, never public media."""
    serial = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    kind = models.CharField(max_length=10, choices=[("signature", "Signature"), ("stamp", "Stamp")])
    image = models.TextField()  # Encrypted normalized PNG, no original retained.
    sha256 = models.CharField(max_length=64, editable=False)
    state = models.CharField(max_length=10, default="pending", choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")])
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_certificate_assets")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="reviewed_certificate_assets")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(kind__in=["signature", "stamp"]), name="certificate_asset_kind"),
            models.CheckConstraint(condition=Q(state="pending", reviewed_by__isnull=True, reviewed_at__isnull=True) | Q(state__in=["approved", "rejected"], reviewed_by__isnull=False, reviewed_at__isnull=False), name="certificate_asset_review_evidence"),
        ]

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        if self.pk:
            old = type(self).objects.get(pk=self.pk)
            fields = ("serial", "kind", "image", "sha256", "state", "uploaded_by_id", "reviewed_by_id", "reviewed_at")
            if old.state != "pending" and any(getattr(old, f) != getattr(self, f) for f in fields):
                raise ValidationError("Reviewed certificate assets are immutable; upload a replacement")
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.serial)


class Document(models.Model):
    is_specimen = models.BooleanField(default=True, editable=False)
    serial = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_at = models.DateTimeField(null=True, editable=False)
    kind = models.CharField(max_length=30)
    membership = models.ForeignKey(Membership, on_delete=models.PROTECT, null=True)
    accreditation = models.ForeignKey(
        Accreditation, on_delete=models.PROTECT, null=True
    )
    registration = models.ForeignKey(Registration, on_delete=models.PROTECT, null=True)
    institutional_role = models.ForeignKey(
        InstitutionalRole, on_delete=models.PROTECT, null=True
    )
    version = models.PositiveIntegerField(default=1)
    token_digest = models.CharField(max_length=64, unique=True)
    code_digest = models.CharField(max_length=64)
    subject_name = models.CharField(max_length=200)
    credentials = models.TextField()  # encrypted verification token + printed code
    portrait = models.ForeignKey(Portrait, on_delete=models.PROTECT, null=True)
    signature_asset = models.ForeignKey(CertificateAsset, on_delete=models.PROTECT, null=True, editable=False, related_name="signature_documents")
    stamp_asset = models.ForeignKey(CertificateAsset, on_delete=models.PROTECT, null=True, editable=False, related_name="stamp_documents")
    signing_snapshot = models.JSONField(default=dict, editable=False)
    rendered = models.TextField(blank=True)  # encrypted printable HTML
    rendering_state = models.CharField(max_length=15, default="pending")
    void = models.BooleanField(default=False)
    replaces = models.OneToOneField("self", on_delete=models.PROTECT, null=True)

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        if self.pk:
            old = type(self).objects.get(pk=self.pk)
            if any(getattr(old, f) != getattr(self, f) for f in ("signature_asset_id", "stamp_asset_id", "signing_snapshot", "is_specimen")):
                raise ValidationError("Issuance signing snapshot is immutable; formal reissuance required")
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        membership__isnull=False,
                        accreditation__isnull=True,
                        registration__isnull=True,
                        institutional_role__isnull=True,
                    )
                    | Q(
                        membership__isnull=True,
                        accreditation__isnull=False,
                        registration__isnull=True,
                        institutional_role__isnull=True,
                    )
                    | Q(
                        membership__isnull=True,
                        accreditation__isnull=True,
                        registration__isnull=False,
                        institutional_role__isnull=True,
                    )
                    | Q(
                        membership__isnull=True,
                        accreditation__isnull=True,
                        registration__isnull=True,
                        institutional_role__isnull=False,
                    )
                ),
                name="one_document_origin",
            ),
            models.UniqueConstraint(
                fields=["membership", "kind", "version"],
                name="membership_document_version",
            ),
            models.UniqueConstraint(
                fields=["accreditation", "kind", "version"],
                name="accreditation_document_version",
            ),
            models.UniqueConstraint(
                fields=["registration", "kind", "version"],
                name="registration_document_version",
            ),
            models.UniqueConstraint(
                fields=["institutional_role", "kind", "version"],
                name="institutional_document_version",
            ),
        ]


class Outbox(models.Model):
    document = models.OneToOneField(Document, on_delete=models.PROTECT)
    state = models.CharField(max_length=15, default="pending")
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=60, blank=True)


class Refund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    approved = models.BooleanField()
    reason = models.TextField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="positive_refund")
        ]


class RecoveryCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    digest = models.CharField(max_length=64, unique=True)
    used_at = models.DateTimeField(null=True)


class RateBucket(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)


class PDFArtifact(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.PROTECT, related_name="pdf_artifacts"
    )
    language = models.CharField(
        max_length=2, choices=[("ar", "Arabic"), ("fr", "French"), ("en", "English")]
    )
    template_version = models.CharField(max_length=40)
    payload = (
        models.TextField()
    )  # Fernet-encrypted PDF, immutable after first rendering
    sha256 = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "language"], name="one_pdf_artifact_per_language"
            ),
            models.CheckConstraint(
                condition=Q(language__in=["ar", "fr", "en"]),
                name="supported_pdf_language",
            ),
        ]


class PartnershipRequest(models.Model):
    organization = models.CharField(max_length=200)
    contact_email = models.EmailField()
    message = models.TextField()
    notice_acknowledged = models.BooleanField(default=False)
    state = models.CharField(max_length=12, default="submitted")
    created_at = models.DateTimeField(auto_now_add=True)
    fixture_key = models.CharField(max_length=60, null=True, unique=True, editable=False)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(state__in=["submitted", "approved", "rejected"]), name="partnership_request_state")]


class Partner(models.Model):
    request = models.OneToOneField(PartnershipRequest, on_delete=models.PROTECT)
    name_ar = models.CharField(max_length=200)
    name_fr = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200)
    summary_ar = models.TextField(blank=True)
    summary_fr = models.TextField(blank=True)
    summary_en = models.TextField(blank=True)
    website = models.URLField(blank=True)
    state = models.CharField(max_length=12, default="active")
    public_visible = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(state__in=["active", "suspended", "cancelled"]), name="partner_state"),
            models.CheckConstraint(condition=Q(public_visible=False) | Q(state="active"), name="partner_public_active"),
        ]


class AccreditationCase(models.Model):
    """Restricted independent assessment; never a public verification record."""
    kind = models.CharField(max_length=20)
    person = models.ForeignKey(Person, on_delete=models.PROTECT, null=True, blank=True)
    subject_name = models.CharField(max_length=200, blank=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    private_payload = models.TextField()
    state = models.CharField(max_length=20, default="draft")
    accreditation = models.OneToOneField(Accreditation, on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    fixture_key = models.CharField(max_length=60, null=True, unique=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(kind__in=["individual", "institution", "course"]), name="case_kind"),
            models.CheckConstraint(condition=Q(state__in=["draft", "reviewed", "rejected", "approved"]), name="case_state"),
            models.CheckConstraint(condition=Q(ends_on__gt=models.F("starts_on")), name="case_dates"),
            models.CheckConstraint(condition=(Q(kind="individual", person__isnull=False, subject_name="") | (~Q(kind="individual") & Q(person__isnull=True) & ~Q(subject_name=""))), name="case_subject"),
            models.CheckConstraint(condition=(Q(state="approved", accreditation__isnull=False) | (~Q(state="approved") & Q(accreditation__isnull=True))), name="case_approval_link"),
        ]


class TranslationAttempt(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    key = models.UUIDField()
    digest = models.CharField(max_length=64)
    state = models.CharField(max_length=10, default='pending')
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['actor', 'key'], name='translation_actor_key')]
