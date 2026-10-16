from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from django.core.exceptions import ValidationError
from .tests import synthetic_user
from .intake_test_support import intake_payload
from . import member_services as m, services as s
from .models import Application, Portrait, Audit, Membership
from .intake import validate_addresses


class ApplicationPhotoTests(TestCase):
    def setUp(self):
        call_command("seed_policy_prices", stdout=StringIO())
        self.user = synthetic_user("synthetic-photo-intake")
        self.client.force_login(self.user)
        m.update_profile(
            self.user,
            key="profile",
            full_name="Synthetic Photo",
            contact="photo@example.invalid",
            phone="0000000000",
            profession="Synthetic coach",
            directory_consent=False,
            notice=True,
        )

    def test_atomic_upload_replay_and_private_addresses(self):
        payload = dict(
            intake_payload(),
            tier="general",
            applicant_capacity="interested",
            key="apply",
        )
        result = m.submit_application(self.user, **payload)
        self.assertEqual(m.submit_application(self.user, **payload), result)
        self.assertEqual(Portrait.objects.count(), 1)
        app = Application.objects.get()
        self.assertEqual(app.intake_portrait.state, "pending")
        self.assertEqual(app.residential_address, "Synthetic residence 01")
        self.assertNotIn(
            "Synthetic residence", str(list(Audit.objects.values("details")))
        )
        self.assertContains(
            self.client.get(f"/members/applications/{app.pk}/"),
            "Synthetic residence 01",
        )
        self.client.force_login(synthetic_user("synthetic-stranger-photo"))
        self.assertEqual(
            self.client.get(f"/members/applications/{app.pk}/").status_code, 404
        )
        self.assertEqual(
            self.client.get(
                f"/private-portraits/{app.intake_portrait.serial}/"
            ).status_code,
            404,
        )

    def test_invalid_photo_rolls_back_application_and_portrait(self):
        payload = intake_payload()
        payload["image_data"] = "invalid"
        with self.assertRaises(ValidationError):
            m.submit_application(
                self.user,
                key="invalid",
                tier="general",
                applicant_capacity="interested",
                **payload,
            )
        self.assertFalse(Application.objects.exists())
        self.assertFalse(Portrait.objects.exists())

    def test_address_branches(self):
        self.assertEqual(
            validate_addresses("professional", "Synthetic office", "", "", True)[2],
            "Synthetic office",
        )
        for args in [
            ("professional", "", "", "", False),
            ("beneficiary", "hidden office", "", "home", False),
            ("beneficiary", "", "", "", False),
            ("invalid", "", "", "home", False),
        ]:
            with self.assertRaises(ValidationError):
                validate_addresses(*args)

    def test_form_requires_photo_consent_and_addresses_in_each_locale(self):
        for lang in ("ar", "fr", "en"):
            response = self.client.get("/members/apply/?lang=" + lang)
            self.assertContains(response, 'enctype="multipart/form-data"')
            self.assertContains(response, 'name="photo"')
            self.assertContains(response, 'name="address_category"')
        response = self.client.post(
            "/members/apply/",
            dict(
                key="00000000-0000-0000-0000-000000000001",
                tier="general",
                applicant_capacity="interested",
            ),
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Application.objects.exists())

    def test_approval_waits_for_review_and_replacement_binds_first_card(self):
        from .models import Authority, Document
        from .tests import administrative_request
        from . import portraits
        import uuid

        admin = synthetic_user("synthetic-photo-admin", True)
        Authority.objects.create(primary=admin)
        request = administrative_request(admin)
        m.submit_application(
            self.user,
            key="apply",
            tier="accredited",
            applicant_capacity="coach",
            **intake_payload(),
        )
        app = Application.objects.get()
        s.exempt_fee(
            request, key="exempt", application_id=app.pk, reason="Synthetic exemption"
        )
        with self.assertRaises(ValidationError):
            s.approve_membership(
                request,
                key="approve",
                application_id=app.pk,
                reason="Synthetic approval",
            )
        self.assertFalse(Membership.objects.exists())
        portraits.review_portrait(
            request,
            key="reject",
            portrait_id=app.intake_portrait_id,
            decision="rejected",
            reason="Synthetic rejection",
        )
        replacement = portraits.upload_portrait(
            self.user,
            key="replace",
            person_id=app.person_id,
            image_data=intake_payload()["image_data"],
            consent=True,
        )
        app.refresh_from_db()
        self.assertEqual(str(app.intake_portrait.serial), replacement["portrait"])
        portraits.review_portrait(
            request,
            key="accept",
            portrait_id=app.intake_portrait_id,
            decision="approved",
            reason="Synthetic accepted",
        )
        result = s.approve_membership(
            request, key="approve", application_id=app.pk, reason="Synthetic approval"
        )
        card = Document.objects.get(pk__in=result["documents"], kind="gold_card")
        self.assertEqual(card.portrait_id, app.intake_portrait_id)
        self.assertEqual(len(result["documents"]), 2)
        # Later uploads cannot rewrite approved applications or issued snapshots.
        portraits.upload_portrait(
            self.user,
            key="later",
            person_id=app.person_id,
            image_data=intake_payload()["image_data"],
            consent=True,
        )
        card.refresh_from_db()
        app.refresh_from_db()
        self.assertEqual(card.portrait_id, app.intake_portrait_id)
