"""Owner-approved self-declared capacities, independent of membership tiers."""

from django.core.exceptions import ValidationError
import re

CAPACITIES = (
    "psychologist",
    "psychotherapist",
    "family_counsellor",
    "coach",
    "therapeutic_coach",
    "psychological_guide",
    "psychological_counsellor",
    "student",
    "interested",
    "other",
)


def validate_capacity(capacity, other):
    if capacity not in CAPACITIES or not isinstance(other, str) or len(other) > 200:
        raise ValidationError("Select a declared applicant capacity")
    if (capacity == "other") != bool(other.strip()):
        raise ValidationError("Specify another capacity only when Other is selected")
    return capacity, other.strip()


def validate_phone(value):
    if (
        not isinstance(value, str)
        or len(value) > 32
        or not re.fullmatch(r"[+0-9 ()/.\-]+", value)
        or not 7 <= sum(c.isdigit() for c in value) <= 15
    ):
        raise ValidationError("Enter a contact phone number containing 7 to 15 digits")
