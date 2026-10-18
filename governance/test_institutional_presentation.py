from datetime import date
from unittest.mock import patch
from django.test import TestCase
from . import test_institutional as fixtures
from .institutional_labels import LABELS
from .models import InstitutionalRole


class InstitutionalPresentationTests(TestCase):
    setUp = fixtures.InstitutionalTests.setUp
    http_login = fixtures.InstitutionalTests.http_login
    payload = fixtures.InstitutionalTests.payload
    grant = fixtures.InstitutionalTests.grant

    @patch('governance.services.today', return_value=date(2030, 1, 1))
    def test_recorded_state_and_effective_card_expiry_stay_distinct(self, _):
        result = self.grant()
        self.http_login()
        for lang in ('ar', 'fr', 'en'):
            labels = LABELS[lang]
            register = self.client.get('/operations/institutional/?lang=' + lang)
            self.assertContains(register, labels['recorded_state'] + ': ' + labels['active'])
            self.assertContains(register, labels['register_window'])
            detail = self.client.get(f'/operations/institutional/{result["institutional_role"]}/?lang={lang}')
            for key in ('card_documents', 'expired', 'download', 'pdf_preview', 'back_register', 'save_role_state'):
                self.assertContains(detail, labels[key])
            self.assertContains(detail, 'institutional.css')
            self.assertContains(detail, 'name="action" value="state"')
            self.assertContains(detail, 'name="action" value="replace"')
            self.assertContains(detail, 'name="csrfmiddlewaretoken"')
            self.assertIn('no-store', detail['Cache-Control'])
        self.assertEqual(InstitutionalRole.objects.get().state, 'active')

    def test_permanent_founder_dates_and_escaped_identity(self):
        self.person.full_name = '<script>synthetic-founder</script>'
        self.person.save(update_fields=['full_name'])
        result = self.grant('founder')
        self.http_login()
        for lang in ('ar', 'fr', 'en'):
            response = self.client.get(f'/operations/institutional/{result["institutional_role"]}/?lang={lang}')
            self.assertContains(response, LABELS[lang]['permanent_term'])
            self.assertContains(response, '&lt;script&gt;synthetic-founder&lt;/script&gt;')
            self.assertNotContains(response, '<script>synthetic-founder</script>')
            self.assertNotContains(response, '<option value="terminated"')
        self.client.force_login(self.holder)
        self.assertEqual(self.client.get('/operations/institutional/').status_code, 403)

    def test_bound_grant_errors_are_visible_without_issuing_cards(self):
        self.http_login()
        response = self.client.post('/operations/institutional/?lang=en', {'role': 'president', 'reason': 'synthetic-invalid'})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'errorlist', status_code=400)
        self.assertContains(response, 'synthetic-invalid', status_code=400)
        self.assertFalse(InstitutionalRole.objects.exists())
