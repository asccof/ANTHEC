"""Sanitized read-only validation of a separately restored LOCAL database."""
import base64
import hashlib
import json
import os
import re
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


def local_restore_target(vendor, config, hosted):
    name = config.get('NAME', '')
    return (not hosted and vendor == 'postgresql'
            and config.get('HOST') in {'127.0.0.1', 'localhost', '::1'}
            and (bool(re.fullmatch(r'anthec_restore_[a-z0-9_]{1,40}', name))
                 or (os.environ.get('CI') == 'true' and name == 'antheec_restore_test')))


class Command(BaseCommand):
    help = 'Check existing encrypted assets in a local isolated restore; never prints private values.'
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('--allow-local-restore', action='store_true')

    def handle(self, *args, **options):
        hosted = any(getattr(settings, key, False) for key in
                     ('ANTHEEC_OPERATIONAL', 'ANTHEEC_OWNER_TESTING', 'ANTHEEC_PUBLIC_PREVIEW'))
        if not options['allow_local_restore'] or not local_restore_target(connection.vendor, connection.settings_dict, hosted):
            raise CommandError('Requires explicit local isolated PostgreSQL restore target; hosted/source databases refused.')
        try:
            result = self.inspect()
        except Exception:
            raise CommandError('Restore integrity check failed; no private values disclosed. Inspect the isolated copy privately.') from None
        self.stdout.write(json.dumps(result, sort_keys=True))

    @staticmethod
    @transaction.atomic
    def inspect():
        from governance.models import Portrait, CertificateAsset, PDFArtifact, Document, Audit
        from governance.services import decrypt
        from governance.pdf_services import bytes_for
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION READ ONLY')
        counts = {'portraits': 0, 'signature_assets': 0, 'stamp_assets': 0,
                  'pdfs': 0, 'document_credentials': 0, 'rendered_documents': 0, 'encrypted_audit': 0}
        def require(value):
            if not value:
                raise ValueError('Restored payload integrity failure')
        for row in Portrait.objects.iterator(chunk_size=50):
            raw = base64.b64decode(decrypt(row.image)['jpeg'], validate=True)
            require(raw.startswith(b'\xff\xd8'))
            counts['portraits'] += 1
        for row in CertificateAsset.objects.iterator(chunk_size=50):
            raw = base64.b64decode(decrypt(row.image)['png'], validate=True)
            require(raw.startswith(b'\x89PNG\r\n\x1a\n') and hashlib.sha256(raw).hexdigest() == row.sha256)
            counts[row.kind + '_assets'] += 1
        for row in PDFArtifact.objects.iterator(chunk_size=20):
            require(bytes_for(row).startswith(b'%PDF'))
            counts['pdfs'] += 1
        for row in Document.objects.iterator(chunk_size=50):
            value = decrypt(row.credentials)
            require(value['token'] and value['code'])
            counts['document_credentials'] += 1
            if row.rendered:
                require(decrypt(row.rendered))
                counts['rendered_documents'] += 1
        for row in Audit.objects.only('details').iterator(chunk_size=100):
            if isinstance(row.details, dict) and row.details.get('encrypted'):
                require(decrypt(row.details['encrypted']))
                counts['encrypted_audit'] += 1
        return {'scope': 'read-only-local-restored-existing-assets', 'checked': counts,
                'absent_not_proven': [key for key, count in counts.items() if count == 0],
                'hosted_restore_proven': False, 'source_comparison_proven': False,
                'release_authorized': False}
