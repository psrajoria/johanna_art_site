"""
Shipping zones and price calculation.

Zones are fixed (Germany / rest of the EU / rest of the world). Johanna only
edits the *prices* per zone and shipping type in the admin.
"""

from decimal import Decimal

from django.utils.translation import gettext_lazy as _

ZONE_GERMANY = "de"
ZONE_EU = "eu"
ZONE_WORLD = "world"

ZONE_CHOICES = [
    (ZONE_GERMANY, _("Germany")),
    (ZONE_EU, _("European Union")),
    (ZONE_WORLD, _("Rest of the world")),
]

EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "GR", "HU",
    "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI",
    "ES", "SE",
}

# Countries offered at checkout. Anything else can ask via the contact form.
COUNTRY_NAMES = {
    "DE": _("Germany"),
    "AT": _("Austria"),
    "BE": _("Belgium"),
    "BG": _("Bulgaria"),
    "HR": _("Croatia"),
    "CY": _("Cyprus"),
    "CZ": _("Czech Republic"),
    "DK": _("Denmark"),
    "EE": _("Estonia"),
    "FI": _("Finland"),
    "FR": _("France"),
    "GR": _("Greece"),
    "HU": _("Hungary"),
    "IE": _("Ireland"),
    "IT": _("Italy"),
    "LV": _("Latvia"),
    "LT": _("Lithuania"),
    "LU": _("Luxembourg"),
    "MT": _("Malta"),
    "NL": _("Netherlands"),
    "PL": _("Poland"),
    "PT": _("Portugal"),
    "RO": _("Romania"),
    "SK": _("Slovakia"),
    "SI": _("Slovenia"),
    "ES": _("Spain"),
    "SE": _("Sweden"),
    "CH": _("Switzerland"),
    "GB": _("United Kingdom"),
    "NO": _("Norway"),
    "IS": _("Iceland"),
    "US": _("United States"),
    "CA": _("Canada"),
    "AU": _("Australia"),
    "NZ": _("New Zealand"),
    "JP": _("Japan"),
    "IN": _("India"),
    "SG": _("Singapore"),
    "AE": _("United Arab Emirates"),
}


def country_choices():
    from django.utils.encoding import force_str

    return sorted(COUNTRY_NAMES.items(), key=lambda kv: force_str(kv[1]))


def zone_for_country(code):
    if code == "DE":
        return ZONE_GERMANY
    if code in EU_COUNTRIES:
        return ZONE_EU
    return ZONE_WORLD


class ShippingUnavailable(Exception):
    """Raised when no price is configured for a zone / shipping type."""


def calculate_shipping(lines, country, free_over=None):
    """
    Shipping for `lines` (objects with .offer and .quantity) to `country`.

    Flat items (prints, cards) travel together: the flat price is charged once.
    Parcel items (originals, framed, large) are each their own parcel.
    Digital items cost nothing. Returns (total, estimate_text).
    """
    from .models import ShippingRate

    flat_units = 0
    parcel_units = 0
    for line in lines:
        cls = line.offer.shipping_class
        if cls == "flat":
            flat_units += line.quantity
        elif cls == "parcel":
            parcel_units += line.quantity

    if not flat_units and not parcel_units:
        return Decimal("0.00"), ""

    zone = zone_for_country(country)
    rates = {
        r.shipping_class: r for r in ShippingRate.objects.filter(zone=zone)
    }

    total = Decimal("0.00")
    estimates = []
    if flat_units:
        rate = rates.get("flat")
        if rate is None:
            raise ShippingUnavailable(zone)
        total += rate.price
        estimates.append(rate.estimate())
    if parcel_units:
        rate = rates.get("parcel")
        if rate is None:
            raise ShippingUnavailable(zone)
        total += rate.price * parcel_units
        estimates.append(rate.estimate())

    subtotal = sum((line.line_total for line in lines), Decimal("0.00"))
    if free_over and free_over > 0 and zone == ZONE_GERMANY and subtotal >= free_over:
        total = Decimal("0.00")

    estimate = next((e for e in estimates if e), "")
    return total, estimate
