from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Inquiry

MAX_REFERENCE_MB = 8


class InquiryForm(forms.ModelForm):
    reference_image = forms.ImageField(
        label=_("Reference photo (optional)"),
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"class": "form-input form-file", "accept": "image/*"}
        ),
        help_text=_("JPG, PNG or WebP, up to 8 MB."),
    )

    # Honeypot: real visitors never see or fill this.
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Inquiry
        fields = [
            "inquiry_type",
            "name",
            "email",
            "message",
            "size_wanted",
            "budget",
            "deadline",
            "reference_link",
            "reference_image",
        ]
        labels = {
            "inquiry_type": _("What is this about?"),
            "name": _("Your name"),
            "email": _("Email"),
            "message": _("Your message"),
            "size_wanted": _("Size (optional)"),
            "budget": _("Budget (optional)"),
            "deadline": _("Deadline (optional)"),
            "reference_link": _("Link to a reference (optional)"),
        }
        widgets = {
            "inquiry_type": forms.Select(attrs={"class": "form-input"}),
            "name": forms.TextInput(
                attrs={"class": "form-input", "autocomplete": "name"}
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "you@email.com",
                    "autocomplete": "email",
                }
            ),
            "message": forms.Textarea(attrs={"class": "form-input", "rows": 6}),
            "size_wanted": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "A4, A3, 40 × 50 cm …"}
            ),
            "budget": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g. 100–200 €"}
            ),
            "deadline": forms.DateInput(
                attrs={"class": "form-input", "type": "date"}
            ),
            "reference_link": forms.URLInput(
                attrs={"class": "form-input", "placeholder": "https://"}
            ),
        }

    def clean_reference_image(self):
        image = self.cleaned_data.get("reference_image")
        if image and image.size > MAX_REFERENCE_MB * 1024 * 1024:
            raise forms.ValidationError(
                _("Please choose a photo smaller than %(mb)d MB.")
                % {"mb": MAX_REFERENCE_MB}
            )
        return image

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise forms.ValidationError("Spam detected.")
        return cleaned
