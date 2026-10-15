"""Invitation presentation only; verification machine vocabulary stays stable."""
from .institutional_labels import LABELS

ROWS = {
    "type": ("نوع الدعوة", "Type d’invitation", "Invitation type"),
    "invitation": ("دعوة شخصية", "Invitation personnelle", "Personal invitation"),
    "activity invitation": ("دعوة لنشاط", "Invitation à une activité", "Activity invitation"),
    # Activities include the last calendar day, unlike annual membership terms.
    "valid_until": ("نهاية الصلاحية (اليوم مشمول)", "Fin de validité (jour inclus)", "Valid until (day included)"),
}


def vocabulary(language="ar"):
    language = language if language in LABELS else "ar"
    index = ("ar", "fr", "en").index(language)
    return language, {**LABELS[language], **{key: row[index] for key, row in ROWS.items()}}
