"""
Plain-text emails for orders. Each message exists in English and German;
the customer's language is stored on the order.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import translation

logger = logging.getLogger(__name__)


def site_base_url():
    return settings.WAGTAILADMIN_BASE_URL.rstrip("/")


def _shop_settings():
    from wagtail.models import Site

    from .models import ShopSettings

    site = Site.objects.filter(is_default_site=True).first()
    return ShopSettings.for_site(site) if site else None


def notify_address():
    shop = _shop_settings()
    return shop.notification_address if shop else settings.SHOP_NOTIFY_EMAIL


def send_email(subject, template, context, to, language="en", folder="shop/emails"):
    """Render `<folder>/<template>.<lang>.txt` and send it. Never raises."""
    if not to:
        return
    lang = language if language in ("en", "de") else "en"
    try:
        with translation.override(lang):
            body = render_to_string(f"{folder}/{template}.{lang}.txt", context)
        EmailMessage(subject=subject, body=body, to=[to]).send(fail_silently=False)
    except Exception:  # an email problem must never break checkout
        logger.exception("Could not send email %s to %s", template, to)


def order_context(order, **extra):
    context = {
        "order": order,
        "items": list(order.items.all()),
        "shop": _shop_settings(),
        "order_url": site_base_url() + order.get_absolute_url(),
    }
    context.update(extra)
    return context


SUBJECTS = {
    "order_placed": {
        "en": "Your order {number} — payment details",
        "de": "Deine Bestellung {number} — Zahlungsdetails",
    },
    "payment_received": {
        "en": "Payment received for order {number}",
        "de": "Zahlung für Bestellung {number} erhalten",
    },
    "shipped": {
        "en": "Your order {number} is on its way",
        "de": "Deine Bestellung {number} ist unterwegs",
    },
    "cancelled": {
        "en": "Your order {number} was cancelled",
        "de": "Deine Bestellung {number} wurde storniert",
    },
}


def _subject(kind, order):
    lang = order.language if order.language in ("en", "de") else "en"
    return SUBJECTS[kind][lang].format(number=order.number)


def _send_to_customer(kind, order):
    send_email(
        _subject(kind, order),
        kind,
        order_context(order),
        order.email,
        order.language,
    )


def send_order_placed(order):
    _send_to_customer("order_placed", order)
    owner = notify_address()
    if owner:
        send_email(
            f"New order {order.number} — €{order.total}",
            "owner_new_order",
            order_context(order),
            owner,
            "en",
        )


def send_payment_received(order):
    _send_to_customer("payment_received", order)


def send_shipped(order):
    _send_to_customer("shipped", order)


def send_cancelled(order):
    _send_to_customer("cancelled", order)
