"""Partnership review without payments, credentials or external delivery."""
from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.validators import URLValidator
from .models import PartnershipRequest, Partner
from .services import command, audit, Conflict

@command('partnership.decide')
def decide(*, actor, request_id, decision, reason):
    row=PartnershipRequest.objects.select_for_update().get(pk=request_id)
    if row.state!='submitted' or decision not in {'approved','rejected'} or not reason.strip():
        raise ValidationError('Submitted request, decision and reason required')
    if not row.notice_acknowledged:
        raise ValidationError('Prior processing notice required')
    row.state=decision; row.save(update_fields=['state'])
    partner=None
    if decision=='approved':
        partner=Partner.objects.create(request=row,name_ar=row.organization,name_fr=row.organization,name_en=row.organization)
    audit(actor,'partnership.'+decision,row.pk,reason)
    return {'request':row.pk,'partner':partner.pk if partner else None}

@command('partner.update')
def update(*, actor, partner_id, state, public_visible, reason, **content):
    if state not in {'active','suspended','cancelled'} or not isinstance(public_visible,bool) or not reason.strip():
        raise ValidationError('Valid state, visibility and reason required')
    if public_visible and getattr(settings,'ANTHEEC_OWNER_TESTING',False):
        raise PermissionDenied('Public publication disabled during owner testing')
    row=Partner.objects.select_for_update().select_related('request').get(pk=partner_id)
    if row.request.state!='approved': raise Conflict('Approved partnership required')
    allowed={'name_ar','name_fr','name_en','summary_ar','summary_fr','summary_en','website'}
    if set(content)!=allowed: raise ValidationError('Complete explicit content required')
    for key,value in content.items():
        if not isinstance(value,str) or len(value)>(200 if key.startswith('name_') or key=='website' else 3000):
            raise ValidationError('Invalid text length')
        if key.startswith('name_') and not value.strip(): raise ValidationError('Localized name required')
        setattr(row,key,value.strip())
    if row.website: URLValidator(schemes=['https'])(row.website)
    row.state=state
    row.public_visible=public_visible if state=='active' else False
    row.save()
    audit(actor,'partner.updated',row.pk,reason,state=state,public_visible=row.public_visible)
    return {'partner':row.pk,'state':row.state,'public_visible':row.public_visible}
