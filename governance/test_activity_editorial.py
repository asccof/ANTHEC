import base64
import io
import uuid
from urllib.parse import urlencode
from datetime import timedelta
from django.test import TestCase, Client, override_settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from . import activity_editorial as editorial, activity_services, services
from .models import Authority, Activity, ActivityImage, Person, Registration, Audit
from .tests import synthetic_user, administrative_request
from .test_deployment import PRIVATE_MIDDLEWARE


def picture():
    output = io.BytesIO()
    Image.new("RGB", (900, 600), "#18665e").save(output, "PNG")
    return output.getvalue()


def content(**changes):
    result = {
        "translations": {
            "ar": {
                "description": "Synthetic description\nSecond paragraph",
                "summary": "Synthetic introduction",
            },
            "fr": {
                "title": "Synthetic rencontre",
                "description": "Synthetic description française",
            },
            "en": {
                "title": "Synthetic meeting",
                "description": "Synthetic English description",
            },
        },
        "category": "workshop",
        "format": "hybrid",
        "links": [
            {
                "title": "Synthetic video",
                "url": "https://www.youtube.com/watch?v=synthetic",
                "kind": "video",
            }
        ],
    }
    result.update(changes)
    return result


class ActivityEditorialTests(TestCase):
    def setUp(self):
        self.owner = synthetic_user("synthetic-editorial-owner", True)
        Authority.objects.create(primary=self.owner)
        self.request = administrative_request(self.owner)
        self.row = Activity.objects.create(
            title="Synthetic source activity",
            starts_on=timezone.localdate(),
            ends_on=timezone.localdate() + timedelta(days=1),
            capacity=30,
            consent_text="PRIVATE GUARDIAN TERMS",
            presentation=content(),
        )
        self.url = f"/activities/{self.row.pk}/about/"
        self.admin_url = f"/operations/activities/{self.row.pk}/"

    def publish(self):
        editorial.publish(
            self.request,
            key=str(uuid.uuid4()),
            activity_id=self.row.pk,
            reason="Synthetic editorial review",
        )

    def login_owner(self):
        from .tests import PolicyTests

        self.admin = self.owner
        PolicyTests.http_login(self)

    def decision(self, action, **extra):
        return self.client.post(
            self.admin_url,
            {
                "action": action,
                "key": str(uuid.uuid4()),
                "reason": "Synthetic editorial decision",
                **extra,
            },
        )

    def test_public_visibility_locales_archive_and_private_data(self):
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertNotContains(
            self.client.get("/activities/"), "Synthetic source activity"
        )
        self.publish()
        for lang, title in [
            ("ar", "Synthetic source activity"),
            ("fr", "Synthetic rencontre"),
            ("en", "Synthetic meeting"),
        ]:
            response = self.client.get(self.url + "?lang=" + lang)
            self.assertContains(response, title)
            self.assertContains(response, 'rel="noopener noreferrer"')
            self.assertNotContains(response, "<iframe")
            self.assertNotContains(response, "PRIVATE GUARDIAN TERMS")
            self.assertContains(self.client.get("/activities/?lang=" + lang), title)
        Activity.objects.filter(pk=self.row.pk).update(
            ends_on=timezone.localdate() - timedelta(days=1),
            starts_on=timezone.localdate() - timedelta(days=2),
        )
        self.assertNotContains(
            self.client.get("/activities/"), "Synthetic source activity"
        )
        self.assertContains(
            self.client.get("/activities/?period=past"), "Synthetic source activity"
        )
        self.assertNotContains(
            self.client.get(self.url), f'href="/activities/{self.row.pk}/?'
        )
        editorial.hide(
            self.request, key="hide", activity_id=self.row.pk, reason="Synthetic hide"
        )
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_image_normalization_visibility_removal_and_origin_scope(self):
        result = editorial.upload_image(
            self.request,
            key="image",
            activity_id=self.row.pk,
            image_data=base64.b64encode(picture()).decode(),
            caption="<img onerror=alert(1)>",
            reason="Synthetic image",
        )
        image = ActivityImage.objects.get(serial=result["image"])
        url = f"/activities/{self.row.pk}/images/{image.serial}/"
        self.assertEqual(self.client.get(url).status_code, 404)
        self.publish()
        response = self.client.get(url)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(Image.open(io.BytesIO(response.content)).format, "JPEG")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(
            self.client.get(f"/activities/999/images/{image.serial}/").status_code, 404
        )
        self.assertNotContains(self.client.get(self.url), "<img onerror=alert(1)>")
        editorial.remove_image(
            self.request,
            key="remove",
            activity_id=self.row.pk,
            image_serial=str(image.serial),
            reason="Synthetic withdrawal",
        )
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertTrue(ActivityImage.objects.filter(pk=image.pk).exists())
        self.assertEqual(
            Audit.objects.filter(action="activity.image.removed").count(), 1
        )

    def test_service_validates_links_schema_and_image_limits(self):
        for url in (
            "javascript:alert(1)",
            "data:text/html,hello",
            "https://user:password@example.invalid/path",
            "http://example.invalid",
        ):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                editorial.validate_presentation(
                    content(links=[{"title": "Synthetic", "url": url, "kind": "video"}])
                )
        with self.assertRaises(ValidationError):
            editorial.validate_presentation({"translations": {"ar": {"unknown": "x"}}})
        for raw in (b"<svg/>", b"x" * (editorial.MAX_INPUT + 1)):
            with self.assertRaises(ValidationError):
                editorial.normalize_image(raw)
        Activity.objects.filter(pk=self.row.pk).update(presentation={})
        with self.assertRaises(ValidationError):
            self.publish()

    def test_create_with_image_atomic_rollback_and_published_edit_scopes(self):
        delegate = synthetic_user("synthetic-editorial-delegate")
        services.delegate(
            self.request,
            key="grant",
            user_id=delegate.pk,
            active=True,
            capabilities=["activity.view", "activity.create", "activity.edit"],
            reason="Synthetic scopes",
        )
        self.client.login(username=delegate.username, password="synthetic-password-123")
        payload = {
            "key": str(uuid.uuid4()),
            "event_title": "Synthetic new",
            "starts_on": str(timezone.localdate()),
            "ends_on": str(timezone.localdate()),
            "capacity": 20,
            "reason": "Synthetic creation",
            "description_ar": "Synthetic body",
            "image_file": SimpleUploadedFile(
                "demo.png", picture(), content_type="image/png"
            ),
        }
        self.assertEqual(
            self.client.post("/operations/activities/", payload).status_code, 403
        )
        self.assertEqual(Activity.objects.count(), 1)
        self.assertFalse(ActivityImage.objects.exists())
        self.publish()
        request = administrative_request(
            delegate, self.client.session["authority_epoch"]
        )
        with self.assertRaises(PermissionDenied):
            activity_services.update(
                request,
                key="edit-live",
                activity_id=self.row.pk,
                title=self.row.title,
                starts_on=str(self.row.starts_on),
                ends_on=str(self.row.ends_on),
                capacity=40,
                allows_minors=False,
                consent_version="v1",
                consent_text="",
                reason="Synthetic",
                presentation=content(),
            )
        self.assertEqual(self.decision("hide").status_code, 403)
        self.assertEqual(self.decision("publish").status_code, 403)

    def test_admin_complete_creation_edit_publish_image_and_hide_flow(self):
        self.login_owner()
        payload = {
            "key": str(uuid.uuid4()),
            "event_title": "Synthetic new",
            "starts_on": str(timezone.localdate()),
            "ends_on": str(timezone.localdate()),
            "capacity": 20,
            "reason": "Synthetic creation",
            "description_ar": "Synthetic body",
            "title_fr": "Synthetic français",
            "link_0_title": "Synthetic resource",
            "link_0_url": "https://example.invalid/resource",
            "link_0_kind": "resource",
            "image_file": SimpleUploadedFile(
                "demo.png", picture(), content_type="image/png"
            ),
        }
        response = self.client.post("/operations/activities/", payload)
        self.assertEqual(response.status_code, 302)
        row = Activity.objects.get(title="Synthetic new")
        self.assertFalse(row.is_published)
        self.assertEqual(row.editorial_images.count(), 1)
        self.assertContains(self.client.get(response.url), "Synthetic body")
        self.admin_url = f"/operations/activities/{row.pk}/"
        self.assertEqual(self.decision("publish").status_code, 302)
        anonymous = Client()
        self.assertContains(
            anonymous.get(f"/activities/{row.pk}/about/?lang=fr"), "Synthetic français"
        )
        self.assertContains(anonymous.get("/activities/"), "Synthetic new")
        self.assertEqual(
            self.decision(
                "upload_image",
                image_file=SimpleUploadedFile(
                    "second.png", picture(), content_type="image/png"
                ),
                caption="Synthetic caption",
            ).status_code,
            302,
        )
        self.assertEqual(row.editorial_images.count(), 2)
        image = row.editorial_images.last()
        self.assertEqual(
            self.decision("remove_image", image_serial=str(image.serial)).status_code,
            302,
        )
        self.assertEqual(self.decision("hide").status_code, 302)
        self.assertEqual(anonymous.get(f"/activities/{row.pk}/about/").status_code, 404)

    @override_settings(ANTHEEC_OWNER_TESTING=True, MIDDLEWARE=PRIVATE_MIDDLEWARE)
    def test_hosted_owner_gate_and_csrf_unchanged(self):
        self.publish()
        self.assertEqual(self.client.get("/activities/").status_code, 404)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.login_owner()
        self.assertContains(self.client.get(self.url), "Synthetic source activity")
        self.assertNotContains(
            self.client.get(self.url), f'href="/activities/{self.row.pk}/?'
        )
        client = Client(enforce_csrf_checks=True)
        from .tests import PolicyTests

        PolicyTests.http_login(self, client=client)
        self.assertEqual(
            client.post(self.admin_url, {"action": "publish"}).status_code, 403
        )

    def test_separate_publisher_and_image_scopes_no_implicit_live_edits(self):
        user = synthetic_user("synthetic-editorial-publisher")
        services.delegate(
            self.request,
            key="publisher",
            user_id=user.pk,
            active=True,
            capabilities=["activity.view", "activity.publish"],
            reason="Synthetic publication scope",
        )
        self.client.login(username=user.username, password="synthetic-password-123")
        self.assertEqual(self.decision("publish").status_code, 302)
        self.assertEqual(self.decision("hide").status_code, 403)
        self.assertEqual(
            self.decision(
                "upload_image",
                image_file=SimpleUploadedFile(
                    "no.png", picture(), content_type="image/png"
                ),
            ).status_code,
            403,
        )
        services.delegate(
            self.request,
            key="uploader",
            user_id=user.pk,
            active=True,
            capabilities=["activity.view", "activity.image_upload"],
            reason="Synthetic upload scope",
        )
        self.client.logout()
        self.client.login(username=user.username, password="synthetic-password-123")
        self.assertEqual(
            self.decision(
                "upload_image",
                image_file=SimpleUploadedFile(
                    "no.png", picture(), content_type="image/png"
                ),
            ).status_code,
            403,
        )
        editorial.hide(
            self.request,
            key="hide-for-upload",
            activity_id=self.row.pk,
            reason="Synthetic draft",
        )
        self.assertEqual(
            self.decision(
                "upload_image",
                image_file=SimpleUploadedFile(
                    "yes.png", picture(), content_type="image/png"
                ),
            ).status_code,
            302,
        )
        self.assertEqual(
            self.decision(
                "remove_image", image_serial=str(ActivityImage.objects.get().serial)
            ).status_code,
            403,
        )

    def test_bounded_gallery_and_untrusted_descriptions_are_escaped(self):
        for index in range(6):
            editorial.upload_image(
                self.request,
                key="image-" + str(index),
                activity_id=self.row.pk,
                image_data=base64.b64encode(picture()).decode(),
                caption="Synthetic",
                reason="Synthetic",
            )
        with self.assertRaises(ValidationError):
            editorial.upload_image(
                self.request,
                key="seventh",
                activity_id=self.row.pk,
                image_data=base64.b64encode(picture()).decode(),
                caption="Synthetic",
                reason="Synthetic",
            )
        body = content()
        body["translations"]["ar"][
            "description"
        ] = '<script>alert("Synthetic")</script>'
        Activity.objects.filter(pk=self.row.pk).update(presentation=body)
        self.publish()
        response = self.client.get(self.url)
        self.assertNotContains(response, "<script>alert(")
        self.assertContains(response, "&lt;script&gt;")

    def test_invalid_image_withdrawal_does_not_bind_publication_form(self):
        self.publish()
        result = editorial.upload_image(
            self.request,
            key="initial-image",
            activity_id=self.row.pk,
            image_data=base64.b64encode(picture()).decode(),
            caption="Synthetic",
            reason="Synthetic",
        )
        user = synthetic_user("synthetic-image-remover")
        services.delegate(
            self.request,
            key="remover",
            user_id=user.pk,
            active=True,
            capabilities=["activity.view", "activity.image_remove"],
            reason="Synthetic remove scope",
        )
        self.client.login(username=user.username, password="synthetic-password-123")
        response = self.client.post(
            self.admin_url,
            {
                "action": "remove_image",
                "key": str(uuid.uuid4()),
                "image_serial": result["image"],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("reason", response.context["removal_form"].errors)
        self.assertFalse(response.context["decision"].is_bound)
        self.row.refresh_from_db()
        self.assertTrue(self.row.is_published)
        self.assertTrue(ActivityImage.objects.get(serial=result["image"]).active)
        self.assertEqual(
            self.decision("remove_image", image_serial=result["image"]).status_code, 302
        )
        self.row.refresh_from_db()
        self.assertTrue(self.row.is_published)

    def test_anonymous_participation_resumes_after_login_without_external_redirects(
        self,
    ):
        self.publish()
        member = synthetic_user("synthetic-activity-visitor")
        target = f"/activities/{self.row.pk}/?lang=fr"
        self.assertContains(
            self.client.get(self.url + "?lang=fr"), "/members/login/?lang=fr"
        )
        login = self.client.get(target)
        self.assertEqual(login.status_code, 302)
        response = self.client.post(
            login.url,
            {"username": member.username, "password": "synthetic-password-123"},
        )
        self.assertRedirects(response, target)
        for unsafe in (
            "https://example.invalid/activities/1/",
            "//example.invalid/activities/1/",
            "/operations/directors/",
        ):
            self.client.logout()
            response = self.client.post(
                "/members/login/",
                {"username": member.username, "password": "synthetic-password-123"},
                QUERY_STRING=__import__(
                    "urllib.parse", fromlist=["urlencode"]
                ).urlencode({"next": unsafe}),
            )
            self.assertRedirects(response, "/members/?lang=ar")
