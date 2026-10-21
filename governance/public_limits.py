"""Explicit shared-ingress budgets; never interpret untrusted proxy headers as clients."""
import unicodedata
from datetime import timedelta
from django.conf import settings
from django.db import transaction, connection
from django.utils import timezone
from .models import RateBucket
from .services import digest


# Deliberate whole-service ceilings, not measured capacity or DDoS guarantees.
HOSTED_LIMITS = {'auth': (300, 200), 'verify': (600, 300), 'partnership': (600, 50)}


def prune_expired(now=None):
    if not any(getattr(settings, name, False) for name in
               ('ANTHEEC_OPERATIONAL', 'ANTHEEC_OWNER_TESTING', 'ANTHEEC_PUBLIC_PREVIEW')):
        return
    now = now or timezone.now()
    with transaction.atomic():
        # All fixed windows are at most ten minutes; retain a full hour.
        stale = RateBucket.objects.filter(created_at__lt=now - timedelta(hours=1)).order_by('created_at', 'key')
        if connection.vendor == 'postgresql':
            stale = stale.select_for_update(skip_locked=True)
        expired = list(stale.values_list('pk', flat=True)[:1000])
        if expired:
            RateBucket.objects.filter(pk__in=expired).delete()


def consume(request, scope, *, identity=None):
    period, ceiling = HOSTED_LIMITS[scope]
    now = timezone.now()
    window = int(now.timestamp() // period)
    operational = getattr(settings, 'ANTHEEC_OPERATIONAL', False)
    if operational:
        budgets = [(digest(f'operational-{scope}-global:{window}'), ceiling)]
        if scope == 'auth':
            # Separate account budget prevents one account's mistakes from
            # imposing a ten-attempt ceiling on all users behind the ingress.
            name = unicodedata.normalize('NFKC', str(identity or '')).strip().casefold()[:150]
            budgets.append((digest(f'operational-auth-account:{name}:{window}'), 10))
    else:
        peer = request.META.get('REMOTE_ADDR', '')
        if scope == 'partnership':
            budgets = [(digest(f'partnership-ip:{peer}:{window}'), 5),
                       (digest(f'partnership-global:{window}'), 50)]
        else:
            prefix = 'member-auth' if scope == 'auth' else 'verify'
            budgets = [(digest(f'{prefix}:{peer}:{window}'), 10 if scope == 'auth' else 30)]
    if operational:
        prune_expired(now)
    with transaction.atomic():
        # Global lock always precedes account creation in operational mode.
        # A denied global attempt must not create attacker-controlled rows.
        for key, limit in (budgets if operational else sorted(budgets)):
            bucket, _ = RateBucket.objects.get_or_create(key=key)
            bucket = RateBucket.objects.select_for_update().get(pk=key)
            if operational and bucket.count >= limit:
                return False
            bucket.count += 1
            bucket.save(update_fields=['count'])
            if bucket.count > limit:
                return False
    return True
