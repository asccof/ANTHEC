"""Behavioral separation, direct-route bypasses, revocation and legacy conversion."""

import base64
import importlib
import uuid
from io import StringIO
from django.apps import apps
from django.contrib.auth.models import Permission, Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.utils import timezone
from . import services as s, certificate_assets as signing
from .capabilities import ALL_CAPABILITIES, validate_capabilities, action_capabilities
from .models import (
    Authority,
    Delegation,
    Person,
    Application,
    Membership,
    Payment,
    Audit,
    CertificateAsset,
)
from .tests import synthetic_user, administrative_request
from . import tests as fixtures
from .test_certificate_assets import raw_fixture


class ScopedDelegationTests(TestCase):
    http_login = fixtures.PolicyTests.http_login

    def setUp(self):
        self.admin = synthetic_user("synthetic-scopes-owner", True)
        Authority.objects.create(primary=self.admin)
        self.delegate = synthetic_user("synthetic-scopes-delegate")
        self.request = administrative_request(self.admin)
        self.person = Person.objects.create(
            full_name="Synthetic scopes holder", verification_notice_at=timezone.now()
        )
        call_command("seed_policy_prices", stdout=StringIO())

    def grant(self, capabilities):
        s.delegate(
            self.request,
            key=str(uuid.uuid4()),
            user_id=self.delegate.pk,
            active=True,
            capabilities=list(capabilities),
            reason="Synthetic explicit grant",
        )
        self.row = Delegation.objects.get(user=self.delegate)
        return administrative_request(self.delegate, self.row.epoch)

    def login(self):
        self.http_login(user=self.delegate, epoch=self.row.epoch)

    def test_no_default_grants_unknown_and_missing_view_fail_closed(self):
        for capabilities in (
            None,
            [],
            ["membership.approve"],
            ["membership.view", "delegate"],
            ["membership.view"] * 2,
            {"membership.view": True},
        ):
            with self.subTest(capabilities=capabilities), self.assertRaises(
                ValidationError
            ):
                s.delegate(
                    self.request,
                    key=str(uuid.uuid4()),
                    user_id=self.delegate.pk,
                    active=True,
                    capabilities=capabilities,
                    reason="Synthetic invalid",
                )
        self.assertFalse(Delegation.objects.exists())
        self.assertEqual(
            len(validate_capabilities(list(ALL_CAPABILITIES))), len(ALL_CAPABILITIES)
        )

    def test_actual_approval_cannot_reject_suspend_or_cancel_via_json(self):
        app = s.create_application(self.person, "general")
        s.exempt_fee(
            self.request,
            key="exempt",
            application_id=app.pk,
            reason="Synthetic exemption",
        )
        self.grant(["membership.view", "membership.approve"])
        self.login()
        denied = self.client.post(
            "/operations/membership.reject/",
            dict(key="reject", application_id=app.pk, reason="Synthetic forbidden"),
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(
            self.client.post(
                "/operations/membership.approve/",
                dict(key="approve", application_id=app.pk, reason="Synthetic approval"),
                content_type="application/json",
            ).status_code,
            200,
        )
        term = Membership.objects.get(application=app)
        for state in ("suspended", "cancelled", "active"):
            self.assertEqual(
                self.client.post(
                    "/operations/right.state/",
                    dict(
                        key=state,
                        model="membership",
                        object_id=term.pk,
                        state=state,
                        reason="Synthetic denied",
                    ),
                    content_type="application/json",
                ).status_code,
                403,
            )
        term.refresh_from_db()
        self.assertEqual(term.state, "active")
        self.assertFalse(Audit.objects.filter(action="membership.rejected").exists())

    def test_action_decisions_use_distinct_capabilities(self):
        pairs = [
            (
                "portrait.review",
                {"decision": "approved"},
                "portrait.approve",
                "portrait.reject",
            ),
            (
                "certificate.asset.review",
                {"decision": "rejected"},
                "signing.reject",
                "signing.approve",
            ),
            (
                "partnership.decide",
                {"decision": "approved"},
                "partner.approve",
                "partner.reject",
            ),
            (
                "registration.decide",
                {"accept": False},
                "registration.reject",
                "registration.approve",
            ),
            (
                "refund.decide",
                {"approved": False},
                "finance.refund_reject",
                "finance.refund_approve",
            ),
            (
                "institutional.state",
                {"state": "terminated"},
                "institutional.terminate",
                "institutional.cancel",
            ),
            (
                "right.state",
                {"model": "membership", "state": "suspended"},
                "membership.suspend",
                "membership.cancel",
            ),
        ]
        for action, payload, allowed, forbidden in pairs:
            self.assertEqual(action_capabilities(action, payload), [allowed])
            self.assertNotEqual(allowed, forbidden)
        for suffix in ("activate", "suspend", "cancel"):
            state = {
                "activate": "active",
                "suspend": "suspended",
                "cancel": "cancelled",
            }[suffix]
            self.assertEqual(
                action_capabilities(
                    "right.state", {"model": "accreditation", "state": state}
                ),
                ["accreditation." + suffix],
            )

    def test_mixed_membership_view_does_not_disclose_finance_or_documents(self):
        app = s.create_application(self.person, "general")
        s.verify_payment(
            self.request,
            key="payment",
            application_id=app.pk,
            amount="100",
            method="cash",
            proof_reference="PRIVATE-SCOPED-PROOF",
        )
        s.approve_membership(
            self.request, key="approve", application_id=app.pk, reason="Synthetic"
        )
        self.grant(["membership.view"])
        self.login()
        page = self.client.get(f"/operations/membership/{app.pk}/?lang=en")
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "PRIVATE-SCOPED-PROOF")
        self.assertFalse(page.context["payments"].exists())
        self.assertEqual(page.context["documents"], [])
        self.assertNotContains(page, 'name="action" value="approve"')
        for url in (
            "/operations/pricing/",
            "/operations/portraits/",
            "/operations/activities/",
            "/operations/partners/",
            "/operations/accreditation/",
            "/operations/institutional/",
            "/operations/membership/identities/",
            "/operations/directors/",
            "/operations/certificate-assets/",
        ):
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_scope_change_revokes_old_session_and_replay_before_command_lookup(self):
        req = self.grant(["pricing.view", "pricing.edit"])
        starts = (timezone.now() + timezone.timedelta(days=2)).isoformat()
        payload = dict(
            tier="general", amount="200", starts_at=starts, reason="Synthetic"
        )
        s.change_price(req, key="replayed", **payload)
        self.login()
        self.grant(["membership.view"])
        self.assertEqual(self.client.get("/operations/pricing/").status_code, 302)
        with self.assertRaises(PermissionDenied):
            s.change_price(req, key="replayed", **payload)
        self.login()
        with self.assertRaises(PermissionDenied):
            s.change_price(
                administrative_request(self.delegate, self.row.epoch),
                key="replayed",
                **payload,
            )
        audit = Audit.objects.filter(action="delegation.changed").latest("pk")
        self.assertIn("pricing.edit", audit.details["before"]["capabilities"])
        self.assertEqual(audit.details["capabilities"], ["membership.view"])

    def test_signing_approval_does_not_grant_upload_rejection_or_delegation(self):
        raw = base64.b64encode(raw_fixture()).decode()
        one = signing.upload_asset(
            self.request,
            key="one",
            kind="signature",
            image_data=raw,
            reason="Synthetic",
        )
        two = signing.upload_asset(
            self.request, key="two", kind="stamp", image_data=raw, reason="Synthetic"
        )
        first = CertificateAsset.objects.get(serial=one["asset"])
        second = CertificateAsset.objects.get(serial=two["asset"])
        req = self.grant(["signing.view", "signing.approve"])
        self.login()
        page = self.client.get("/operations/certificate-assets/?lang=en")
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'name="action" value="upload"')
        self.assertEqual(
            list(page.context["review_form"].fields["decision"].choices),
            [("approved", "Approve")],
        )
        signing.review_asset(
            req,
            key="approve",
            asset_id=first.pk,
            decision="approved",
            reason="Synthetic",
        )
        with self.assertRaises(PermissionDenied):
            signing.review_asset(
                req,
                key="reject",
                asset_id=second.pk,
                decision="rejected",
                reason="Synthetic",
            )
        with self.assertRaises(PermissionDenied):
            signing.upload_asset(
                req, key="upload", kind="stamp", image_data=raw, reason="Synthetic"
            )
        with self.assertRaises(PermissionDenied):
            s.delegate(
                req,
                key="escalate",
                user_id=self.delegate.pk,
                active=False,
                reason="Synthetic",
            )
        second.refresh_from_db()
        self.assertEqual(second.state, "pending")

    def test_viewing_document_does_not_allow_download_generate_or_reissue(self):
        app = s.create_application(self.person, "founder")
        result = s.approve_membership(
            self.request, key="approve", application_id=app.pk, reason="Synthetic"
        )
        doc_id = result["documents"][0]
        self.grant(["document.view"])
        self.login()
        self.assertEqual(
            self.client.get(f"/my-documents/{doc_id}/preview/").status_code, 409
        )
        self.assertEqual(self.client.get(f"/my-documents/{doc_id}/").status_code, 404)
        self.assertEqual(
            self.client.get(f"/my-documents/{doc_id}/pdf/").status_code, 404
        )
        self.assertEqual(
            self.client.post(f"/my-documents/{doc_id}/prepare/").status_code, 404
        )
        self.assertEqual(
            self.client.post(
                "/operations/document.replace/",
                dict(key="replace", document_id=doc_id, reason="Synthetic"),
                content_type="application/json",
            ).status_code,
            403,
        )

    def test_read_only_cms_and_unknown_paths_deny_even_unrelated_django_permissions(
        self,
    ):
        call_command("seed_demo", stdout=StringIO())
        from content.models import InstitutionalPage

        page = InstitutionalPage.objects.first()
        self.grant(["content.view"])
        self.login()
        self.delegate.user_permissions.set(Permission.objects.all())
        self.assertEqual(self.client.get("/admin/pages/").status_code, 200)
        for url, data in [
            (
                f"/admin/pages/{page.pk}/edit/",
                {"title": "FORBIDDEN", "action-publish": "1"},
            ),
            (f"/admin/pages/{page.pk}/delete/", {}),
            ("/admin/users/", {}),
            ("/admin/groups/", {}),
            ("/admin/settings/content/publiccontact/", {}),
            ("/admin/images/add/", {}),
            (f"/admin/pages/{page.pk}/copy/", {}),
        ]:
            self.assertEqual(self.client.post(url, data).status_code, 403, url)
        self.assertEqual(
            self.client.get("/admin/settings/content/publiccontact/").status_code, 403
        )
        self.assertEqual(self.client.get("/admin/").url, "/operations/workspace/")
        page.refresh_from_db()
        self.assertNotEqual(page.title, "FORBIDDEN")

    def test_saved_draft_publish_is_independent_from_edit(self):
        call_command("seed_demo", stdout=StringIO())
        from content.models import InstitutionalPage
        from .content_operations import publish_saved

        page = InstitutionalPage.objects.first()
        page.title = "Synthetic saved draft"
        revision = page.save_revision()
        req = self.grant(["content.view", "content.publish"])
        self.login()
        self.assertEqual(
            self.client.post(
                f"/admin/pages/{page.pk}/edit/", {"title": "FORBIDDEN"}
            ).status_code,
            403,
        )
        publish_saved(
            req,
            key="publish",
            page_id=page.pk,
            revision_id=revision.pk,
            reason="Synthetic saved revision approval",
        )
        page.refresh_from_db()
        self.assertEqual(page.live_revision_id, revision.pk)
        self.assertEqual(page.title, "Synthetic saved draft")
        with self.assertRaises(ValidationError):
            publish_saved(
                req,
                key="stale",
                page_id=page.pk,
                revision_id=revision.pk + 1,
                reason="Synthetic",
            )

    def test_director_form_preselects_only_existing_explicit_grant_and_blocks_stale_edit(
        self,
    ):
        self.grant(["membership.view", "membership.reject"])
        self.http_login()
        response = self.client.get(
            f"/operations/directors/?lang=fr&user={self.delegate.pk}"
        )
        self.assertEqual(
            set(response.context["form"]["capabilities"].value()),
            {"membership.view", "membership.reject"},
        )
        for payload in (
            dict(capabilities=[]),
            dict(capabilities=["membership.approve"]),
            dict(expected_epoch=0),
        ):
            data = dict(
                user=self.delegate.pk,
                key=str(uuid.uuid4()),
                decision="grant",
                reason="Synthetic",
                confirm=True,
                capabilities=["membership.view"],
                expected_epoch=self.row.epoch,
            )
            data.update(payload)
            self.assertEqual(
                self.client.post("/operations/directors/", data).status_code, 400
            )
        self.row.refresh_from_db()
        self.assertEqual(
            set(self.row.capabilities), {"membership.view", "membership.reject"}
        )

    def test_legacy_conversion_revokes_grant_and_removes_old_group(self):
        # Exercise the same forward transition against ORM-compatible historical fields.
        row = Delegation.objects.create(user=self.delegate, active=True, epoch=7)
        group = Group.objects.create(name="ANTHEEC operational directors")
        self.delegate.groups.add(group)
        operation = importlib.import_module(
            "governance.migrations.0012_scoped_delegation"
        )
        from types import SimpleNamespace

        operation.close_legacy_grants(apps, SimpleNamespace(connection=connection))
        row.refresh_from_db()
        self.assertFalse(row.active)
        self.assertEqual(row.epoch, 8)
        self.assertEqual(row.capabilities, [])
        self.assertFalse(self.delegate.groups.filter(pk=group.pk).exists())

    def test_case_reviewer_cannot_edit_assessment_or_approve(self):
        from . import accreditation_services as case_service
        from .models import AccreditationCase

        data = dict(
            kind="individual",
            person_id=self.person.pk,
            subject_name="",
            starts_on="2026-10-18",
            ends_on="2027-10-18",
            criteria="Synthetic criteria",
            assessment="Synthetic assessment",
            fee="300",
            reason="Synthetic case",
        )
        result = case_service.create(self.request, key="case", **data)
        req = self.grant(["accreditation.view", "accreditation.review"])
        payload = dict(
            case_id=result["case"],
            decision="reviewed",
            criteria="Synthetic criteria",
            assessment="CHANGED-UNAUTHORIZED",
            fee="300",
            reason="Synthetic review",
        )
        with self.assertRaises(PermissionDenied):
            case_service.review(req, key="tampered", **payload)
        payload["assessment"] = "Synthetic assessment"
        case_service.review(req, key="review", **payload)
        row = AccreditationCase.objects.get(pk=result["case"])
        self.assertEqual(row.state, "reviewed")
        with self.assertRaises(PermissionDenied):
            case_service.approve(req, key="approve", case_id=row.pk, reason="Synthetic")
        with self.assertRaises(PermissionDenied):
            case_service.review(req, key="reopen", **{**payload, "decision": "draft"})

    def test_partner_state_and_content_and_public_visibility_are_independent(self):
        from .models import PartnershipRequest, Partner
        from . import partner_services

        application = PartnershipRequest.objects.create(
            organization="Synthetic partner",
            contact_email="partner@example.invalid",
            message="Synthetic",
            notice_acknowledged=True,
            state="approved",
        )
        row = Partner.objects.create(
            request=application,
            name_ar="Synthetic",
            name_fr="Synthetic",
            name_en="Synthetic",
            public_visible=True,
        )
        content = {
            f: getattr(row, f)
            for f in (
                "name_ar",
                "name_fr",
                "name_en",
                "summary_ar",
                "summary_fr",
                "summary_en",
                "website",
            )
        }
        req = self.grant(["partner.view", "partner.suspend"])
        with self.assertRaises(PermissionDenied):
            partner_services.update(
                req,
                key="hide-implicit",
                partner_id=row.pk,
                state="suspended",
                public_visible=False,
                reason="Synthetic",
                **content,
            )
        req = self.grant(["partner.view", "partner.suspend", "partner.hide"])
        with self.assertRaises(PermissionDenied):
            partner_services.update(
                req,
                key="edit-implicit",
                partner_id=row.pk,
                state="suspended",
                public_visible=False,
                reason="Synthetic",
                **{**content, "name_en": "Changed"},
            )
        partner_services.update(
            req,
            key="suspend-and-hide",
            partner_id=row.pk,
            state="suspended",
            public_visible=False,
            reason="Synthetic",
            **content,
        )
        row.refresh_from_db()
        self.assertEqual(row.state, "suspended")
        self.assertFalse(row.public_visible)

    def test_contact_and_media_read_only_scopes_do_not_allow_mutations(self):
        call_command("seed_demo", stdout=StringIO())
        self.grant(["contact.view", "media_image.view", "media_document.view"])
        self.login()
        self.assertEqual(
            self.client.get("/admin/settings/content/publiccontact/").status_code, 302
        )
        for url in (
            "/admin/settings/content/publiccontact/",
            "/admin/images/add/",
            "/admin/documents/add/",
        ):
            self.assertEqual(self.client.post(url, {}).status_code, 403, url)
        self.assertEqual(self.client.get("/admin/images/").status_code, 200)
        self.assertEqual(self.client.get("/admin/documents/").status_code, 200)

    def test_revocation_does_not_require_irrelevant_checked_scope_prerequisites(self):
        self.grant(["membership.view", "membership.approve"])
        s.delegate(
            self.request,
            key="revoke-partial-checkboxes",
            user_id=self.delegate.pk,
            active=False,
            capabilities=["membership.approve"],
            reason="Synthetic revoke",
        )
        row = Delegation.objects.get(user=self.delegate)
        self.assertFalse(row.active)
        self.assertEqual(row.capabilities, [])

    def test_refund_rejection_and_approval_are_independent_actual_commands(self):
        app = s.create_application(self.person, "general")
        result = s.verify_payment(
            self.request,
            key="paid",
            application_id=app.pk,
            amount="100",
            method="cash",
            proof_reference="Synthetic",
        )
        payment = Payment.objects.get(application=app)
        req = self.grant(["membership.view", "finance.view", "finance.refund_reject"])
        payload = dict(payment_id=payment.pk, amount="20", reason="Synthetic")
        with self.assertRaises(PermissionDenied):
            s.decide_refund(req, key="approve", approved=True, **payload)
        s.decide_refund(req, key="reject", approved=False, **payload)
        from .models import Refund

        self.assertEqual(Refund.objects.count(), 1)
        self.assertFalse(Refund.objects.get().approved)

    def test_document_only_registry_and_generation_do_not_force_download(self):
        from unittest.mock import patch

        app = s.create_application(self.person, "founder")
        result = s.approve_membership(
            self.request, key="approve", application_id=app.pk, reason="Synthetic"
        )
        doc_id = result["documents"][0]
        self.grant(["document.view", "document.generate"])
        self.login()
        page = self.client.get("/operations/documents/?lang=en")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Synthetic scopes holder")
        self.assertNotContains(page, "Download document")
        with patch("governance.pdf_services.artifact_for") as generate:
            response = self.client.post(f"/my-documents/{doc_id}/prepare/?lang=en")
        generate.assert_called_once_with(doc_id, "en")
        self.assertEqual(response.url, f"/operations/documents/{doc_id}/?lang=en")

    def test_contact_view_does_not_create_settings_or_grant_native_edit_permission(
        self,
    ):
        from content.models import PublicContact

        PublicContact.objects.all().delete()
        self.grant(["contact.view"])
        self.login()
        response = self.client.get("/operations/contact/?lang=en")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PublicContact.objects.exists())
        self.assertFalse(self.delegate.has_perm("content.change_publiccontact"))
        native = self.client.get("/admin/settings/content/publiccontact/")
        self.assertEqual(native.url, "/operations/contact/")
        self.assertFalse(PublicContact.objects.exists())
