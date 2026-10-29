from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from .models import Authority, Delegation, Person, MemberAccountControl
from . import services


def ordinary_accounts():
    return get_user_model().objects.filter(is_staff=False,is_superuser=False).exclude(
        pk__in=Authority.objects.values('primary_id')).exclude(pk__in=Delegation.objects.values('user_id'))


def target_account(user_id, *, lock=False):
    query = get_user_model().objects.select_for_update() if lock else get_user_model().objects
    user = query.get(pk=user_id)
    if (user.is_staff or user.is_superuser or Authority.objects.filter(primary=user).exists()
            or Delegation.objects.filter(user=user).exists()):
        raise PermissionDenied('Administrative accounts are managed separately')
    return user


def status_for(user):
    try:
        control = user.member_control
    except MemberAccountControl.DoesNotExist:
        control = None
    state = control.state if control else ('active' if user.is_active else 'suspended')
    if not user.is_active and state == 'active':
        state = 'suspended'
    return state, control.epoch if control else 0


def control_for(user, expected_epoch):
    row, _ = MemberAccountControl.objects.get_or_create(user=user,defaults={'state':'active' if user.is_active else 'suspended'})
    if isinstance(expected_epoch,bool) or row.epoch != expected_epoch:
        raise services.Conflict('Reload the account before changing it')
    return row


@services.command('account.state')
def change_state(*, actor, user_id, state, expected_epoch, confirm, reason=''):
    if confirm is not True or state not in {'active','suspended','cancelled'} or not isinstance(reason,str) or len(reason)>3000:
        raise ValidationError('Confirmed account decision required')
    user = target_account(user_id,lock=True)
    control = control_for(user,expected_epoch)
    before = status_for(user)[0]
    control.state, control.epoch = state, control.epoch+1
    control.save(update_fields=['state','epoch','updated_at'])
    user.is_active = state == 'active'
    user.save(update_fields=['is_active'])
    services.audit(actor,'account.state.changed',user.pk,reason,before=before,state=state,epoch=control.epoch)
    return {'user':user.pk,'state':state}


@services.command('account.edit')
def edit_account(*, actor, user_id, expected_epoch, confirm, fields, reason=''):
    if confirm is not True or not isinstance(reason,str) or len(reason)>3000:
        raise ValidationError('Confirmed account edit required')
    user = target_account(user_id,lock=True)
    control = control_for(user,expected_epoch)
    from .account_forms import AccountEditForm
    form = AccountEditForm(fields, user=user)
    if not form.is_valid():
        raise ValidationError('Invalid account fields')
    allowed = {'username','email','first_name','last_name','full_name','contact','phone','profession'}
    if set(fields)-allowed:
        raise ValidationError('Unknown account field')
    changed=[]
    for name in ('username','email','first_name','last_name'):
        value=form.cleaned_data[name]
        if getattr(user,name)!=value:
            setattr(user,name,value);changed.append(name)
    user.full_clean(exclude=['password'])
    if changed:
        user.save(update_fields=changed)
    person=Person.objects.select_for_update().filter(user=user).first()
    if person:
        updates=[]
        for name in ('full_name','contact','phone','profession'):
            value=form.cleaned_data[name]
            if getattr(person,name)!=value:
                setattr(person,name,value);updates.append(name)
        person.full_clean(exclude=[field.name for field in person._meta.fields if field.name not in ('full_name','contact','phone','profession')])
        if updates: person.save(update_fields=updates)
        changed.extend('profile.'+name for name in updates)
    control.epoch+=1
    control.save(update_fields=['epoch','updated_at'])
    services.audit(actor,'account.details.changed',user.pk,reason,fields=changed,epoch=control.epoch)
    return {'user':user.pk}
