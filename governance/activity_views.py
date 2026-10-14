import uuid
from django.conf import settings
from django.core.exceptions import ValidationError,PermissionDenied
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render,redirect,get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .institutional_views import read_authority
from .member_views import localized
from .member_labels import vocabulary as member_vocabulary
from .activity_labels import vocabulary
from .activity_forms import ActivityForm,RegistrationForm,DecisionForm,CheckinForm
from .models import Activity,Registration,Attendance,Audit,Document
from .deployment import require_applications_enabled,require_issuance_enabled
from . import services,activity_services


def context(request):
    language,extra=vocabulary(request.GET.get('lang','ar'))
    labels=dict(member_vocabulary(language)[1]);labels.update(extra)
    return dict(language=language,labels=labels,direction='rtl' if language=='ar' else 'ltr',owner_testing=getattr(settings,'ANTHEEC_OWNER_TESTING',False))

def go(request,name,*args):
    return redirect(reverse(name,args=args)+'?lang='+context(request)['language'])

def form_payload(data):
    data=dict(data);key=str(data.pop('key'));data['title']=data.pop('event_title')
    for field in ('starts_on','ends_on'):data[field]=data[field].isoformat()
    return key,data


@never_cache
@login_required(login_url='/members/login/')
@require_http_methods(['GET'])
@localized
def listing(request):
    ctx=context(request)
    ctx['activities']=Activity.objects.filter(ends_on__gte=timezone.localdate()).order_by('starts_on','pk')[:100]
    rows=list(Registration.objects.filter(Q(person__user=request.user,person__minor=False)|Q(person__guardian=request.user,person__minor=True)).select_related('activity','person').order_by('-pk')[:100])
    for row in rows:row.display_state=ctx['labels'][row.state]
    ctx['mine']=rows
    return render(request,'governance/activity_list.html',ctx)


@never_cache
@login_required(login_url='/members/login/')
@require_http_methods(['GET','POST'])
@localized
def participate(request,activity_id):
    row=get_object_or_404(Activity,pk=activity_id,ends_on__gte=timezone.localdate())
    ctx=context(request)
    form=RegistrationForm(request.POST if request.method=='POST' else None,user=request.user,activity=row,labels=ctx['labels'])
    status=200
    if request.method=='POST':
        require_applications_enabled()
        if form.is_valid():
            data=dict(form.cleaned_data);person=data.pop('person')
            try:
                services.register(row,person,request.user,**data)
                return go(request,'activity_list')
            except PermissionDenied:form.add_error(None,ctx['labels']['error']);status=403
            except ValidationError:form.add_error(None,ctx['labels']['error']);status=400
        else:status=400
    ctx.update(row=row,form=form)
    return render(request,'governance/activity_participate.html',ctx,status=status)


@never_cache
@login_required(login_url='/admin/login/')
@require_http_methods(['GET','POST'])
@localized
def register(request):
    read_authority(request);ctx=context(request)
    form=ActivityForm(request.POST if request.method=='POST' else None,labels=ctx['labels'],initial={'key':uuid.uuid4()})
    status=200
    if request.method=='POST':
        if form.is_valid():
            key,data=form_payload(form.cleaned_data)
            try:
                result=activity_services.create(request,key=key,**data)
                return go(request,'activity_admin_detail',result['activity'])
            except PermissionDenied:form.add_error(None,ctx['labels']['error']);status=403
            except ValidationError:form.add_error(None,ctx['labels']['error']);status=400
        else:status=400
    ctx.update(form=form,activities=Activity.objects.order_by('-pk')[:100])
    return render(request,'governance/activity_register.html',ctx,status=status)


@never_cache
@login_required(login_url='/admin/login/')
@require_http_methods(['GET','POST'])
@localized
def detail(request,activity_id):
    read_authority(request);ctx=context(request)
    row=get_object_or_404(Activity,pk=activity_id)
    initial={field:getattr(row,field) for field in ('starts_on','ends_on','capacity','allows_minors','consent_version','consent_text')}
    initial.update(event_title=row.title,key=uuid.uuid4())
    form=ActivityForm(request.POST if request.method=='POST' else None,labels=ctx['labels'],initial=initial)
    status=200
    if request.method=='POST':
        if form.is_valid():
            key,data=form_payload(form.cleaned_data)
            try:
                activity_services.update(request,key=key,activity_id=row.pk,**data)
                return go(request,'activity_admin_detail',row.pk)
            except PermissionDenied:form.add_error(None,ctx['labels']['error']);status=403
            except ValidationError:form.add_error(None,ctx['labels']['error']);status=400
        else:status=400
    rows=list(Registration.objects.filter(activity=row).select_related('person').order_by('-pk')[:100])
    attended=set(Attendance.objects.filter(registration__activity=row).values_list('registration_id',flat=True))
    for item in rows:
        item.display_state=ctx['labels'][item.state]
        item.display_attendance=ctx['labels']['present' if item.pk in attended else 'absent']
    ctx.update(row=row,form=form,registrations=rows)
    return render(request,'governance/activity_detail.html',ctx,status=status)


@never_cache
@login_required(login_url='/admin/login/')
@require_http_methods(['GET','POST'])
@localized
def admission(request,registration_id):
    read_authority(request);ctx=context(request)
    row=get_object_or_404(Registration.objects.select_related('activity','person','submitted_by'),pk=registration_id)
    form=DecisionForm(request.POST if request.method=='POST' and request.POST.get('operation')!='checkin' else None,labels=ctx['labels'],initial={'key':uuid.uuid4()})
    if request.method=='GET':
        choices=['cancel'] if row.state=='confirmed' else ['reject','cancel'] if ctx['owner_testing'] else ['accept','reject','cancel']
        form.fields['operation'].choices=[(value,ctx['labels'][value]) for value in choices]
    checkin=CheckinForm(request.POST if request.method=='POST' and request.POST.get('operation')=='checkin' else None,initial={'key':uuid.uuid4()})
    doc=Document.objects.filter(registration=row,kind='invitation',void=False).order_by('-pk').first()
    status=200;active=checkin if request.POST.get('operation')=='checkin' else form
    if request.method=='POST':
        if active.is_valid():
            data=active.cleaned_data; key=str(data['key'])
            try:
                operation=request.POST.get('operation')
                if operation=='checkin':
                    if not doc:raise ValidationError('Invitation required')
                    services.check_in(request,key=key,document_id=doc.pk)
                elif operation=='cancel':services.cancel_registration(request,key=key,registration_id=row.pk,reason=data['reason'])
                else:
                    if operation=='accept':require_issuance_enabled()
                    services.decide_registration(request,key=key,registration_id=row.pk,accept=operation=='accept',reason=data['reason'])
                return go(request,'activity_admission',row.pk)
            except PermissionDenied:active.add_error(None,ctx['labels']['error']);status=403
            except ValidationError:active.add_error(None,ctx['labels']['error']);status=400
        else:status=400
    ctx.update(row=row,form=form,checkin=checkin,can_checkin=bool(doc and services.document_status(doc)=='active'),
        display_state=ctx['labels'][row.state],display_attendance=ctx['labels']['present' if Attendance.objects.filter(registration=row).exists() else 'absent'],
        history=Audit.objects.filter(subject=str(row.pk),action__in=['registration.decided','registration.cancelled']).order_by('pk'))
    return render(request,'governance/activity_admission.html',ctx,status=status)
