from django.test import TestCase
from . import test_membership_admin as fixtures
from .member_labels import vocabulary


class MembershipPresentationTests(TestCase):
    setUp = fixtures.MembershipAdminTests.setUp
    http_login = fixtures.MembershipAdminTests.http_login
    post = fixtures.MembershipAdminTests.post
    # Reuse the established authorization fixtures without duplicating its tests.
    def test_localized_register_and_pending_decisions(self):
        self.person.full_name = '<script>synthetic</script>'
        self.person.save(update_fields=['full_name'])
        for lang in ('ar', 'fr', 'en'):
            labels = vocabulary(lang)[1]
            response = self.client.get('/operations/membership/?lang=' + lang)
            self.assertContains(response, labels['register_window'])
            self.assertContains(response, 'application-card')
            self.assertContains(response, '&lt;script&gt;synthetic&lt;/script&gt;')
            self.assertNotContains(response, '<script>synthetic</script>')
            detail = self.client.get(f'/operations/membership/{self.app.pk}/?lang={lang}')
            for key in ('financial_summary', 'back_register', 'record_payment', 'record_exemption', 'review_decisions'):
                self.assertContains(detail, labels[key])
            for action in ('payment', 'exempt', 'approve', 'reject'):
                self.assertContains(detail, f'name="action" value="{action}"')
            self.assertContains(detail, 'name="csrfmiddlewaretoken"')

    def test_validation_error_remains_visible_with_bound_fields(self):
        response = self.post('payment', amount='not-money', method='cash', proof_reference='synthetic')
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'errorlist', status_code=400)
        self.assertContains(response, 'synthetic', status_code=400)
        self.app.refresh_from_db()
        self.assertEqual(self.app.state, 'submitted')

    def test_issued_documents_keep_download_and_preview_actions_distinct(self):
        self.assertEqual(self.post('exempt', reason='Synthetic exemption').status_code, 302)
        self.assertEqual(self.post('approve', reason='Synthetic approval').status_code, 302)
        for lang in ('ar', 'fr', 'en'):
            labels = vocabulary(lang)[1]
            response = self.client.get(f'/operations/membership/{self.app.pk}/?lang={lang}')
            self.assertContains(response, labels['download_document'])
            self.assertContains(response, labels['pdf_preview'])
            self.assertContains(response, labels['replace_document'])
            self.assertNotContains(response, 'name="action" value="approve"')
