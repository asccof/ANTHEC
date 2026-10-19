from django import forms
from django.db.models import Q
from .models import Person


class LabelForm(forms.Form):
    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.label = labels.get(name, field.label)


class ActivityForm(LabelForm):
    key = forms.UUIDField(widget=forms.HiddenInput)
    event_title = forms.CharField(max_length=200)
    starts_on = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    ends_on = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    capacity = forms.IntegerField(min_value=1, max_value=100000)
    allows_minors = forms.BooleanField(required=False)
    consent_version = forms.CharField(max_length=60, required=False)
    consent_text = forms.CharField(
        max_length=10000, required=False, widget=forms.Textarea
    )
    reason = forms.CharField(max_length=3000, widget=forms.Textarea)


class SourceTitleInput(forms.TextInput):
    def use_required_attribute(self, initial):
        # The source locale/action decides the requirement on the server.
        return False


class EditorialActivityForm(ActivityForm):
    editorial_version = forms.CharField(required=False, widget=forms.HiddenInput)
    translation_source = forms.ChoiceField(
        required=False,
        choices=[("ar", "العربية"), ("fr", "Français"), ("en", "English")],
        initial="ar",
    )
    translation_replace = forms.BooleanField(required=False)
    translation_public = forms.BooleanField(required=False)

    image_file = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png"}),
    )

    def __init__(self, *args, presentation=None, **kwargs):
        from .activity_editorial import TEXT_FIELDS, CATEGORIES, FORMATS

        labels = kwargs["labels"]
        super().__init__(*args, **kwargs)
        presentation = presentation or {}
        self.fields["event_title"].widget = SourceTitleInput()
        self.fields["category"] = forms.ChoiceField(
            required=False,
            label=labels["category"],
            choices=[(x, labels[x]) for x in CATEGORIES],
            initial=presentation.get("category", "meeting"),
        )
        self.fields["format"] = forms.ChoiceField(
            required=False,
            label=labels["format"],
            choices=[(x, labels[x]) for x in FORMATS],
            initial=presentation.get("format", "online"),
        )
        self.fields["translation_source"].label = labels["translation_source"]
        self.fields["translation_replace"].label = labels["translation_replace"]
        self.fields["translation_public"].label = labels["translation_public"]
        if (
            self.is_bound
            and self.data.get("translation_action") in {"preview", "direct"}
            and self.data.get("translation_source") in {"fr", "en"}
        ):
            self.fields["event_title"].required = False
        self.editorial_error = labels["error"]
        self.editorial_groups = []
        for lang in ("ar", "fr", "en"):
            names = []
            for field, limit in TEXT_FIELDS.items():
                if field == "title" and lang == "ar":
                    continue
                name = field + "_" + lang
                self.fields[name] = forms.CharField(
                    required=False,
                    max_length=limit,
                    label=labels["event_title" if field == "title" else field],
                    initial=presentation.get("translations", {})
                    .get(lang, {})
                    .get(field, ""),
                    widget=(
                        forms.TextInput()
                        if field in ("title", "summary", "location")
                        else forms.Textarea(attrs={"rows": 4, "dir": "auto"})
                    ),
                )
                names.append(name)
            self.editorial_groups.append((lang, names))
        for i in range(4):
            link = (presentation.get("links", []) + [{}] * 4)[i]
            for field in ("title", "url", "kind"):
                name = f"link_{i}_{field}"
                self.fields[name] = (
                    forms.ChoiceField(
                        required=False,
                        choices=[
                            ("resource", labels["resource"]),
                            ("video", labels["video"]),
                        ],
                        label=labels["link_kind"],
                        initial=link.get(field, "resource"),
                    )
                    if field == "kind"
                    else forms.CharField(
                        required=False,
                        max_length=1000 if field == "url" else 160,
                        label=labels["link_url" if field == "url" else "link_title"],
                        initial=link.get(field, ""),
                    )
                )
        self.fields["image_file"].label = labels["image_file"]
        self.fields["image_file"].help_text = labels["image_help"]
        for name, field in self.fields.items():
            field.widget.attrs["id"] = "activity-edit-" + name

    @property
    def translation_groups(self):
        return [
            (lang, [self[name] for name in names])
            for lang, names in self.editorial_groups
        ]

    @property
    def link_groups(self):
        return [
            [self[f"link_{i}_{field}"] for field in ("title", "url", "kind")]
            for i in range(4)
        ]

    def clean(self):
        from .activity_editorial import validate_presentation

        data = super().clean()
        try:
            data["presentation"] = validate_presentation(self.presentation_data(data))
        except forms.ValidationError:
            raise forms.ValidationError(self.editorial_error)
        return data

    @staticmethod
    def presentation_data(data):
        from .activity_editorial import TEXT_FIELDS

        result = {
            "category": data.get("category") or "meeting",
            "format": data.get("format") or "online",
            "translations": {},
            "links": [],
        }
        for lang in ("ar", "fr", "en"):
            result["translations"][lang] = {
                field: data.get(field + "_" + lang, "") for field in TEXT_FIELDS
            }
        result["translations"]["ar"]["title"] = data.get("event_title", "")
        for i in range(4):
            title, url = data.get(f"link_{i}_title", ""), data.get(f"link_{i}_url", "")
            if title or url:
                result["links"].append(
                    {
                        "title": title,
                        "url": url,
                        "kind": data.get(f"link_{i}_kind") or "resource",
                    }
                )
        return result


class EditorialDecisionForm(LabelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["id"] = self.__class__.__name__.lower() + "-" + name

    key = forms.UUIDField(widget=forms.HiddenInput)
    reason = forms.CharField(max_length=3000, widget=forms.Textarea(attrs={"rows": 2}))


class ActivityImageForm(EditorialDecisionForm):
    image_file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png"})
    )
    caption = forms.CharField(required=False, max_length=240)


class RegistrationForm(LabelForm):
    person = forms.ModelChoiceField(queryset=Person.objects.none())
    guardian_name = forms.CharField(max_length=200, required=False)
    guardian_capacity = forms.CharField(max_length=100, required=False)
    consent = forms.BooleanField(required=False)

    def __init__(self, *args, user, activity, **kwargs):
        super().__init__(*args, **kwargs)
        scope = Q(user=user, minor=False)
        if activity.allows_minors:
            scope |= Q(guardian=user, minor=True)
        self.fields["person"].queryset = Person.objects.filter(
            scope, verification_notice_at__isnull=False
        ).order_by("pk")
        self.fields["person"].label_from_instance = lambda row: row.full_name


class DecisionForm(LabelForm):
    key = forms.UUIDField(widget=forms.HiddenInput)
    operation = forms.ChoiceField(
        choices=[(x, x) for x in ("accept", "reject", "cancel")]
    )
    reason = forms.CharField(max_length=3000, widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        labels = kwargs["labels"]
        super().__init__(*args, **kwargs)
        self.fields["operation"].label = labels["decision"]
        self.fields["operation"].choices = [
            (x, labels[x]) for x in ("accept", "reject", "cancel")
        ]


class CheckinForm(forms.Form):
    key = forms.UUIDField(widget=forms.HiddenInput)
