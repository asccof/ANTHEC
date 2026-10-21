import uuid
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .institutional_views import read_authority
from .member_views import localized
from .partner_labels import vocabulary
from .member_labels import vocabulary as member_vocabulary
from .partner_forms import PartnershipForm, PartnershipDecisionForm, PartnerForm
from .models import PartnershipRequest, Partner, Audit, RateBucket
from . import partner_services as service
from .services import digest
from .deployment import require_applications_enabled
from .public_presentation import labels as public_words

def context(request):
    language,partner_labels=vocabulary(request.GET.get('lang','ar'))
    labels=dict(member_vocabulary(language)[1]); labels.update(partner_labels)
    return {'language':language,'labels':labels,'direction':'rtl' if language=='ar' else 'ltr','owner_testing':getattr(settings,'ANTHEEC_OWNER_TESTING',False),'public_labels':public_words(language)}

@never_cache
@require_http_methods(['GET'])
@localized
def listing(request):
    ctx=context(request)
    rows=Partner.objects.filter(state='active',public_visible=True,request__state='approved').order_by('pk')
    # Only explicit public fields enter the public rendering context.
    ctx['partners']=[{'name':getattr(p,'name_'+ctx['language']),'summary':getattr(p,'summary_'+ctx['language']),'website':p.website} for p in rows]
    return render(request,'governance/partners.html',ctx)

@never_cache
@require_http_methods(['GET','POST'])
@localized
def request_partnership(request):
    ctx=context(request)
    form=PartnershipForm(request.POST if request.method=='POST' else None,labels=ctx['labels'])
    if request.method=='POST':
        require_applications_enabled()
        window=int(timezone.now().timestamp()//600)
        keys=[(digest(f'partnership-ip:{request.META.get("REMOTE_ADDR","")}:{window}'),5),(digest(f'partnership-global:{window}'),50)]
        with transaction.atomic():
            for key,limit in sorted(keys):
                bucket,_=RateBucket.objects.get_or_create(key=key)
                bucket=RateBucket.objects.select_for_update().get(pk=key)
                bucket.count+=1; bucket.save(update_fields=['count'])
                if bucket.count>limit: return HttpResponse('Try again later',status=429)
        if form.is_valid():
            PartnershipRequest.objects.create(**form.cleaned_data)
            return redirect(reverse('partnership_request')+'?lang='+ctx['language']+'&received=1')
    ctx.update(form=form,received=request.GET.get('received')=='1')
    return render(request,'governance/partnership_request.html',ctx,status=400 if request.method=='POST' and form.errors else 200)

@never_cache
@login_required(login_url='/admin/login/')
@require_http_methods(['GET'])
@localized
def register(request):
    read_authority(request, "partner.view"); ctx=context(request)
    ctx['requests']=list(PartnershipRequest.objects.order_by('-pk')[:100])
    ctx['records']=list(Partner.objects.order_by('-pk')[:100])
    for row in ctx['requests']: row.display_state=ctx['labels'][row.state]
    for row in ctx['records']:
        row.display_state=ctx['labels'][row.state]
        row.display_name=getattr(row,'name_'+ctx['language'])
    return render(request,'governance/partnership_register.html',ctx)

@never_cache
@login_required(login_url='/admin/login/')
@require_http_methods(['GET','POST'])
@localized
def review(request,request_id):
    read_authority(request, "partner.view"); ctx=context(request)
    row=get_object_or_404(PartnershipRequest,pk=request_id)
    form=PartnershipDecisionForm(request.POST if request.method=='POST' else None,labels=ctx['labels'],initial={'key':uuid.uuid4()})
    status=200
    if request.method=='POST':
        if form.is_valid():
            data=form.cleaned_data
            try:
                service.decide(request,key=str(data['key']),request_id=row.pk,decision=data['decision'],reason=data['reason'])
                return redirect(reverse('partnership_register')+'?lang='+ctx['language'])
            except PermissionDenied: form.add_error(None,ctx['labels']['error']); status=403
            except ValidationError: form.add_error(None,ctx['labels']['error']); status=400
        else: status=400
    from .capabilities import restrict_choices
    restrict_choices(request, form, 'decision', {'approved': 'partner.approve', 'rejected': 'partner.reject'})
    row.display_state=ctx['labels'][row.state]
    ctx.update(row=row,form=form,history=Audit.objects.filter(subject=str(row.pk),action__in=['partnership.approved','partnership.rejected']).order_by('pk'))
    return render(request,'governance/partnership_review.html',ctx,status=status)

@never_cache
@login_required(login_url='/admin/login/')
@require_http_methods(['GET','POST'])
@localized
def detail(request,partner_id):
    read_authority(request, "partner.view"); ctx=context(request)
    row=get_object_or_404(Partner,pk=partner_id)
    initial={name:getattr(row,name) for name in ['name_ar','name_fr','name_en','summary_ar','summary_fr','summary_en','website','state','public_visible']}
    initial['key']=uuid.uuid4()
    form=PartnerForm(request.POST if request.method=='POST' else None,labels=ctx['labels'],initial=initial)
    from .capabilities import allows
    for name in ('name_ar','name_fr','name_en','summary_ar','summary_fr','summary_en','website'):
        form.fields[name].disabled = not allows(request, 'partner.edit')
    form.fields['state'].choices = [(value, caption) for value, caption in form.fields['state'].choices
        if value == row.state or allows(request, 'partner.' + {'active':'activate','suspended':'suspend','cancelled':'cancel'}[value])]
    form.fields['public_visible'].disabled = not allows(request, 'partner.hide' if row.public_visible else 'partner.publish')
    partner_can_mutate = any(allows(request, 'partner.' + action) for action in ('edit','activate','suspend','cancel','publish','hide'))
    status=200
    if request.method=='POST':
        if form.is_valid():
            data=dict(form.cleaned_data); key=str(data.pop('key'))
            try:
                service.update(request,key=key,partner_id=row.pk,**data)
                return redirect(reverse('partner_detail',args=[row.pk])+'?lang='+ctx['language'])
            except PermissionDenied: form.add_error(None,ctx['labels']['error']); status=403
            except ValidationError: form.add_error(None,ctx['labels']['error']); status=400
        else: status=400
    ctx.update(row=row,display_name=getattr(row,'name_'+ctx['language']),form=form,partner_can_mutate=partner_can_mutate,history=Audit.objects.filter(subject=str(row.pk),action='partner.updated').order_by('pk'))
    return render(request,'governance/partner_detail.html',ctx,status=status)
