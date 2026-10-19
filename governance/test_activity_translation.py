import json
import uuid
from unittest.mock import patch, MagicMock
from datetime import timedelta
from django.test import TestCase, SimpleTestCase, Client, override_settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from .models import Authority, Activity, TranslationAttempt
from .tests import synthetic_user, administrative_request
from . import activity_translation as translation, services


def translated(source, content, targets):
    return {
        lang: {
            field: "Synthetic " + lang + " " + value for field, value in content.items()
        }
        for lang in targets
    }


class ActivityTranslationTests(TestCase):
    def setUp(self):
        self.admin = synthetic_user("synthetic-translation-owner", True)
        Authority.objects.create(primary=self.admin)
        self.request = administrative_request(self.admin)
        from .tests import PolicyTests

        PolicyTests.http_login(self)
        self.payload = dict(
            key=str(uuid.uuid4()),
            event_title="Synthetic title",
            starts_on=str(timezone.localdate()),
            ends_on=str(timezone.localdate() + timedelta(days=1)),
            capacity=20,
            description_ar="Synthetic public body",
            reason="Synthetic reason",
            translation_source="ar",
            translation_public="on",
            translation_action="preview",
            consent_text="PRIVATE CONSENT NOT FOR TRANSLATION",
        )

    @patch("governance.activity_translation.provider", side_effect=translated)
    def test_preview_no_save_then_accept_and_publish(self, provider):
        response = self.client.post("/operations/activities/?lang=fr", self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Activity.objects.exists())
        self.assertContains(response, "Synthetic fr Synthetic public body")
        sent = provider.call_args.args[1]
        self.assertNotIn("PRIVATE CONSENT", json.dumps(sent))
        form = response.context["form"]
        data = form.data.copy()
        data["translation_action"] = "publish"
        response = self.client.post("/operations/activities/", data)
        self.assertEqual(response.status_code, 302)
        row = Activity.objects.get()
        self.assertTrue(row.is_published)
        self.assertEqual(
            row.presentation["translations"]["fr"]["description"],
            "Synthetic fr Synthetic public body",
        )
        self.assertEqual(provider.call_count, 1)
        self.assertContains(
            Client().get(f"/activities/{row.pk}/about/?lang=fr"),
            "Synthetic fr Synthetic public body",
        )

    @patch("governance.activity_translation.provider", side_effect=translated)
    def test_direct_publish_and_repeat_does_not_repeat_network(self, provider):
        self.payload["translation_action"] = "direct"
        for _ in range(2):
            self.assertEqual(
                self.client.post("/operations/activities/", self.payload).status_code,
                302,
            )
        self.assertEqual(Activity.objects.count(), 1)
        self.assertTrue(Activity.objects.get().is_published)
        self.assertEqual(provider.call_count, 1)

    @patch("governance.activity_translation.provider", side_effect=translated)
    def test_replacement_and_public_ack_are_explicit(self, provider):
        self.payload["description_fr"] = "Synthetic manual translation"
        self.assertEqual(
            self.client.post("/operations/activities/", self.payload).status_code, 400
        )
        provider.assert_not_called()
        self.payload["translation_replace"] = "on"
        self.payload.pop("translation_public")
        self.assertEqual(
            self.client.post("/operations/activities/", self.payload).status_code, 400
        )
        provider.assert_not_called()
        self.payload["translation_public"] = "on"
        self.assertEqual(
            self.client.post("/operations/activities/", self.payload).status_code, 200
        )
        provider.assert_called_once()

    @patch(
        "governance.activity_translation.provider",
        side_effect=translation.TranslationUnavailable,
    )
    def test_failure_preserves_input_and_does_not_publish(self, provider):
        self.payload["translation_action"] = "direct"
        response = self.client.post("/operations/activities/", self.payload)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Synthetic public body", status_code=400)
        self.assertFalse(Activity.objects.exists())
        self.assertEqual(TranslationAttempt.objects.get().state, "failed")

    @patch("governance.activity_translation.provider", side_effect=translated)
    def test_unauthorized_generation_and_direct_publication_denied_before_network(
        self, provider
    ):
        user = synthetic_user("synthetic-translation-delegate")
        services.delegate(
            self.request,
            key="translation-delegate",
            user_id=user.pk,
            active=True,
            capabilities=["activity.view", "activity.create"],
            reason="Synthetic",
        )
        self.client.logout()
        self.client.login(username=user.username, password="synthetic-password-123")
        self.payload["translation_action"] = "direct"
        self.assertEqual(
            self.client.post("/operations/activities/", self.payload).status_code, 403
        )
        provider.assert_not_called()
        self.assertFalse(Activity.objects.exists())
        self.payload["translation_action"] = "preview"
        self.assertEqual(
            self.client.post("/operations/activities/", self.payload).status_code, 200
        )
        self.assertEqual(provider.call_count, 1)

    @patch("governance.activity_translation.provider", side_effect=translated)
    def test_daily_cap_and_revocation_after_network(self, provider):
        TranslationAttempt.objects.bulk_create(
            [
                TranslationAttempt(
                    actor=self.admin, key=uuid.uuid4(), digest="synthetic"
                )
                for _ in range(20)
            ]
        )
        self.assertEqual(
            self.client.post("/operations/activities/", self.payload).status_code, 400
        )
        provider.assert_not_called()
        TranslationAttempt.objects.all().delete()

        def revoke(source, content, targets):
            type(self.admin).objects.filter(pk=self.admin.pk).update(is_active=False)
            return translated(source, content, targets)

        provider.side_effect = revoke
        self.payload["translation_action"] = "direct"
        self.assertEqual(
            self.client.post("/operations/activities/", self.payload).status_code, 403
        )
        self.assertFalse(Activity.objects.exists())

    @patch("governance.activity_translation.provider", side_effect=translated)
    def test_french_and_english_source_only_creation(self, provider):
        from bs4 import BeautifulSoup

        page = self.client.get("/operations/activities/")
        title_input = BeautifulSoup(page.content, "html.parser").find(
            "input", {"name": "event_title"}
        )
        self.assertFalse(title_input.has_attr("required"))
        for source in ("fr", "en"):
            data = dict(
                self.payload,
                key=str(uuid.uuid4()),
                event_title="",
                description_ar="",
                translation_source=source,
                translation_action="direct",
            )
            data["title_" + source] = "Synthetic source title"
            data["description_" + source] = "Synthetic source body"
            self.assertEqual(
                self.client.post("/operations/activities/", data).status_code, 302
            )
        self.assertEqual(Activity.objects.count(), 2)
        for row in Activity.objects.all():
            self.assertTrue(row.is_published)
            self.assertTrue(row.presentation["translations"]["ar"]["title"])
            self.assertTrue(row.presentation["translations"]["ar"]["description"])

    def editing_activity(self):
        row = Activity.objects.create(
            title="Synthetic title",
            starts_on=timezone.localdate(),
            ends_on=timezone.localdate() + timedelta(days=1),
            capacity=20,
            presentation={
                "translations": {
                    "ar": {
                        "title": "Synthetic title",
                        "description": "Synthetic public body",
                    }
                }
            },
        )
        data = dict(
            self.payload,
            action="edit",
            editorial_version=translation.version_token(row),
        )
        return row, data, f"/operations/activities/{row.pk}/"

    @patch("governance.activity_translation.provider", side_effect=translated)
    def test_stale_before_generation_and_persisted_target_need_replacement(
        self, provider
    ):
        row, data, url = self.editing_activity()
        row.presentation["translations"]["fr"] = {
            "description": "Synthetic manual target"
        }
        row.save()
        self.assertEqual(self.client.post(url, data).status_code, 400)
        provider.assert_not_called()
        data["editorial_version"] = translation.version_token(row)
        self.assertEqual(self.client.post(url, data).status_code, 400)
        provider.assert_not_called()
        data["translation_replace"] = "on"
        self.assertEqual(self.client.post(url, data).status_code, 200)
        provider.assert_called_once()

    @patch("governance.activity_translation.provider")
    def test_concurrent_manual_target_during_provider_is_preserved(self, provider):
        row, data, url = self.editing_activity()

        def concurrent_edit(source, content, targets):
            row.presentation["translations"]["fr"] = {
                "description": "Synthetic concurrent manual target"
            }
            row.save()
            return translated(source, content, targets)

        provider.side_effect = concurrent_edit
        data["translation_action"] = "direct"
        self.assertEqual(self.client.post(url, data).status_code, 400)
        row.refresh_from_db()
        self.assertEqual(
            row.presentation["translations"]["fr"]["description"],
            "Synthetic concurrent manual target",
        )
        self.assertFalse(row.is_published)

    @patch("governance.activity_translation.provider", side_effect=translated)
    def test_concurrent_manual_target_after_preview_is_preserved_at_final_save(
        self, provider
    ):
        row, data, url = self.editing_activity()
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        data = response.context["form"].data.copy()
        data["translation_action"] = "publish"
        row.presentation["translations"]["fr"] = {
            "description": "Synthetic edit after preview"
        }
        row.save()
        self.assertEqual(self.client.post(url, data).status_code, 400)
        row.refresh_from_db()
        self.assertEqual(
            row.presentation["translations"]["fr"]["description"],
            "Synthetic edit after preview",
        )
        self.assertFalse(row.is_published)


