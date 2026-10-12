"""Certificate presentation regressions; synthetic data and plain image fixtures."""

import io
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from pypdf import PdfReader
from . import services as s, pdf_design as design, pdf_services as pdf
from .certificate_content import CONTENT
from .models import Accreditation, Person
from .tests import synthetic_user
from .test_certificate_assets import approved_test_assets


class CertificateLayoutTests(TestCase):
    def setUp(self):
        self.person = Person.objects.create(full_name="Synthetic Certificate Holder")
        self.accreditation = Accreditation.objects.create(
            person=self.person, subject_name=self.person.full_name,
            kind="professional", starts_on=timezone.localdate(),
            ends_on=timezone.localdate() + timedelta(days=365),
        )

    def render_checked(self, render, category, language):
        layouts = []
        original = design.HTML.render

        def capture(instance, *args, **kwargs):
            document = original(instance, *args, **kwargs)
            layouts.append(document)
            return document

        with patch.object(design.HTML, "render", capture):
            body, metadata = render()
        reader = PdfReader(io.BytesIO(body))
        self.assertEqual(len(reader.pages), 1)
        page = reader.pages[0]
        self.assertAlmostEqual(float(page.mediabox.width) * 25.4 / 72, 297, places=3)
        self.assertAlmostEqual(float(page.mediabox.height) * 25.4 / 72, 210, places=3)
        text_lines = []
        observed = {}

        def walk(box):
            yield box
            for child in getattr(box, "children", ()):
                yield from walk(child)

        for box in walk(layouts[-1].pages[0]._page_box):
            if (box.__class__.__name__ != "AbsolutePlaceholder" or
                    box.element is None or
                    "text" not in box.element.get("class", "").split()):
                continue
            label = box.element.text or ""
            observed[label] = box.style["font_size"] * 72 / 96
            for line in walk(box):
                if line.__class__.__name__ != "LineBox":
                    continue
                self.assertLessEqual(line.position_y + line.height,
                                     box.position_y + box.height + .2, label)
                self.assertGreaterEqual(line.position_x, box.position_x - .2, label)
                self.assertLessEqual(line.position_x + line.width,
                                     box.position_x + box.width + .2, label)
                text_lines.append((label, line.position_x, line.position_y,
                                   line.position_x + line.width,
                                   line.position_y + line.height))

        def overlaps(a, b):
            return min(a[3], b[3]) - max(a[1], b[1]) > .2 and min(a[4], b[4]) - max(a[2], b[2]) > .2

        for i, a in enumerate(text_lines):
            for b in text_lines[i+1:]:
                self.assertFalse(overlaps(a, b), (a[0], b[0]))
            # QR quiet zone and authentic-image slots must remain text-free.
            for region in [("QR", 25, 169, 22, 22),
                           ("signature", 195, 165, 41, 16),
                           ("stamp", 242, 163, 24, 18)]:
                label, x, y, w, h = region
                # Unsigned placeholders are text inside their own image slot.
                if any(word in a[0] for word in ("Awaiting", "authentique", "بانتظار")):
                    continue
                b = (label, x*96/25.4, y*96/25.4, (x+w)*96/25.4, (y+h)*96/25.4)
                self.assertFalse(overlaps(a, b), (a[0], label))
        self.assertGreaterEqual(observed[CONTENT[category][language][1]], 13)
        self.assertGreaterEqual(observed[CONTENT[category][language][2]], 11.5)
        self.assertEqual(metadata["template"], design.CERTIFICATE_VERSION)
        return body, metadata

    def test_all_nine_unsigned_certificate_layouts_are_readable_and_separate(self):
        for kind in ("professional_certificate", "accreditation_certificate"):
            doc = s.issue(kind, accreditation=self.accreditation)
            for language in ("ar", "fr", "en"):
                with self.subTest(kind=kind, language=language):
                    self.render_checked(lambda: design.render(doc, language, proof=True), kind, language)
        proof = design.ParticipationProof(
            "Synthetic Participant", "Synthetic professional communication workshop",
            "Synthetic organizer", "2026-10-12", "2026-10-13", "12 hours",
        )
        for language in ("ar", "fr", "en"):
            with self.subTest(kind="participation", language=language):
                body, metadata = self.render_checked(
                    lambda: design.render_participation_proof(proof, language),
                    "participation_design_proof", language,
                )
                self.assertIn("NOT ISSUED", PdfReader(io.BytesIO(body)).pages[0].extract_text())

    def test_signed_edition_uses_same_clear_slots_and_records_certificate_version(self):
        user = synthetic_user("synthetic-layout-primary", True)
        approved_test_assets(user)  # Plain rectangles, not imitated artwork.
        doc = s.issue("professional_certificate", accreditation=self.accreditation)
        for language in ("ar", "fr", "en"):
            with self.subTest(language=language):
                self.render_checked(lambda: design.render(doc, language),
                                    "professional_certificate", language)
        artifact = pdf.artifact_for(doc.pk, "en")
        self.assertEqual(artifact.template_version, artifact.metadata["template"])
        self.assertEqual(artifact.template_version, design.CERTIFICATE_VERSION)
        self.assertEqual(artifact.metadata["signing_status"], "approved_raster_assets")

    def test_unbounded_signatory_text_fails_layout_review_without_clipping(self):
        doc = s.issue("professional_certificate", accreditation=self.accreditation)
        # Ephemeral proof input only; never rebind or save an issued snapshot.
        doc.signing_snapshot = {**doc.signing_snapshot, "latin_name": "W" * 120}
        with self.assertRaises(design.LayoutError):
            design.render(doc, "en", proof=True)
