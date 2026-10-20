from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import Order
from .shipping import country_choices

User = get_user_model()


def _attrs(**extra):
    attrs = {"class": "form-input"}
    attrs.update(extra)
    return attrs


class CheckoutForm(forms.Form):
    """
    Customer details. Address fields are only required when the cart contains
    something that has to be shipped; the digital-content waiver only when it
    contains a download.
    """

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs=_attrs(autocomplete="email")),
    )
    name = forms.CharField(
        label=_("Full name"),
        max_length=160,
        widget=forms.TextInput(attrs=_attrs(autocomplete="name")),
    )
    phone = forms.CharField(
        label=_("Phone (optional)"),
        max_length=40,
        required=False,
        widget=forms.TextInput(attrs=_attrs(autocomplete="tel")),
    )

    address_line1 = forms.CharField(
        label=_("Street and number"),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs=_attrs(autocomplete="address-line1")),
    )
    address_line2 = forms.CharField(
        label=_("Address line 2 (optional)"),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs=_attrs(autocomplete="address-line2")),
    )
    postal_code = forms.CharField(
        label=_("Postal code"),
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs=_attrs(autocomplete="postal-code")),
    )
    city = forms.CharField(
        label=_("City"),
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs=_attrs(autocomplete="address-level2")),
    )
    country = forms.ChoiceField(
        label=_("Country"),
        choices=country_choices,
        required=False,
        initial="DE",
        widget=forms.Select(attrs=_attrs(autocomplete="country")),
    )

    customer_note = forms.CharField(
        label=_("Note for Johanna (optional)"),
        required=False,
        widget=forms.Textarea(attrs=_attrs(rows=3)),
    )

    payment_method = forms.ChoiceField(
        label=_("How would you like to pay?"),
        choices=[],
        widget=forms.RadioSelect,
    )

    accept_terms = forms.BooleanField(
        required=True,
        error_messages={"required": _("Please accept the terms to place your order.")},
    )
    accept_digital_waiver = forms.BooleanField(required=False)

    # Honeypot: real visitors never see or fill this.
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, needs_shipping, has_digital, payment_choices, **kwargs):
        super().__init__(*args, **kwargs)
        self.needs_shipping = needs_shipping
        self.has_digital = has_digital
        self.fields["payment_method"].choices = payment_choices
        if len(payment_choices) == 1:
            self.fields["payment_method"].initial = payment_choices[0][0]
        if has_digital:
            self.fields["accept_digital_waiver"].required = True
            self.fields["accept_digital_waiver"].error_messages["required"] = _(
                "Please confirm this to receive your download."
            )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise forms.ValidationError("Spam detected.")
        if self.needs_shipping:
            for field in ("address_line1", "postal_code", "city", "country"):
                if not cleaned.get(field):
                    self.add_error(field, _("This field is required for delivery."))
        return cleaned


class RegisterForm(UserCreationForm):
    """Sign-up with email + password. The email doubles as the username."""

    email = forms.EmailField(
        label=_("Email"), widget=forms.EmailInput(attrs=_attrs(autocomplete="email"))
    )
    first_name = forms.CharField(
        label=_("Your name"),
        max_length=60,
        widget=forms.TextInput(attrs=_attrs(autocomplete="name")),
    )

    class Meta:
        model = User
        fields = ("first_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("password1", "password2"):
            self.fields[name].widget.attrs.update(_attrs(autocomplete="new-password"))
        self.fields["password1"].label = _("Password")
        self.fields["password2"].label = _("Repeat password")
        # The model's own `username` field is not shown; we fill it in save().
        self.fields.pop("username", None)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError(
                _("There is already an account with this email. Please log in.")
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class EmailLoginForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Email"),
        widget=forms.TextInput(attrs=_attrs(autocomplete="username", autofocus=True)),
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs=_attrs(autocomplete="current-password")),
    )

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class OrderLookupForm(forms.Form):
    number = forms.CharField(
        label=_("Order number"),
        max_length=20,
        widget=forms.TextInput(attrs=_attrs(placeholder="JL-2026-0001")),
    )
    email = forms.EmailField(
        label=_("Email used for the order"),
        widget=forms.EmailInput(attrs=_attrs()),
    )
