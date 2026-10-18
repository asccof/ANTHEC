from django.test import TestCase
from . import test_portraits as portrait_fixtures
from . import test_certificate_assets as asset_fixtures
from . import certificate_assets as assets
from .models import CertificateAsset, Portrait
from .member_labels import vocabulary


class PortraitReviewPresentationTests(TestCase):
    setUp = portrait_fixtures.PortraitTests.setUp
    http_login = portrait_fixtures.PortraitTests.http_login
    upload = portrait_fixtures.PortraitTests.upload

    def test_empty_queue_and_bound_errors_remain_visible(self):
        self.http_login()
        for lang in ('ar', 'fr', 'en'):
            response = self.client.get('/operations/portraits/?lang=' + lang)
            self.assertContains(response, vocabulary(lang)[1]['no_pending_review'])
            self.assertContains(response, 'name="csrfmiddlewaretoken"')
        response = self.client.post('/operations/portraits/?lang=en', {'reason': 'synthetic-invalid'})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'errorlist', status_code=400)
        self.assertContains(response, 'synthetic-invalid', status_code=400)
        self.assertFalse(Portrait.objects.exists())

    def test_private_queue_localized_names_references_and_previews(self):
        self.person.full_name = '<script>synthetic</script>'
        self.person.save(update_fields=['full_name'])
        photo = self.upload()
        self.http_login()
        for lang in ('ar', 'fr', 'en'):
            response = self.client.get('/operations/portraits/?lang=' + lang)
            self.assertContains(response, vocabulary(lang)[1]['portrait_queue_notice'])
            self.assertContains(response, '&lt;script&gt;synthetic&lt;/script&gt;')
            self.assertNotContains(response, '<script>synthetic</script>')
            self.assertContains(response, str(photo.serial))
            self.assertContains(response, 'loading="lazy"')
            self.assertIn('no-store', response['Cache-Control'])
        self.client.force_login(self.holder)
        self.assertEqual(self.client.get('/operations/portraits/').status_code, 403)


class SigningReviewPresentationTests(TestCase):
    setUp = asset_fixtures.CertificateAssetTests.setUp
    http_login = asset_fixtures.CertificateAssetTests.http_login
    upload = asset_fixtures.CertificateAssetTests.upload

    def test_history_states_and_pending_choices_remain_separate_in_three_locales(self):
        approved = CertificateAsset.objects.get(serial=self.upload(key='first')['asset'])
        assets.review_asset(self.request, key='approve', asset_id=approved.pk, decision='approved', reason='Synthetic approval')
        pending = CertificateAsset.objects.get(serial=self.upload(kind='stamp', key='stamp')['asset'])
        rejected = CertificateAsset.objects.get(serial=self.upload(key='rejected')['asset'])
        assets.review_asset(self.request, key='reject', asset_id=rejected.pk, decision='rejected', reason='Synthetic refusal')
        self.http_login()
        for lang in ('ar', 'fr', 'en'):
            response = self.client.get('/operations/certificate-assets/?lang=' + lang)
            labels = vocabulary(lang)[1]
            for key in ('asset_queue_notice', 'asset_upload_hint', 'record_review'):
                self.assertContains(response, labels[key])
            self.assertEqual(list(response.context['review_form'].fields['asset_id'].queryset), [pending])
            self.assertEqual({row.pk for row in response.context['assets']}, {approved.pk, pending.pk, rejected.pk})
            self.assertContains(response, str(approved.serial))
            self.assertContains(response, str(rejected.serial))
            self.assertContains(response, 'enctype="multipart/form-data"')
            self.assertContains(response, 'name="action" value="upload"')
            self.assertContains(response, 'name="action" value="review"')
            self.assertContains(response, 'name="csrfmiddlewaretoken"')
            self.assertEqual(response['Referrer-Policy'], 'no-referrer')
            self.assertIn('no-store', response['Cache-Control'])

    def test_empty_pending_batch_keeps_invalid_review_errors_visible(self):
        self.http_login()
        response = self.client.post('/operations/certificate-assets/?lang=en', {'action': 'review', 'reason': 'synthetic-invalid'})
        self.assertContains(response, vocabulary('en')[1]['no_pending_review'], status_code=400)
        self.assertContains(response, 'errorlist', status_code=400)
        self.assertContains(response, 'synthetic-invalid', status_code=400)
        self.assertFalse(CertificateAsset.objects.exists())
