"""Browser acceptance against an isolated local database, never hosted personal data."""
import os
import threading
import tempfile
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from wsgiref.simple_server import make_server, WSGIRequestHandler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'antheec_app.settings.test')
from django.conf import settings
if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
    raise SystemExit('Layout acceptance requires isolated SQLite test settings.')
_layout_database = tempfile.TemporaryDirectory(prefix='anthec-layout-')
settings.DATABASES['default']['NAME'] = str(Path(_layout_database.name) / 'layout.sqlite3')
import django
django.setup()
from django.db import connections
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.test import override_settings
from playwright.sync_api import sync_playwright
from django.utils import timezone
from PIL import Image
from governance.models import Activity, ActivityImage
from governance.tests import PolicyTests
from governance.services import decrypt


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def main():
    if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
        raise SystemExit('Layout acceptance requires isolated SQLite test settings.')
    output = Path('layout-acceptance')
    output.mkdir(exist_ok=True)
    with override_settings(ANTHEEC_OPERATIONAL=True, ANTHEEC_PRIVACY_NOTICE_ENABLED=True,
                           ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON='2026-10-22'):
        call_command('migrate', verbosity=0)
        call_command('seed_demo')
        call_command('publish_approved_editorial', apply=True)
        call_command('publish_multilingual_editorial', apply=True)
        # Synthetic posts and an issued synthetic document exist only in this isolated CI database.
        today = timezone.localdate()
        picture = BytesIO()
        Image.new('RGB', (80, 50), '#146e70').save(picture, 'JPEG')
        for offset in (-2, 2):
            activity = Activity.objects.create(title='Synthetic published activity',
                starts_on=today+timedelta(days=offset), ends_on=today+timedelta(days=offset),
                capacity=10, is_published=True, presentation={'translations': {
                    code: {'title': 'Synthetic '+code+' activity', 'summary': 'Synthetic public post',
                           'description': 'Synthetic public description'} for code in ('ar','fr','en')}})
            ActivityImage.objects.create(activity=activity, jpeg=picture.getvalue(), caption='Synthetic illustration')
        fixture = PolicyTests('test_public_verification_requires_secret_and_has_only_allowlisted_fields')
        fixture.setUp()
        document = fixture.document()
        credentials = decrypt(document.credentials)
        server = make_server('127.0.0.1', 0, StaticFilesHandler(get_wsgi_application()), handler_class=QuietHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                for language in ('ar', 'fr', 'en'):
                    page = browser.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    for width in (320, 390, 768, 1280):
                        page.set_viewport_size({'width': width, 'height': 960})
                        response = page.goto(f'http://127.0.0.1:{server.server_port}/{language}/')
                        assert response.status == 200
                        page.evaluate('document.fonts.ready')
                        assert page.locator('.founders-grid article').count() == 7
                        assert page.locator('.home-access a').count() == 3
                        assert page.locator('.home-activity-card').count() == 2
                        assert page.locator('.home-activity-card img').count() == 2
                        for image in page.locator('.home-activity-card img').all():
                            image.scroll_into_view_if_needed()
                            image.evaluate('(image) => image.decode()')
                            assert image.evaluate('(image) => image.naturalWidth > 0')
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language, width, 'page overflow')
                        assert page.locator('html').get_attribute('dir') == ('rtl' if language == 'ar' else 'ltr')
                        for group in page.locator('.main-nav details').all():
                            summary = group.locator('summary')
                            summary.click()
                            box = group.locator('.nav-dropdown').bounding_box()
                            assert box and box['x'] >= -1 and box['x'] + box['width'] <= width + 1, (language, width, box)
                            summary.focus()
                            page.keyboard.press('Escape')
                            assert group.get_attribute('open') is None
                        page.locator('.hero').scroll_into_view_if_needed()
                        if width in (390, 1280):
                            page.screenshot(path=str(output / f'home-{language}-{width}.png'), full_page=True)
                    assert not errors, errors
                    response = page.goto(f'http://127.0.0.1:{server.server_port}/{language}/governance/')
                    assert response.status == 200
                    assert page.locator('.office-card').count() == 2
                    assert page.locator('.founders-grid article').count() == 7
                    from governance.privacy_notice import WORDS
                    for width in (390, 1280):
                        page.set_viewport_size({'width': width, 'height': 960})
                        response = page.goto(f'http://127.0.0.1:{server.server_port}/privacy/?lang={language}')
                        assert response.status == 200
                        assert page.locator('h1').inner_text() == WORDS[language][0]
                        assert page.locator('article h2').count() == 6
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language, width, 'privacy overflow')
                    response = page.goto(f'http://127.0.0.1:{server.server_port}/members/signup/?lang={language}')
                    assert response.status == 200
                    for width in (320, 390, 768, 1280):
                        page.set_viewport_size({'width': width, 'height': 960})
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language, width, 'intake overflow')
                        assert page.locator('#membership-intake fieldset').count() == 4
                        if width in (390, 1280):
                            page.screenshot(path=str(output / f'intake-{language}-{width}.png'), full_page=True)
                    for fee_tier, expected in (('general', '100'), ('affiliate', '500'), ('advanced', '1500'), ('accredited', '3000'), ('founder', '0'), ('honorary', '0')):
                        page.locator('#id_tier').select_option(fee_tier)
                        reminder = page.locator('[data-fee-tier="'+fee_tier+'"]')
                        assert reminder.is_visible()
                        assert expected in reminder.inner_text()
                        assert page.locator('[data-fee-tier]:visible').count() == 1
                    assert not page.locator('#id_privacy_acceptance').is_checked()
                    assert page.locator('#id_privacy_version').input_value().startswith('ANTHEC-privacy-v2')
                    # A public visitor opens the form and a QR result without account login.
                    response = page.goto(f'http://127.0.0.1:{server.server_port}/verify/?lang={language}')
                    assert response.status == 200
                    assert page.locator('#document-reference').is_visible()
                    assert page.locator('input[type="password"]').count() == 0
                    qr = browser.new_page()
                    qr.goto(f'http://127.0.0.1:{server.server_port}/verify/?lang={language}#'+credentials['token'])
                    qr.get_by_text('Synthetic Person', exact=True).wait_for(state='visible')
                    assert qr.locator('#verification').count() == 0
                    assert '#' not in qr.url
                    qr.close()
                    # One complete synthetic signup creates the pending application, not membership.
                    page.goto(f'http://127.0.0.1:{server.server_port}/members/signup/?lang={language}')
                    page.locator('#id_address_category').select_option('beneficiary')
                    for name, value in {'username': 'synthetic-browser-'+language,
                            'password1': 'Cedar-mountain-789!pass', 'password2': 'Cedar-mountain-789!pass',
                            'full_name': 'Synthetic Browser '+language, 'phone': '+212600000001',
                            'profession': 'Synthetic coach', 'residential_address': 'Synthetic residence'}.items():
                        page.locator('#id_'+name).fill(value)
                    page.locator('#id_tier').select_option('affiliate')
                    page.locator('#id_applicant_capacity').select_option('coach')
                    portrait = BytesIO()
                    Image.new('RGB', (600, 750), 'navy').save(portrait, 'PNG')
                    page.locator('#id_photo').set_input_files({'name': 'synthetic.png', 'mimeType': 'image/png', 'buffer': portrait.getvalue()})
                    for name in ('notice', 'photo_consent', 'privacy_acceptance'):
                        page.locator('#id_'+name).check()
                    page.locator('#membership-intake button[type=submit]').click()
                    page.wait_for_url('**/members/applications/**')
                    assert page.locator('[role=status]').count() == 2
                    assert page.locator('main').get_by_text('Synthetic Browser '+language, exact=False).count() > 0
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language, 'receipt overflow')
                    page.close()
                browser.close()
            # Playwright's sync context owns an event loop; inspect Django ORM only after it exits.
            from governance.models import Application, Membership
            for language in ('ar', 'fr', 'en'):
                submitted = Application.objects.get(person__user__username='synthetic-browser-'+language)
                assert submitted.state == 'submitted' and not Membership.objects.filter(application=submitted).exists()
        finally:
            server.shutdown()
            server.server_close()
    print('PASS: three languages, four widths, published activity images, anonymous verification, direct QR results versioned privacy notice/unchecked acknowledgement, and one-submit membership intake in each language.')


if __name__ == '__main__':
    try:
        main()
    finally:
        connections.close_all()
        _layout_database.cleanup()
