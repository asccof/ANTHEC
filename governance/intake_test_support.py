"""Synthetic intake fixtures; no real identity or image."""

import base64
import io
from PIL import Image


def intake_payload():
    output = io.BytesIO()
    Image.new("RGB", (600, 750), "navy").save(output, format="PNG")
    return dict(
        address_category="beneficiary",
        residential_address="Synthetic residence 01",
        image_data=base64.b64encode(output.getvalue()).decode(),
        photo_consent=True,
    )
