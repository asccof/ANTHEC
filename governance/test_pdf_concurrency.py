from unittest import skipUnless
from datetime import date
from django.db import connection, transaction
from django.test import TransactionTestCase
from django.utils import timezone
from . import (
    test_concurrency as helpers,
    services as s,
    pdf_services as pdf,
    portraits as p,
)
from .tests import synthetic_user, administrative_request
from .models import Authority, Person, Portrait, InstitutionalRole, PDFArtifact
import base64, io
from PIL import Image


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class PDFConcurrencyTests(TransactionTestCase):
    concurrent = helpers.ConcurrentPolicyTests.concurrent

    def setUp(self):
        self.admin = synthetic_user("synthetic-director", True)
        Authority.objects.create(primary=self.admin)
        self.person = Person.objects.create(full_name="Synthetic Concurrent Holder")
        raw = io.BytesIO()
        Image.new("RGB", (600, 750), "blue").save(raw, "JPEG")
        self.photo = Portrait.objects.create(
            person=self.person,
            uploaded_by=self.admin,
            image=s.encrypt({"jpeg": base64.b64encode(raw.getvalue()).decode()}),
            state="approved",
            reviewed_by=self.admin,
            reviewed_at=timezone.now(),
        )
        role = InstitutionalRole.objects.create(
            person=self.person,
            role="president",
            starts_on=date(2026, 1, 1),
            ends_on=date(2029, 4, 17),
            legal_reference="SYNTHETIC",
        )
        with transaction.atomic():
            self.doc = s.issue("president_card", institutional_role=role)

    def test_parallel_render_returns_one_immutable_artifact(self):
        results = self.concurrent(
            lambda request, index: {"artifact": pdf.artifact_for(self.doc.pk, "en").pk}
        )
        self.assertEqual(results[0], results[1])
        self.assertEqual(PDFArtifact.objects.count(), 1)

    def test_parallel_review_preserves_one_decision(self):
        self.photo.state = "pending"
        self.photo.reviewed_by = None
        self.photo.reviewed_at = None
        self.photo.save()
        results = self.concurrent(
            lambda request, index: p.review_portrait(
                request,
                key=str(index),
                portrait_id=self.photo.pk,
                decision="approved" if index == 0 else "rejected",
                reason="Synthetic",
            )
        )
        self.assertEqual(sorted(x[0] for x in results), ["conflict", "ok"])
