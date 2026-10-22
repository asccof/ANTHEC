"""Bounded synthetic capacity acceptance; run only in disposable CI container."""
from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
from pathlib import Path
import resource
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    if os.environ.get('CI') != 'true' or os.environ.get('ANTHEC_CAPACITY_SYNTHETIC') != '1':
        raise SystemExit('Requires explicit disposable synthetic CI execution.')
    limit = Path('/sys/fs/cgroup/memory.max')
    if not limit.exists() or limit.read_text().strip() != str(512 * 1024 * 1024):
        raise SystemExit('Run with an enforced 512 MiB cgroup memory limit.')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'antheec_app.settings.test'
    # The runtime image defaults to secure hosted mode. This isolated utility
    # must explicitly select synthetic settings before Django is initialized.
    os.environ['ANTHEEC_MODE'] = 'development'
    from django.conf import settings
    if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
        raise SystemExit('Requires disposable SQLite, never a hosted database.')
    with tempfile.TemporaryDirectory(prefix='anthec-capacity-') as folder:
        settings.DATABASES['default']['NAME'] = str(Path(folder) / 'synthetic.sqlite3')
        import django
        django.setup()
        from django.core.management import call_command
        from django.db import connections
        from django.test import Client, override_settings
        from governance.test_pdfs import PDFTests
        from governance import pdf_design, portraits
        from governance import activity_editorial, certificate_assets
        from governance.models import Document
        from PIL import Image
        with override_settings(ANTHEEC_OPERATIONAL=True):
            call_command('migrate', verbosity=0)
            call_command('seed_demo', verbosity=0)
            fixture = PDFTests('test_actual_dimensions_embedded_fonts_languages_and_bleed')
            fixture.setUp()
            # Largest accepted pixel dimensions, compressible under the 3 MiB byte cap.
            raw = io.BytesIO()
            Image.new('RGB', (4000, 4000), '#265878').save(raw, 'PNG')
            source = raw.getvalue()
            assert len(source) <= portraits.MAX_BYTES

            def render(language):
                started = time.perf_counter()
                try:
                    doc = Document.objects.get(pk=fixture.doc.pk)
                    body, _ = pdf_design.render(doc, language)
                    assert body.startswith(b'%PDF')
                    return time.perf_counter() - started
                finally:
                    connections.close_all()

            def portrait(_):
                started = time.perf_counter()
                result = portraits.normalize(io.BytesIO(source))
                assert result.startswith(b'\xff\xd8')
                return time.perf_counter() - started

            # Two concurrent tasks matches the deployed single-worker/two-thread limit.
            with ThreadPoolExecutor(max_workers=2) as pool:
                pdf_seconds = list(pool.map(render, ('ar', 'fr', 'en') * 2))
                print('CAPACITY_STAGE PDF rendering completed', flush=True)
                portrait_seconds = list(pool.map(portrait, range(4)))
                print('CAPACITY_STAGE maximum-pixel portraits completed', flush=True)
                def mixed(index):
                    return render(('ar', 'fr', 'en')[index % 3]) if index % 2 else portrait(index)
                mixed_seconds = list(pool.map(mixed, range(6)))
                print('CAPACITY_STAGE mixed rendering/uploads completed', flush=True)
                activity_images = list(pool.map(activity_editorial.normalize_image, (source, source)))
                signing_images = list(pool.map(lambda raw: certificate_assets.normalize(io.BytesIO(raw)), (source, source)))
                assert all(activity_images) and all(signing_images)
                print('CAPACITY_STAGE activity/signing image normalization completed', flush=True)

            def browse(index):
                started = time.perf_counter()
                try:
                    client = Client()
                    language = ('ar', 'fr', 'en')[index % 3]
                    for path in (f'/{language}/', f'/verify/?lang={language}', f'/activities/?lang={language}'):
                        response = client.get(path)
                        assert response.status_code == 200, response.status_code
                        assert b'type="password"' not in response.content
                    return time.perf_counter() - started
                finally:
                    connections.close_all()
            with ThreadPoolExecutor(max_workers=2) as pool:
                browsing_seconds = list(pool.map(browse, range(12)))
            assert max(pdf_seconds) < 120
            assert max(portrait_seconds) < 120
            peak_file = Path('/sys/fs/cgroup/memory.peak')
            peak = int(peak_file.read_text()) if peak_file.exists() else None
            if peak is not None:
                assert peak < 512 * 1024 * 1024
            result = {'scope': 'synthetic-single-process-two-threads',
                      'memory_limit_mib': 512, 'cgroup_peak_mib': round(peak / 2**20, 2) if peak else None,
                      'process_peak_mib': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
                      'pdf_count': len(pdf_seconds), 'pdf_max_seconds': round(max(pdf_seconds), 3),
                      'portrait_count': len(portrait_seconds), 'portrait_pixels': 16_000_000,
                      'portrait_max_seconds': round(max(portrait_seconds), 3),
                      'mixed_count': len(mixed_seconds), 'mixed_max_seconds': round(max(mixed_seconds), 3),
                      'public_get_count': len(browsing_seconds) * 3,
                      'three_gets_max_seconds': round(max(browsing_seconds), 3),
                      'hosted_load_or_throughput_proven': False}
            print('CAPACITY_RESULT ' + json.dumps(result, sort_keys=True))
            connections.close_all()


if __name__ == '__main__':
    main()
