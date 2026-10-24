import base64
import uuid
from django.core.exceptions import ValidationError, PermissionDenied
from .models import MemberTool, ToolRequest
from .services import command, audit
from .deployment import workflow_disabled
from .activity_editorial import normalize_image


@command('tool.save', primary_only=True)
def save_tool(*, actor, tool_pk=None, fields, image_data=None, remove_image=False):
    row = MemberTool.objects.select_for_update().get(pk=tool_pk) if tool_pk else MemberTool()
    allowed = {field+'_'+lang for lang in ('ar','fr','en') for field in ('title','summary','description')}
    allowed.update({'website','sort_order','published'})
    if set(fields) != allowed:
        raise ValidationError('Invalid tool fields')
    if fields['published'] and workflow_disabled('APPLICATIONS'):
        raise PermissionDenied('Publication is unavailable in this deployment')
    for name, value in fields.items():
        setattr(row, name, value)
    if image_data is not None:
        row.image = normalize_image(base64.b64decode(image_data, validate=True))
        row.image_serial = uuid.uuid4()
    elif remove_image:
        row.image = b''
        row.image_serial = uuid.uuid4()
    # Recheck link constraints at the command boundary too.
    from urllib.parse import urlsplit
    from django.core.validators import URLValidator
    if row.website:
        URLValidator(schemes=['https'])(row.website)
        if urlsplit(row.website).username or urlsplit(row.website).password:
            raise ValidationError('Credentials forbidden')
    row.full_clean()
    row.save()
    audit(actor, 'tool.saved', row.pk, published=row.published)
    return {'tool': row.pk}


@command('tool.request.review', primary_only=True)
def review_request(*, actor, request_id, state, notes):
    row = ToolRequest.objects.select_for_update().get(pk=request_id)
    row.state, row.notes = state, notes
    row.full_clean()
    row.save(update_fields=['state','notes','updated_at'])
    audit(actor, 'tool.request.reviewed', row.pk, state=state)
    return {'request': row.pk}
