"""Synthetic operational UI acceptance; deployment gates stay closed."""
import uuid
from datetime import timedelta
from io import StringIO
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.core.management import call_command, CommandError
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from . import tests as fixtures, services
from .models import Authority, Delegation, Price, Person, Application, Payment, Document, Audit
from .test_deployment import PRIVATE_MIDDLEWARE

class OperationalInterfaceTests(TestCase):
    http_login = fixtures.PolicyTests.http_login
    def setUp(self):
        self.admin = fixtures.synthetic_user("synthetic-operations-owner", True)
        Authority.objects.create(primary=self.admin)
        self.target = fixtures.synthetic_user("synthetic-operations-target")
        self.request = fixtures.administrative_request(self.admin)
        call_command("seed_policy_prices", stdout=StringIO())
    def director_payload(self, **changes):
        data = dict(key=str(uuid.uuid4()), user=self.target.pk, decision="grant", reason="Synthetic mandate", confirm=True)
        data.update(changes)
        return data
    def price_payload(self, **changes):
        moment = timezone.now() + timedelta(days=2)
        data = dict(key=str(uuid.uuid4()), tier="affiliate", amount="600.00",
                    starts_at=moment.strftime("%Y-%m-%dT%H:%M"), reason="Synthetic future price", confirm=True)
        data.update(changes)
        return data
    def grant(self):
        services.delegate(self.request, key=str(uuid.uuid4()), user_id=self.target.pk, active=True, reason="Synthetic mandate")
        return Delegation.objects.get(user=self.target).epoch
    def test_primary_grant_revoke_replay_and_epoch(self):
        self.http_login()
        data = self.director_payload()
        self.assertEqual(self.client.post("/operations/directors/", data).status_code, 302)
        row = Delegation.objects.get(user=self.target); epoch = row.epoch
        self.assertEqual(self.client.post("/operations/directors/", data).status_code, 302)
        row.refresh_from_db(); self.assertEqual(row.epoch, epoch)
        old = fixtures.administrative_request(self.target, epoch)
        data = self.director_payload(decision="revoke")
        self.assertEqual(self.client.post("/operations/directors/", data).status_code, 302)
        row.refresh_from_db(); self.assertFalse(row.active); self.assertGreater(row.epoch, epoch)
        with self.assertRaises(PermissionDenied):
            services.change_price(old, key=str(uuid.uuid4()), tier="affiliate", amount="600", starts_at=(timezone.now()+timedelta(days=2)).isoformat())
        self.assertEqual(Authority.objects.get().primary_id, self.admin.pk)
        self.target.refresh_from_db(); self.assertFalse(self.target.is_superuser)
    def test_delegate_cannot_manage_directors_even_with_unrelated_permission(self):
        epoch = self.grant()
        self.target.user_permissions.add(Permission.objects.get(codename="change_user", content_type__app_label="auth"))
        self.http_login(user=self.target, epoch=epoch)
        for method in ("get", "post"):
            response = getattr(self.client, method)("/operations/directors/", self.director_payload() if method=="post" else {})
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get("/operations/pricing/").status_code, 200)
        from .wagtail_hooks import director_menu
        request = fixtures.administrative_request(self.target, epoch)
        self.assertFalse(director_menu().is_shown(request))
        self.assertTrue(director_menu().is_shown(self.request))
    def test_primary_superuser_inactive_and_unconfirmed_targets_rejected(self):
        self.http_login()
        outsider = fixtures.synthetic_user("synthetic-other-superuser", True)
        for target in (self.admin, outsider):
            self.assertEqual(self.client.post("/operations/directors/", self.director_payload(user=target.pk)).status_code, 400)
        self.target.is_active=False; self.target.save()
        self.assertEqual(self.client.post("/operations/directors/", self.director_payload()).status_code, 400)
        self.target.is_active=True; self.target.save()
        self.assertEqual(self.client.post("/operations/directors/", self.director_payload(confirm=False)).status_code, 400)
        self.assertFalse(Delegation.objects.exists())
    def test_price_is_prospective_and_old_quote_is_immutable(self):
        person = Person.objects.create(full_name="Synthetic price holder", verification_notice_at=timezone.now())
        old = services.create_application(person, "affiliate")
        old_price = old.price_id
        self.http_login()
        data = self.price_payload()
        self.assertEqual(self.client.post("/operations/pricing/?lang=en", data).status_code, 302)
        scheduled = Price.objects.filter(tier="affiliate").latest("pk")
        self.assertTrue(timezone.is_aware(scheduled.starts_at))
        self.assertEqual(scheduled.starts_at.utcoffset(), timedelta(0))
        self.assertEqual(self.client.post("/operations/pricing/", data).status_code, 302)
        self.assertEqual(Price.objects.filter(tier="affiliate").count(), 2)
        old.refresh_from_db(); self.assertEqual(old.quote, 500); self.assertEqual(old.price_id, old_price)
        self.assertEqual(services.create_application(person,"affiliate").quote, 500)
        with override_settings(USE_TZ=True):
            from unittest.mock import patch
            with patch("governance.services.timezone.now", return_value=scheduled.starts_at + timedelta(seconds=1)):
                self.assertEqual(services.create_application(person,"affiliate").quote, 600)
        self.assertEqual(Audit.objects.get(action="price.changed").reason, "Synthetic future price")
        self.assertFalse(Payment.objects.exists()); self.assertFalse(Document.objects.exists())
    def test_invalid_price_free_designations_and_past_date_rejected(self):
        self.http_login(); count = Price.objects.count()
        for change in ({"tier":"founder"},{"tier":"honorary"},{"amount":"-1"},{"starts_at":"2000-01-01T00:00"},{"confirm":False}):
            self.assertEqual(self.client.post("/operations/pricing/",self.price_payload(**change)).status_code,400)
        self.assertEqual(Price.objects.count(),count)
    def test_csrf_recent_mfa_and_revoked_delegate_write(self):
        csrf = Client(enforce_csrf_checks=True); self.http_login(client=csrf)
        self.assertEqual(csrf.post("/operations/directors/",self.director_payload()).status_code,403)
        self.assertEqual(csrf.post("/operations/pricing/",self.price_payload()).status_code,403)
        self.http_login()
        session=self.client.session;session["reauth_at"]=0;session.save()
        self.assertEqual(self.client.get("/operations/directors/").status_code,200)
        self.assertEqual(self.client.post("/operations/directors/",self.director_payload()).status_code,403)
        self.assertEqual(self.client.post("/operations/pricing/",self.price_payload()).status_code,403)
    @override_settings(ANTHEEC_OWNER_TESTING=True, MIDDLEWARE=PRIVATE_MIDDLEWARE)
    def test_trial_locales_and_candidate_cannot_enter_private_site(self):
        self.assertEqual(self.client.get("/operations/directors/").status_code,404)
        self.http_login()
        for language in ("ar","fr","en"):
            for path in ("/operations/directors/","/operations/pricing/"):
                response=self.client.get(path+"?lang="+language)
                self.assertEqual(response.status_code,200)
                self.assertIn("no-store",response["Cache-Control"])
                self.assertContains(response, 'lang="'+language+'"')
        self.assertEqual(self.client.post("/operations/directors/",self.director_payload()).status_code,302)
        epoch=Delegation.objects.get(user=self.target).epoch
        self.http_login(user=self.target,epoch=epoch)
        self.assertEqual(self.client.get("/admin/").status_code,404)
        self.assertFalse(Payment.objects.exists());self.assertFalse(Document.objects.exists())
    def test_fixture_is_guarded_idempotent_and_grants_no_privilege(self):
        with self.assertRaises(CommandError):call_command("seed_operations_demo",stdout=StringIO())
        with override_settings(ANTHEEC_OWNER_TESTING=True):
            call_command("seed_operations_demo",stdout=StringIO())
            call_command("seed_operations_demo",stdout=StringIO())
        from django.contrib.auth import get_user_model
        user=get_user_model().objects.get(username="synthetic-director-candidate-v1")
        self.assertFalse(user.has_usable_password());self.assertFalse(user.is_staff);self.assertFalse(user.is_superuser)
        self.assertFalse(Delegation.objects.exists());self.assertEqual(Price.objects.count(),6)
