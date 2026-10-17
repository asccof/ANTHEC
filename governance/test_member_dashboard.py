from datetime import date
from unittest.mock import patch
from django.test import TestCase
from .tests import synthetic_user
from .models import Person, Application, Membership
from . import services as s
from .member_labels import vocabulary


class MemberDashboardTests(TestCase):
    def setUp(self):
        self.user = synthetic_user('synthetic-dashboard')
        self.person = Person.objects.create(user=self.user, full_name='Synthetic Dashboard', contact='dashboard@example.invalid')
        self.client.force_login(self.user)

    def term(self, person=None, tier='accredited', starts=date(2026, 10, 16), ends=date(2027, 10, 16), state='active'):
        app = Application.objects.create(person=person or self.person, tier=tier, state='approved', quote=3000, quoted_on=date(2026, 10, 16))
        return Membership.objects.create(application=app, starts_on=starts, ends_on=ends, state=state)

    @patch('governance.services.today', return_value=date(2026, 10, 17))
    def test_current_future_exclusive_expiry_and_suspension_are_distinct(self, _):
        self.term()
        self.term(starts=date(2027, 10, 16), ends=date(2028, 10, 16))
        self.term(starts=date(2025, 10, 17), ends=date(2026, 10, 17))
        self.term(state='suspended')
        for lang in ('ar', 'fr', 'en'):
            response = self.client.get('/members/?lang=' + lang)
            self.assertEqual(response.status_code, 200)
            self.assertEqual([r['state_key'] for r in response.context['membership_terms']], ['upcoming_term', 'suspended', 'active', 'expired'])
            for key in ('membership_summary', 'upcoming_term', 'quick_actions', 'edit_profile'):
                self.assertContains(response, vocabulary(lang)[1][key])
            self.assertIn('no-store', response['Cache-Control'])
            self.assertContains(response, 'member.css')

    def test_owner_totals_and_terms_do_not_disclose_other_members(self):
        own = self.term()
        s.issue('gold_card', membership=own)
        stranger = Person.objects.create(user=synthetic_user('synthetic-dashboard-other'), full_name='PRIVATE-OTHER-DASHBOARD')
        other = self.term(person=stranger)
        s.issue('gold_card', membership=other)
        Application.objects.create(person=stranger, tier='general', quote=100, quoted_on=date(2026, 10, 16))
        Application.objects.create(person=self.person, tier='general', quote=100, quoted_on=date(2026, 10, 16))
        response = self.client.get('/members/')
        self.assertEqual(response.context['document_count'], 1)
        self.assertEqual(response.context['pending_count'], 1)
        self.assertEqual(len(response.context['membership_terms']), 1)
        self.assertNotContains(response, 'PRIVATE-OTHER-DASHBOARD')
        self.assertEqual(self.client.get('/members/documents/').context['documents'][0]['doc'].membership_id, own.pk)
        self.assertEqual(len(self.client.get('/members/documents/').context['documents']), 1)

    def test_permanent_member_has_no_renewal_action_and_escaped_profile(self):
        self.term(tier='honorary', ends=None)
        self.person.full_name = '<script>synthetic</script>'
        self.person.save(update_fields=['full_name'])
        response = self.client.get('/members/?lang=en')
        self.assertFalse(response.context['can_renew'])
        self.assertContains(response, 'Permanent — no end date')
        self.assertContains(response, '&lt;script&gt;synthetic&lt;/script&gt;')
        self.assertNotContains(response, '<script>synthetic</script>')

    def test_new_account_empty_states_and_logout_csrf_form(self):
        self.person.delete()
        response = self.client.get('/members/?lang=en')
        self.assertEqual(response.context['document_count'], 0)
        self.assertEqual(response.context['pending_count'], 0)
        self.assertContains(response, 'No approved membership yet.')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.client.logout()
        self.assertEqual(self.client.get('/members/').status_code, 302)
