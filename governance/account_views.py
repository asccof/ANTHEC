import uuid
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.core.paginator import Paginator
from django.shortcuts import render,redirect,get_object_or_404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .operations_views import context
from .member_views import localized
from .capabilities import enforce,allows
from .account_forms import AccountEditForm,AccountConfirmationForm
from . import account_services as service


@never_cache
@login_required(login_url='/admin/login/')
@require_http_methods(['GET'])
@localized
def listing(request):
    enforce(request,'account.view')
    ctx=context(request)
    query=service.ordinary_accounts().select_related('member_control','person').order_by('-pk')
    if request.GET.get('q'):query=query.filter(username__icontains=request.GET['q'][:150])
    page=Paginator(query,25).get_page(request.GET.get('page'))
    for user in page:
        user.account_label=ctx['labels']['account_'+service.status_for(user)[0]]
    return render(request,'governance/accounts.html',{**ctx,'page':page})


@never_cache
@login_required(login_url='/admin/login/')
@require_http_methods(['GET','POST'])
@localized
def detail(request,user_id):
    enforce(request,'account.view')
    user=get_object_or_404(service.ordinary_accounts().select_related('person','member_control'),pk=user_id)
    ctx=context(request)
    state,epoch=service.status_for(user)
    initial={'key':uuid.uuid4(),'expected_epoch':epoch}
    confirm=AccountConfirmationForm(request.POST if request.method=='POST' else None,labels=ctx['labels'],initial=initial,auto_id='id_edit_%s')
    editing=request.method=='POST' and request.POST.get('action')=='edit'
    form=AccountEditForm(request.POST if editing else None,user=user,labels=ctx['labels'])
    status=200
    if request.method=='POST':
        action=request.POST.get('action')
        cap={'active':'activate','suspended':'suspend','cancelled':'cancel','edit':'edit'}.get(action)
        enforce(request,'account.view','account.'+(cap or 'invalid'))
        if confirm.is_valid() and (not editing or form.is_valid()):
            data=confirm.cleaned_data
            common=dict(key=str(data['key']),user_id=user.pk,expected_epoch=data['expected_epoch'],confirm=data['confirm'],reason=data['reason'])
            try:
                if editing:service.edit_account(request,fields=form.cleaned_data,**common)
                else:service.change_state(request,state=action,**common)
                return redirect(reverse('member_account',args=[user.pk])+'?lang='+ctx['language']+'&saved=1')
            except PermissionDenied:
                raise
            except (ValidationError,IntegrityError):
                confirm.add_error(None,ctx['labels']['account_stale'])
        status=400
    actions=[dict(state=value,caption=ctx['labels']['account_'+verb])
             for value,verb in [('suspended','suspend'),('cancelled','cancel'),('active','activate')]
             if value!=state and allows(request,'account.'+verb)]
    for action in actions:
        action['form']=AccountConfirmationForm(request.POST if request.method=='POST' and request.POST.get('action')==action['state'] else None, labels=ctx['labels'], initial=initial, auto_id='id_'+action['state']+'_%s')
        if request.method=='POST' and request.POST.get('action')==action['state']:
            action['form']=confirm
            action['form'].auto_id='id_'+action['state']+'_%s'
    return render(request,'governance/account_detail.html',{**ctx,'target':user,'state_label':ctx['labels']['account_'+state],
        'confirmation':confirm,'edit_form':form,'actions':actions,'can_edit':allows(request,'account.edit'),
        'saved':request.GET.get('saved')=='1'},status=status)
