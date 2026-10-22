"""Synthetic-only recovery evidence. No command for inspecting hosted identities."""
import base64
import hashlib
from django.apps import apps
from django.db import connection
from django.test import override_settings
from cryptography.fernet import Fernet, InvalidToken


def seed():
    from governance.test_pdfs import PDFTests
    from governance.models import Accreditation, Audit
    from governance import services, pdf_services
    fixture = PDFTests('test_actual_dimensions_embedded_fonts_languages_and_bleed')
    fixture.setUp()
    certificate = services.issue('accreditation_certificate', accreditation=Accreditation.objects.create(
        person=fixture.person, subject_name='Synthetic restore subject', kind='individual',
        starts_on=fixture.role.starts_on, ends_on=fixture.role.ends_on))
    for doc in (fixture.doc, certificate):
        for language in ('ar', 'fr', 'en'):
            pdf_services.artifact_for(doc.pk, language)
    Audit.objects.create(action='recovery.synthetic', subject='synthetic',
                         details={'encrypted': services.encrypt({'proof': 'synthetic-recovery-only'})})


def snapshot():
    from governance.models import Portrait, CertificateAsset, PDFArtifact, Document, Audit
    from governance import services, pdf_services
    result = {'counts': {model._meta.label: model.objects.count()
                         for model in apps.get_models() if not model._meta.proxy}, 'payloads': {}}
    for model, field, key in ((Portrait, 'image', 'jpeg'), (CertificateAsset, 'image', 'png')):
        rows = list(model.objects.all())
        assert rows, model._meta.label
        for row in rows:
            raw = base64.b64decode(services.decrypt(getattr(row, field))[key], validate=True)
            assert raw
            result['payloads'][f'{model._meta.label}/{row.pk}'] = hashlib.sha256(raw).hexdigest()
    assert PDFArtifact.objects.count() == 6
    for row in PDFArtifact.objects.all():
        raw = pdf_services.bytes_for(row)
        assert raw.startswith(b'%PDF')
        result['payloads'][f'pdf/{row.pk}'] = hashlib.sha256(raw).hexdigest()
    for row in Document.objects.all():
        secret = services.decrypt(row.credentials)
        assert secret['token'] and secret['code']
        result['payloads'][f'document/{row.pk}'] = hashlib.sha256(row.credentials.encode()).hexdigest()
    encrypted = Audit.objects.get(action='recovery.synthetic').details['encrypted']
    assert services.decrypt(encrypted) == {'proof': 'synthetic-recovery-only'}
    with override_settings(ANTHEEC_DATA_KEY=Fernet.generate_key().decode()):
        try:
            services.decrypt(encrypted)
        except InvalidToken:
            pass
        else:
            raise AssertionError('Wrong key unexpectedly decrypted recovery evidence')
    with connection.cursor() as cursor:
        cursor.execute('SELECT app, name FROM django_migrations ORDER BY app, name')
        result['migrations'] = cursor.fetchall()
    return result
