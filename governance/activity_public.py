"""Shared read-only publication rules for the activity listing and homepage."""
from django.db.models import Prefetch
from django.utils import timezone
from .models import Activity, ActivityImage
from . import activity_editorial


def decorate_activity(row, language):
    row.content = activity_editorial.display(row, language)
    row.ended = row.ends_on < timezone.localdate()
    return row


def image_query():
    return Prefetch(
        "editorial_images",
        queryset=ActivityImage.objects.filter(active=True).defer("jpeg").order_by("pk"),
        to_attr="public_images",
    )


def published_activities(*, past=False):
    today = timezone.localdate()
    rows = Activity.objects.filter(is_published=True).prefetch_related(image_query())
    return (rows.filter(ends_on__lt=today).order_by("-starts_on", "-pk") if past
            else rows.filter(ends_on__gte=today).order_by("starts_on", "pk"))


def homepage_activities(language):
    return [dict(past=past, activities=[decorate_activity(row, language)
            for row in published_activities(past=past)[:3]]) for past in (False, True)]
