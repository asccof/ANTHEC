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


def signup_payload(username='synthetic-unified', **changes):
    """Fresh upload per request, never reuse a consumed multipart file."""
    import uuid
    from django.core.files.uploadedfile import SimpleUploadedFile
    data = dict(username=username, password1='Cedar-mountain-789!pass',
        password2='Cedar-mountain-789!pass', key=str(uuid.uuid4()),
        full_name='Synthetic Applicant', contact='synthetic@example.invalid',
        phone='+212600000001', profession='Synthetic coach', notice='on',
        tier='affiliate', applicant_capacity='coach', address_category='beneficiary',
        residential_address='Synthetic residence', photo_consent='on',
        photo=SimpleUploadedFile('synthetic.png', base64.b64decode(intake_payload()['image_data']), content_type='image/png'))
    data.update(changes)
    return data
