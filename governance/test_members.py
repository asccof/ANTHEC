from .intake_test_support import intake_payload
from django.core.files.uploadedfile import SimpleUploadedFile
import base64

"""Synthetic account/profile/submission boundary regressions."""

from io import StringIO
import uuid
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.exceptions import PermissionDenied
from django.test import TestCase, Client
from django.utils import timezone
from .tests import synthetic_user
from . import member_services as m, services as s
from .member_labels import vocabulary
from .models import Person, Application, Audit, Command, RateBucket


class MemberTests(TestCase):
    def setUp(self):
        call_command("seed_policy_prices", stdout=StringIO())
        self.user = synthetic_user("synthetic-member")
        self.client.force_login(self.user)

    def profile(self, **changes):
        data = dict(
            key=str(uuid.uuid4()),
            full_name="Synthetic Member",
            phone="+212600000001",
            profession="Synthetic coach",
            contact="synthetic@example.invalid",
            directory_consent=False,
            notice=True,
        )
        data.update(changes)
        return m.update_profile(self.user, **data)

    def test_signup_login_logout_password_and_no_privileges(self):
        client = Client()
        response = client.post(
            "/members/signup/?lang=fr",
            {
                "username": "synthetic-new",
                "password1": "Synthetic-long-567!pass",
                "password2": "Synthetic-long-567!pass",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username="synthetic-new")
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertFalse(user.groups.exists())
        self.assertEqual(Person.objects.count(), 0)
        self.assertEqual(client.get("/members/logout/").status_code, 405)
        self.assertEqual(client.post("/members/logout/").status_code, 302)
        self.assertEqual(
            client.post(
                "/members/login/", {"username": user.username, "password": "Wrong"}
            ).status_code,
            400,
        )
        self.assertEqual(
            client.post(
                "/members/login/",
                {"username": user.username, "password": "Synthetic-long-567!pass"},
            ).status_code,
            302,
        )
        response = client.post(
            "/members/password/",
            {
                "old_password": "Synthetic-long-567!pass",
                "new_password1": "Cedar-ocean-456!pass",
                "new_password2": "Cedar-ocean-456!pass",
            },
        )
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password("Cedar-ocean-456!pass"))
        self.assertEqual(client.get("/members/").status_code, 200)
        for action in [
            "member.account.created",
            "member.account.failed",
            "member.account.login",
            "member.account.logout",
            "member.password.changed",
        ]:
            self.assertTrue(Audit.objects.filter(action=action).exists())
        self.assertEqual(client.get("/operations/institutional/").status_code, 403)

    def test_password_validation_and_auth_throttle(self):
        self.client.logout()
        self.assertEqual(
            self.client.post(
                "/members/signup/",
                {"username": "synthetic-weak", "password1": "123", "password2": "123"},
            ).status_code,
            400,
        )
        for _ in range(9):
            self.client.post(
                "/members/login/",
                {"username": "nonexistent-synthetic", "password": "bad"},
            )
        self.assertEqual(
            self.client.post(
                "/members/login/",
                {"username": "nonexistent-synthetic", "password": "bad"},
            ).status_code,
            429,
        )
        self.assertEqual(RateBucket.objects.count(), 1)
        self.assertFalse(
            get_user_model().objects.filter(username="synthetic-weak").exists()
        )

    def test_profile_create_update_and_replay_preserve_one_person(self):
        first = self.profile(key="same")
        self.assertEqual(first, self.profile(key="same"))
        self.profile(full_name="Synthetic Corrected", directory_consent=True)
        self.assertEqual(Person.objects.count(), 1)
        person = Person.objects.get(user=self.user)
        self.assertEqual(person.full_name, "Synthetic Corrected")
        self.assertTrue(person.directory_consent)
        self.profile(directory_consent=False)
        self.assertFalse(Person.objects.get(pk=person.pk).directory_consent)
        self.assertEqual(
            Audit.objects.filter(action="member.profile.created").count(), 1
        )
        self.assertEqual(
            Audit.objects.filter(action="member.profile.updated").count(), 2
        )
        self.assertNotIn(
            "synthetic@example.invalid", str(list(Audit.objects.values("details")))
        )

    def test_existing_linked_person_reused_and_managed_identity_protected(self):
        person = Person.objects.create(
            user=self.user,
            full_name="Existing Synthetic",
            verification_notice_at=timezone.now(),
        )
        self.profile()
        self.assertEqual(Person.objects.get().pk, person.pk)
        person.minor = True
        person.save(update_fields=["minor"])
        with self.assertRaises(PermissionDenied):
            self.profile()
        person.refresh_from_db()
        self.assertTrue(person.minor)

    def test_application_quote_idempotency_duplicate_and_ownership(self):
        self.profile()
        result = m.submit_application(
            self.user,
            **intake_payload(),
            applicant_capacity="interested",
            tier="accredited",
            key="application",
        )
        self.assertEqual(
            result,
            m.submit_application(
                self.user,
                **intake_payload(),
                applicant_capacity="interested",
                tier="accredited",
                key="application",
            ),
        )
        with self.assertRaises(s.Conflict):
            m.submit_application(
                self.user,
                **intake_payload(),
                applicant_capacity="interested",
                tier="general",
                key="application",
            )
        with self.assertRaises(s.Conflict):
            m.submit_application(
                self.user,
                **intake_payload(),
                applicant_capacity="interested",
                tier="general",
                key="other",
            )
        app = Application.objects.get()
        self.assertEqual(str(app.quote), "3000.00")
        self.assertEqual(app.state, "submitted")
        self.assertTrue(
            Audit.objects.filter(
                action="member.application.submitted",
                subject=str(app.pk),
                actor=self.user,
            ).exists()
        )
        stranger = synthetic_user("synthetic-stranger")
        self.client.force_login(stranger)
        response = self.client.get("/members/")
        self.assertNotContains(response, "3000")
        self.assertNotContains(response, "Synthetic Member")
        self.assertEqual(self.client.get("/my-documents/1/").status_code, 404)

    def test_ui_notice_required_and_account_ids_cannot_select_someone_else(self):
        self.assertEqual(self.client.get("/members/apply/").status_code, 302)
        data = dict(
            key=str(uuid.uuid4()),
            full_name="Synthetic Own",
            phone="+212600000001",
            profession="Synthetic coach",
            contact="own@example.invalid",
        )
        self.assertEqual(self.client.post("/members/profile/", data).status_code, 400)
        self.assertFalse(Person.objects.exists())
        other = Person.objects.create(full_name="Synthetic Other")
        data.update(
            notice="on", user_id=999, person_id=other.pk, minor="on", is_superuser="on"
        )
        self.assertEqual(self.client.post("/members/profile/", data).status_code, 302)
        person = Person.objects.get(user=self.user)
        self.assertNotEqual(person.pk, other.pk)
        self.assertFalse(person.minor)
        self.assertEqual(
            self.client.post(
                "/members/apply/",
                {
                    "key": str(uuid.uuid4()),
                    "tier": "affiliate",
                    "applicant_capacity": "coach",
                    "person_id": other.pk,
                    "address_category": "professional",
                    "correspondence_address": "Synthetic office",
                    "same_address": "on",
                    "photo_consent": "on",
                    "photo": __import__(
                        "django.core.files.uploadedfile",
                        fromlist=["SimpleUploadedFile"],
                    ).SimpleUploadedFile(
                        "synthetic.png",
                        base64.b64decode(intake_payload()["image_data"]),
                        content_type="image/png",
                    ),
                },
            ).status_code,
            302,
        )
        self.assertEqual(Application.objects.get().person_id, person.pk)

    def test_csrf_anonymous_cache_locales_and_xss(self):
        self.client.logout()
        self.assertEqual(self.client.get("/members/").status_code, 302)
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/members/signup/", {}).status_code, 403)
        client.force_login(self.user)
        self.assertEqual(client.post("/members/profile/", {}).status_code, 403)
        self.profile(full_name="<script>synthetic</script>")
        self.client.force_login(self.user)
        for language in ["ar", "fr", "en"]:
            for path in ["/", "/profile/", "/apply/", "/password/"]:
                response = self.client.get("/members" + path + "?lang=" + language)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'lang="{language}"')
                self.assertIn("no-store", response["Cache-Control"])
            self.assertNotContains(
                self.client.get("/members/"), "<script>synthetic</script>"
            )
        self.assertFalse(
            Command.objects.filter(
                actor=self.user, action__startswith="institutional."
            ).exists()
        )

    def test_inactive_user_and_payload_conflict_cannot_mutate(self):
        self.profile(key="profile")
        with self.assertRaises(s.Conflict):
            self.profile(key="profile", full_name="Changed")
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            self.profile()

    def test_member_password_path_cannot_bypass_director_mfa(self):
        from .models import Authority, Delegation
        from . import tests as fixtures

        self.admin = synthetic_user("synthetic-password-director", True)
        Authority.objects.create(primary=self.admin)
        payload = {
            "old_password": "synthetic-password-123",
            "new_password1": "Cedar-ocean-456!pass",
            "new_password2": "Cedar-ocean-456!pass",
        }
        for user in [self.admin, self.user]:
            if user == self.user:
                Delegation.objects.create(user=user, active=True, capabilities=["membership.view"])
            self.client.force_login(user)
            if user == self.admin:
                self.assertEqual(self.client.post("/members/password/", payload).status_code, 403)
                user.refresh_from_db()
                self.assertTrue(user.check_password("synthetic-password-123"))
                fixtures.PolicyTests.http_login(self, user=user, epoch=0)
            else:
                self.assertNotIn("otp_device_id", self.client.session)
            self.assertEqual(
                self.client.post("/members/password/", payload).status_code, 302
            )
            self.assertNotIn("reauth_at", self.client.session)
        self.assertEqual(
            Audit.objects.filter(action="member.password.denied").count(), 1
        )
