import logging

from django.urls import reverse

from shop.emails import _shop_settings, notify_address, send_email, site_base_url

logger = logging.getLogger(__name__)

FOLDER = "contact/emails"

STATUS_SUBJECTS = {
    "quoted": {
        "en": "Your request {number} — a quote from Johanna",
        "de": "Deine Anfrage {number} — ein Angebot von Johanna",
    },
    "in_progress": {
        "en": "Your request {number} — I've started painting",
        "de": "Deine Anfrage {number} — ich habe angefangen zu malen",
    },
    "finished": {
        "en": "Your request {number} is finished",
        "de": "Deine Anfrage {number} ist fertig",
    },
    "shipped": {
        "en": "Your request {number} is on its way",
        "de": "Deine Anfrage {number} ist unterwegs",
    },
    "declined": {
        "en": "About your request {number}",
        "de": "Zu deiner Anfrage {number}",
    },
}


def _context(inquiry):
    try:
        admin_url = site_base_url() + reverse(
            "wagtailsnippets_contact_inquiry:edit", args=[inquiry.pk]
        )
    except Exception:
        admin_url = site_base_url() + "/admin/"
    return {
        "inquiry": inquiry,
        "shop": _shop_settings(),
        "status_url": site_base_url() + inquiry.get_status_url(),
        "admin_url": admin_url,
    }


def send_received(inquiry):
    """Confirmation to the visitor and an alert for Johanna."""
    lang = inquiry.language if inquiry.language in ("en", "de") else "en"
    subjects = {
        "en": f"We got your message ({inquiry.number})",
        "de": f"Deine Nachricht ist angekommen ({inquiry.number})",
    }
    context = _context(inquiry)
    send_email(
        subjects[lang], "inquiry_received", context, inquiry.email, lang, FOLDER
    )

    owner = notify_address()
    if owner:
        send_email(
            f"New {inquiry.get_inquiry_type_display().lower()} from {inquiry.name} ({inquiry.number})",
            "owner_new_inquiry",
            context,
            owner,
            "en",
            FOLDER,
        )


def send_status_update(inquiry, status):
    lang = inquiry.language if inquiry.language in ("en", "de") else "en"
    subject = STATUS_SUBJECTS[status][lang].format(number=inquiry.number)
    send_email(
        subject, f"request_{status}", _context(inquiry), inquiry.email, lang, FOLDER
    )