class GeminiProviderTests(SimpleTestCase):
    def test_disabled_never_calls_network(self):
        with patch("requests.post") as post, self.assertRaises(
            translation.TranslationUnavailable
        ):
            translation.provider("ar", {"title": "Synthetic"}, ["en", "fr"])
        post.assert_not_called()

    @override_settings(
        ANTHEEC_GEMINI_ENABLED=True,
        ANTHEEC_GEMINI_FREE_PROJECT_CONFIRMED=True,
        ANTHEEC_GEMINI_API_KEY="synthetic-not-a-real-key",
    )
    def test_bounded_structured_response_errors_and_no_retry(self):
        content = {"title": "Synthetic", "description": "Synthetic body"}
        output = translated("ar", content, ["fr", "en"])
        response = MagicMock()
        response.__enter__.return_value = response
        response.status_code = 200
        response.iter_content.return_value = [
            json.dumps(
                {
                    "candidates": [
                        {
                            "finishReason": "STOP",
                            "content": {"parts": [{"text": json.dumps(output)}]},
                        }
                    ]
                }
            ).encode()
        ]
        with patch("requests.post", return_value=response) as post:
            self.assertEqual(translation.provider("ar", content, ["fr", "en"]), output)
            self.assertFalse(post.call_args.kwargs["allow_redirects"])
            self.assertNotIn("key=", post.call_args.args[0])
            self.assertEqual(post.call_args.kwargs["timeout"], (5, 30))
            response.status_code = 429
            with self.assertRaises(translation.TranslationUnavailable):
                translation.provider("ar", content, ["fr", "en"])
            self.assertEqual(post.call_count, 2)
            response.status_code = 200
            response.iter_content.return_value = [b"x" * 200001]
            with self.assertRaises(translation.TranslationUnavailable):
                translation.provider("ar", content, ["fr", "en"])
