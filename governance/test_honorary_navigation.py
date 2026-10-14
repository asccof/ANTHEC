"""Permanent honorary designation and safe, localized navigation."""
from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError, transaction
from django.utils import translation
from django.template.loader import render_to_string
from . import test_institutional as fixtures
from . import institutional as roles, services
from .models import InstitutionalRole, Document, Outbox, Membership, Accreditation
from .institutional_forms import GrantForm, DecisionForm
from .institutional_labels import vocabulary
from .documents import printable

class HonoraryNavigationTests(TestCase):
    setUp = fixtures.InstitutionalTests.setUp
    payload = fixtures.InstitutionalTests.payload
    grant = fixtures.InstitutionalTests.grant

    def test_honorary_permanent_card_and_state_lifecycle(self):
        import base64, uuid
        from .test_portraits import image_bytes
        from .portraits import upload_portrait, review_portrait
        from .models import Portrait
        uploaded = upload_portrait(self.holder,key=str(uuid.uuid4()),person_id=self.person.pk,image_data=base64.b64encode(image_bytes()).decode(),consent=True)
        photo = Portrait.objects.get(serial=uploaded['portrait'])
        review_portrait(self.request,key=str(uuid.uuid4()),portrait_id=photo.pk,decision='approved',reason='Synthetic photo')
        result = self.grant('honorary', ends_on=None)
        row = InstitutionalRole.objects.get(pk=result['institutional_role'])
        doc = Document.objects.get(pk=result['document'])
        self.assertIsNone(row.ends_on)
        self.assertEqual(doc.kind, 'honorary_card')
        from .pdf_design import render
        from pypdf import PdfReader
        from io import BytesIO
        self.assertEqual(len(PdfReader(BytesIO(render(doc,"ar",preview=True,proof=True)[0])).pages),2)
        self.assertEqual(Membership.objects.count(), 0)
        self.assertEqual(Accreditation.objects.count(), 0)
        for lang in ('ar','fr','en'):
            self.assertIn(vocabulary(lang)[1]['honorary_card'], printable(doc, lang))
            self.assertIn(('honorary', vocabulary(lang)[1]['honorary']), GrantForm(labels=vocabulary(lang)[1]).fields['role'].choices)
        for state in ('suspended','cancelled','active'):
            roles.change_state(self.request,key='honorary-'+state,role_id=row.pk,state=state,reason='Synthetic decision')
            self.assertEqual(services.document_status(Document.objects.get(pk=doc.pk)),state)
        with self.assertRaises(ValidationError):
            roles.change_state(self.request,key='honorary-terminate',role_id=row.pk,state='terminated',reason='Synthetic')
        with self.assertRaises(services.Conflict): self.grant('honorary', ends_on=None)
        self.assertEqual(Document.objects.count(),1)

    def test_honorary_invalid_term_and_database_constraints(self):
        with self.assertRaises(ValidationError): self.grant('honorary',ends_on='2027-01-01')
        with self.assertRaises(ValidationError): self.grant('honorary',ends_on=None,replaces_role_id=123)
        for end in ('2027-01-01',):
            with self.assertRaises(IntegrityError), transaction.atomic():
                InstitutionalRole.objects.create(person=self.person,role='honorary',starts_on='2026-01-01',ends_on=end,legal_reference='SYNTHETIC')
        self.grant('honorary', ends_on=None)
        with self.assertRaises(IntegrityError), transaction.atomic():
            InstitutionalRole.objects.create(person=self.person,role='honorary',starts_on='2026-01-01',legal_reference='SYNTHETIC')
        for lang in ('ar','fr','en'):
            self.assertNotIn('terminated',dict(DecisionForm(labels=vocabulary(lang)[1],founder=True).fields['state'].choices))

    @override_settings(ANTHEEC_OWNER_TESTING=True)
    def test_owner_testing_honorary_grant_rolls_back(self):
        with self.assertRaises(PermissionDenied): self.grant('honorary',ends_on=None)
        self.assertEqual(InstitutionalRole.objects.count(),0)
        self.assertEqual(Document.objects.count(),0)
        self.assertEqual(Outbox.objects.count(),0)

    def test_shared_navigation_and_admin_menu_languages(self):
        from .wagtail_hooks import return_to_website_menu
        item = return_to_website_menu()
        for lang in ('ar','fr','en'):
            with translation.override(lang):
                html=render_to_string('governance/navigation.html',{'language':lang,'user':self.admin})
                self.assertIn('href="/'+lang+'/"',html)
                self.assertIn('href="/admin/"',html)
                self.assertEqual(str(item.url),'/'+lang+'/')
                self.assertIn(str(item.label), html)
        html=render_to_string('governance/navigation.html',{'language':'ar','user':self.holder})
        self.assertNotIn('href="/admin/"',html)
