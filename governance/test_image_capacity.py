"""Orientation, transparency and output bounds for early image downsampling."""
from io import BytesIO
from PIL import Image
from django.test import SimpleTestCase
from governance.activity_editorial import normalize_image
from governance.certificate_assets import normalize


class ImageDownsamplingTests(SimpleTestCase):
    def test_activity_images_keep_oriented_bounds_and_remove_metadata(self):
        for orientation in range(1, 9):
            with self.subTest(orientation=orientation):
                source = Image.new('RGBA', (2000, 1500), (0, 0, 255, 128))
                exif = Image.Exif()
                exif[274] = orientation
                exif[270] = 'PRIVATE-SYNTHETIC-EXIF'
                raw = BytesIO()
                source.save(raw, 'PNG', exif=exif)
                result = normalize_image(raw.getvalue())
                with Image.open(BytesIO(result)) as clean:
                    self.assertEqual(clean.size, (900, 1200) if orientation in {5, 6, 7, 8} else (1600, 1200))
                    self.assertEqual(clean.mode, 'RGB')
                    self.assertFalse(clean.getexif())
                    self.assertGreater(clean.getpixel((10, 10))[0], 110)
                self.assertNotIn(b'PRIVATE', result)

    def test_signing_images_keep_alpha_bounds_and_remove_metadata(self):
        source = Image.new('RGBA', (2400, 1200), (0, 0, 255, 128))
        exif = Image.Exif()
        exif[274] = 6
        exif[270] = 'PRIVATE-SYNTHETIC-EXIF'
        raw = BytesIO()
        source.save(raw, 'PNG', exif=exif)
        result = normalize(BytesIO(raw.getvalue()))
        with Image.open(BytesIO(result)) as clean:
            self.assertEqual(clean.size, (1000, 2000))
            self.assertEqual(clean.mode, 'RGBA')
            self.assertEqual(clean.getpixel((10, 10))[3], 128)
            self.assertFalse(clean.getexif())
        self.assertNotIn(b'PRIVATE', result)
