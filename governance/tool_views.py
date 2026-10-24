import base64
from django.db import transaction
from django.db.models import Case, When, Value, BooleanField
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.core.exceptions import ValidationError, PermissionDenied
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import MemberTool, ToolRequest
from .member_views import localized
from .partner_views import context as public_context
from .tool_labels import vocabulary
from .tool_forms import ToolForm, ToolRequestForm, ToolReviewForm
from . import services, tool_services
from .deployment import require_applications_enabled


def context(request):
    ctx = public_context(request)
    ctx['labels'].update(vocabulary(ctx['language'])[1])
    return ctx


def decorate(row, language):
    row.content = row.public_values(language)
    row.safe_website = ''
    if row.website:
        from urllib.parse import urlsplit
        from django.core.validators import URLValidator
        try:
            URLValidator(schemes=['https'])(row.website)
            if not (urlsplit(row.website).username or urlsplit(row.website).password):
                row.safe_website = row.website
        except ValidationError:
            pass
    return row


def tool_queryset():
    return MemberTool.objects.defer('image').annotate(has_image=Case(
        When(image=b'', then=Value(False)), default=Value(True), output_field=BooleanField()))


def public_tool(tool_id):
    return get_object_or_404(tool_queryset(), pk=tool_id, published=True)


@never_cache
@require_http_methods(['GET','HEAD'])
@localized
def listing(request):
    ctx = context(request)
    page = Paginator(tool_queryset().filter(published=True), 12).get_page(request.GET.get('page'))
    ctx.update(page=page, tools=[decorate(row, ctx['language']) for row in page])
    return render(request, 'governance/tools.html', ctx)


@never_cache
@require_http_methods(['GET','HEAD'])
@localized
def detail(request, tool_id):
    ctx = context(request)
    row = decorate(public_tool(tool_id), ctx['language'])
    return render(request, 'governance/tool_detail.html', {**ctx,'tool':row})


@never_cache
@require_http_methods(['GET','HEAD'])
def image(request, tool_id, serial):
    row = get_object_or_404(MemberTool.objects.only('image'), pk=tool_id, image_serial=serial, published=True)
    if not row.image:
        from django.http import Http404
        raise Http404()
    response = HttpResponse(bytes(row.image), content_type='image/jpeg')
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@never_cache
@require_http_methods(['GET','POST'])
@localized
def request_tool(request, tool_id):
    ctx = context(request)
    row = decorate(public_tool(tool_id), ctx['language'])
    if request.method == 'POST':
        require_applications_enabled()
        from .public_limits import consume
        if not consume(request, 'tool_request'):
            return HttpResponse(ctx['labels']['limited'], status=429)
    form = ToolRequestForm(request.POST if request.method == 'POST' else None, labels=ctx['labels'], tool_id=row.pk)
    if request.method == 'POST' and form.is_valid():
        from .privacy_notice import pop_ack, record
        data = dict(form.cleaned_data)
        evidence = pop_ack(data)
        nonce = data.pop('token')
        with transaction.atomic():
            # Serialize publication/removal against intake; no private data on public views.
            current = get_object_or_404(MemberTool.objects.select_for_update(), pk=row.pk, published=True)
            saved, created = ToolRequest.objects.get_or_create(submission_key=nonce,
                defaults={**data,'tool':current,'tool_title':current.public_values(ctx['language'])['title'],'language':ctx['language']})
            if not created and (saved.tool_id != row.pk or any(getattr(saved, key) != value for key,value in data.items())):
                form.add_error(None, ctx['labels']['expired'])
            else:
                if created:
                    record(request.user if request.user.is_authenticated else None, 'tool.request', saved.pk, evidence)
                    services.audit(request.user if request.user.is_authenticated else None, 'tool.request.submitted', saved.pk, tool=row.pk)
                return redirect(reverse('tool_request',args=[row.pk])+'?lang='+ctx['language']+'&received=1')
    return render(request, 'governance/tool_request.html', {**ctx,'tool':row,'form':form,
        'received':request.GET.get('received')=='1'}, status=400 if form.errors else 200)


def primary(request):
    with transaction.atomic():
        services.authorize(request, primary_only=True, recent=False)


@never_cache
@login_required(login_url='/admin/login/')
@require_http_methods(['GET'])
@localized
def register(request):
    primary(request)
    ctx = context(request)
    rows = MemberTool.objects.defer('image')
    page = Paginator(ToolRequest.objects.select_related('tool').defer('tool__image').order_by('-pk'), 25).get_page(request.GET.get('page'))
    state = request.GET.get('state','')
    if state in {'submitted','contacted','closed'}:
        page = Paginator(ToolRequest.objects.filter(state=state).select_related('tool').defer('tool__image').order_by('-pk'), 25).get_page(request.GET.get('page'))
    return render(request,'governance/tool_register.html',{**ctx,'tools':rows,'page':page,'state_filter':state})


@never_cache
@login_required(login_url='/admin/login/')
@require_http_methods(['GET','POST'])
@localized
def edit(request, tool_id=None):
    primary(request)
    ctx = context(request)
    row = get_object_or_404(MemberTool,pk=tool_id) if tool_id else None
    form = ToolForm(request.POST if request.method=='POST' else None, request.FILES if request.method=='POST' else None,
                    instance=row, labels=ctx['labels'])
    if request.method=='POST' and form.is_valid():
        fields = {name:form.cleaned_data[name] for name in form.Meta.fields}
        try:
            result = tool_services.save_tool(request,key=str(form.cleaned_data['key']),tool_pk=tool_id,fields=fields,
                image_data=base64.b64encode(form.normalized_image).decode() if form.normalized_image else None,
                remove_image=form.cleaned_data['remove_image'])
            return redirect(reverse('tool_edit',args=[result['tool']])+'?lang='+ctx['language']+'&saved=1')
        except (ValidationError, PermissionDenied):
            form.add_error(None,ctx['labels']['error'])
    return render(request,'governance/tool_edit.html',{**ctx,'form':form,'tool':row,'saved':request.GET.get('saved')=='1'},status=400 if form.errors else 200)


@never_cache
@login_required(login_url='/admin/login/')
@require_http_methods(['GET','POST'])
@localized
def review(request, request_id):
    primary(request)
    ctx = context(request)
    row = get_object_or_404(ToolRequest,pk=request_id)
    form = ToolReviewForm(request.POST if request.method=='POST' else None, labels=ctx['labels'],initial={'state':row.state,'notes':row.notes})
    if request.method=='POST' and form.is_valid():
        try:
            tool_services.review_request(request,key=str(form.cleaned_data['key']),request_id=row.pk,
                state=form.cleaned_data['state'], notes=form.cleaned_data['notes'])
            return redirect(reverse('tool_review',args=[row.pk])+'?lang='+ctx['language']+'&saved=1')
        except (ValidationError, PermissionDenied):
            form.add_error(None,ctx['labels']['error'])
    return render(request,'governance/tool_review.html',{**ctx,'row':row,'form':form,'saved':request.GET.get('saved')=='1'},status=400 if form.errors else 200)


@never_cache
@login_required(login_url='/admin/login/')
@require_http_methods(['GET','HEAD'])
def admin_image(request, tool_id, serial):
    primary(request)
    row = get_object_or_404(MemberTool,pk=tool_id,image_serial=serial)
    if not row.image:
        from django.http import Http404
        raise Http404()
    response = HttpResponse(bytes(row.image),content_type='image/jpeg')
    response['X-Content-Type-Options'] = 'nosniff'
    return response
