"""One HTTP form and one atomic account/profile/application submission."""
import base64
from django.contrib.auth import login
from django.contrib import messages
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect
from django.urls import reverse
from . import member_services, services
from .member_forms import SignupForm, ProfileForm, ApplicationForm
from .member_views import context, go, auth_attempt
from .models import Person, Application, Membership

PROFILE_FIELDS = ('full_name', 'contact', 'phone', 'profession', 'directory_consent')
APPLICATION_FIELDS = ('address_category', 'correspondence_address', 'professional_address',
                      'residential_address', 'same_address', 'tier', 'applicant_capacity', 'capacity_other')


def intake(request, *, new_account):
    from .deployment import require_applications_enabled
    require_applications_enabled()
    ctx = context(request)
    initial = {}
    if not new_account:
        # Never create a second pending request or replace an existing membership.
        person = Person.objects.filter(user=request.user).first()
        if person:
            pending = Application.objects.filter(person=person, state='submitted').first()
            if pending:
                return redirect(reverse('member_application', args=[pending.pk]) + '?lang=' + ctx['language'])
            if Membership.objects.filter(application__person=person).exists():
                return go(request, 'member_home')
            initial = {name: getattr(person, name) for name in PROFILE_FIELDS}
            initial['notice'] = bool(person.verification_notice_at)
    posting = request.method == 'POST'
    status = 200
    if posting and new_account and not auth_attempt(request):
        ctx['error'] = ctx['labels']['limited']
        status, posting = 429, False  # Do not decode an uploaded image after budget denial.
    data = request.POST.copy() if posting else None
    if data is not None and not new_account:
        # Preserve existing-client submissions that already completed the profile.
        # Explicit blanks/unchecked browser checkboxes are never replaced by initials.
        for name, value in initial.items():
            if (name not in data and name != 'directory_consent'
                    and not (name == 'notice' and data.get('intake_profile') == '1')):
                data[name] = value
    account = SignupForm(data, labels=ctx['labels']) if new_account else None
    profile = ProfileForm(data, labels=ctx['labels'], initial=initial)
    application = ApplicationForm(data, request.FILES if posting else None, labels=ctx['labels'])
    forms = [form for form in (account, profile, application) if form is not None]
    if posting:
        valid = [form.is_valid() for form in forms]
        if all(valid):
            try:
                with transaction.atomic():
                    user = account.save() if account else request.user
                    if account:
                        from .privacy_notice import pop_ack, record
                        evidence = pop_ack(dict(account.cleaned_data))
                        services.audit(user, 'member.account.created', user.pk)
                        record(user, 'member.signup', user.pk, evidence)
                    member_services.update_profile(user, **{
                        **profile.cleaned_data, 'key': str(profile.cleaned_data['key'])})
                    payload = {name: application.cleaned_data[name] for name in APPLICATION_FIELDS}
                    payload.update({name: value for name, value in application.cleaned_data.items()
                                    if name.startswith('privacy_')})
                    result = member_services.submit_application(user,
                        key=str(application.cleaned_data['key']),
                        image_data=base64.b64encode(application.normalized_photo).decode(),
                        photo_consent=application.cleaned_data['photo_consent'], **payload)
                if account:
                    login(request, user)
                messages.success(request, ctx['labels']['application_received'])
                return redirect(reverse('member_application', args=[result['application']]) + '?lang=' + ctx['language'])
            except (IntegrityError, ValidationError, ObjectDoesNotExist, PermissionDenied):
                application.add_error(None, ctx['labels']['error'])
        if account is not None and not all(valid):
            services.audit(None, 'member.account.failed', 'signup')
        ctx['error'] = ctx['labels']['intake_errors']
        status = 400
    privacy_form = account or profile
    groups = []
    if account:
        groups.append((ctx['labels']['account_section'], [account[name] for name in ('username', 'password1', 'password2')]))
    groups.extend([
        (ctx['labels']['profile_section'], [profile[name] for name in PROFILE_FIELDS if name != 'directory_consent']),
        (ctx['labels']['application_section'], [application[name] for name in
            ('tier', 'applicant_capacity', 'capacity_other', 'address_category', 'correspondence_address',
             'same_address', 'professional_address', 'residential_address', 'photo')]),
        (ctx['labels']['consent_section'], [profile['notice'], application['photo_consent'], profile['directory_consent']]
         + ([privacy_form['privacy_acceptance']] if 'privacy_acceptance' in privacy_form.fields else [])),
    ])
    return render(request, 'governance/member_intake.html', {
        **ctx, 'title': ctx['labels']['signup_apply'] if account else ctx['labels']['apply'],
        'submit_label': ctx['labels']['signup_apply_submit'] if account else ctx['labels']['submit_application'],
        'form': account or application, 'account_form': account, 'profile_form': profile,
        'application_form': application, 'privacy_form': privacy_form, 'intake_forms': forms,
        'field_groups': groups, 'new_account': new_account,
    }, status=status)
