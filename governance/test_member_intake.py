"""Synthetic owner-approved intake and browser verification boundary checks."""

from io import StringIO
import uuid
from bs4 import BeautifulSoup
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from .tests import synthetic_user
from .models import Application, Person, Audit
from . import member_services as m, services as s
from .intake import CAPACITIES
from .member_labels import vocabulary


class IntakeTests(TestCase):
    def setUp(self):
        call_command("seed_policy_prices", stdout=StringIO())
        self.user = synthetic_user("synthetic-intake")
        self.client.force_login(self.user)
        m.update_profile(
            self.user,
            key="profile",
            full_name="Synthetic Intake",
            contact="intake@example.invalid",
            directory_consent=False,
            notice=True,
            phone="+212600000001",
            profession="Synthetic specialism",
        )

    def test_all_declared_capacities_and_other_validation(self):
        for value in CAPACITIES:
            with self.subTest(value=value):
                result = m.submit_application(
                    self.user,
                    key=value,
                    tier="affiliate",
                    applicant_capacity=value,
                    capacity_other="Synthetic other" if value == "other" else "",
                )
                app = Application.objects.get(pk=result["application"])
                self.assertEqual(app.applicant_capacity, value)
                self.assertEqual(app.profession_snapshot, "Synthetic specialism")
                self.assertEqual(app.quote, 500)
                self.assertEqual(app.state, "submitted")
                self.assertFalse(self.user.is_staff or self.user.is_superuser)
                app.state = "rejected"
                app.save(update_fields=["state"])
        for value, other in [("invalid", ""), ("other", ""), ("coach", "unexpected")]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                m.submit_application(
                    self.user,
                    key=str(uuid.uuid4()),
                    tier="general",
                    applicant_capacity=value,
                    capacity_other=other,
                )

    def test_profile_phone_validation_private_data_and_immutable_application_declaration(
        self,
    ):
        result = m.submit_application(
            self.user,
            key="apply",
            tier="general",
            applicant_capacity="psychological_counsellor",
        )
        for bad in ["", "abc", "12", "1" * 16, "12\n3456789"]:
            with self.subTest(phone=bad), self.assertRaises(ValidationError):
                m.update_profile(
                    self.user,
                    key=str(uuid.uuid4()),
                    full_name="Synthetic Intake",
                    contact="",
                    directory_consent=False,
                    notice=True,
                    phone=bad,
                )
        m.update_profile(
            self.user,
            key="change",
            full_name="Synthetic Intake",
            contact="",
            directory_consent=False,
            notice=True,
            profession="Changed synthetic profession",
        )
        app = Application.objects.get(pk=result["application"])
        self.assertEqual(app.profession_snapshot, "Synthetic specialism")
        self.assertNotIn("+212600000001", str(list(Audit.objects.values("details"))))
        self.assertNotIn(
            "Synthetic specialism", str(list(Audit.objects.values("details")))
        )
        stranger = Client()
        stranger.force_login(synthetic_user("synthetic-other-intake"))
        self.assertEqual(
            stranger.get(f"/members/applications/{app.pk}/").status_code, 404
        )
        self.assertNotContains(stranger.get("/members/"), "+212600000001")

    def test_required_browser_fields_locales_and_escaped_declared_other(self):
        for lang in ("ar", "fr", "en"):
            _, labels = vocabulary(lang)
            for url, label in [
                ("/members/profile/", "save_profile"),
                ("/members/apply/", "submit_application"),
            ]:
                response = self.client.get(url + "?lang=" + lang)
                self.assertContains(response, labels[label])
            response = self.client.get("/members/apply/?lang=" + lang)
            for value in CAPACITIES:
                self.assertContains(response, f'value="{value}"')
        bad = self.client.post(
            "/members/apply/", {"key": str(uuid.uuid4()), "tier": "affiliate"}
        )
        self.assertEqual(bad.status_code, 400)
        self.assertFalse(Application.objects.exists())
        result = m.submit_application(
            self.user,
            key="other",
            tier="general",
            applicant_capacity="other",
            capacity_other="<script>synthetic</script>",
        )
        response = self.client.get(
            f'/members/applications/{result["application"]}/?lang=en'
        )
        self.assertContains(response, "&lt;script&gt;synthetic&lt;/script&gt;")
        self.assertNotContains(response, "<script>synthetic</script>")
        self.assertContains(response, vocabulary("en")[1]["capacity_notice"])

    def test_signup_and_login_buttons_have_action_specific_captions(self):
        self.client.logout()
        for lang in ("ar", "fr", "en"):
            _, labels = vocabulary(lang)
            for mode in ("signup", "login"):
                soup = BeautifulSoup(
                    self.client.get(f"/members/{mode}/?lang={lang}").content,
                    "html.parser",
                )
                self.assertEqual(
                    soup.select_one("section form button").get_text(strip=True),
                    labels[mode],
                )

    def test_verification_csrf_origin_boundary_and_nonleaking_policy(self):
        browser = Client(enforce_csrf_checks=True)
        response = browser.get("/verify/?lang=fr")
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertEqual(
            soup.find("meta", attrs={"name": "referrer"})["content"], "same-origin"
        )
        token = soup.select_one("[name=csrfmiddlewaretoken]")["value"]
        # Valid same-origin requests reach lookup (404 for synthetic absent record).
        data = {
            "csrfmiddlewaretoken": token,
            "serial": str(uuid.uuid4()),
            "code": "synthetic",
        }
        self.assertEqual(
            browser.post("/verify/", data, HTTP_ORIGIN="http://testserver").status_code,
            404,
        )
        for origin in ("null", "https://untrusted.example.invalid"):
            self.assertEqual(
                browser.post("/verify/", data, HTTP_ORIGIN=origin).status_code, 403
            )
        self.assertEqual(
            browser.post("/verify/", {}, HTTP_ORIGIN="http://testserver").status_code,
            403,
        )
