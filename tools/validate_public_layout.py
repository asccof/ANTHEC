"""Browser acceptance against an isolated local database, never hosted personal data."""
import os
import threading
from pathlib import Path
from wsgiref.simple_server import make_server, WSGIRequestHandler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'antheec_app.settings.test')
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.test import override_settings
from playwright.sync_api import sync_playwright


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def main():
    if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
        raise SystemExit('Layout acceptance requires isolated SQLite test settings.')
    output = Path('layout-acceptance')
    output.mkdir(exist_ok=True)
    with override_settings(ANTHEEC_OPERATIONAL=True):
        call_command('migrate', verbosity=0)
        call_command('seed_demo')
        call_command('publish_approved_editorial', apply=True)
        call_command('publish_multilingual_editorial', apply=True)
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
                    page.close()
                browser.close()
        finally:
            server.shutdown()
    print('PASS: three languages, four widths, dropdowns, keyboard dismissal and governance directory.')


if __name__ == '__main__':
    main()
