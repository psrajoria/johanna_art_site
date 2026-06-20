from django import forms

from .models import Inquiry


class InquiryForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        fields = [
            "inquiry_type",
            "name",
            "email",
            "message",
            "budget",
            "deadline",
            "reference_link",
        ]

        widgets = {
            "inquiry_type": forms.Select(attrs={"class": "form-input"}),
            "name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Your name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-input", "placeholder": "your@email.com"}
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-input form-textarea",
                    "placeholder": "Tell Johanna what you are interested in...",
                    "rows": 6,
                }
            ),
            "budget": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Optional, e.g. 100–200 €",
                }
            ),
            "deadline": forms.DateInput(
                attrs={
                    "class": "form-input",
                    "type": "date",
                }
            ),
            "reference_link": forms.URLInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Optional link to reference photo",
                }
            ),
        }
