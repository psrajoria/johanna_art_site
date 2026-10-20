import logging

from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.html import strip_tags

from shop.emails import site_base_url

logger = logging.getLogger(__name__)

CONFIRM_SUBJECT = {
    "en": "Please confirm your newsletter sign-up",
    "de": "Bitte bestätige deine Newsletter-Anmeldung",
}


def _lang(subscriber_or_lang):
    lang = getattr(subscriber_or_lang, "language", subscriber_or_lang)
    return lang if lang in ("en", "de") else "en"


def send_confirmation(subscriber):
    lang = _lang(subscriber)
    context = {"confirm_url": site_base_url() + subscriber.confirm_path(), "lang": lang}
    try:
        with translation.override(lang):
            body = render_to_string(f"newsletter/emails/confirm.{lang}.txt", context)
        EmailMultiAlternatives(CONFIRM_SUBJECT[lang], body, to=[subscriber.email]).send()
    except Exception:
        logger.exception("Could not send newsletter confirmation to %s", subscriber.email)


def _absolute(url):
    if not url:
        return ""
    return url if url.startswith("http") else site_base_url() + url


def _artwork_bits(campaign, lang):
    artwork = campaign.artwork
    if not artwork:
        return None
    from wagtail.models import Locale

    page = artwork
    try:
        translated = artwork.get_translation_or_none(Locale.objects.get(language_code=lang))
        page = translated or artwork
    except Exception:
        pass
    image_url = ""
    if page.main_image_id:
        image_url = _absolute(page.main_image.get_rendition("fill-1000x700|format-jpeg").url)
    price = artwork.from_price
    return {
        "title": page.title,
        "text": page.short_description,
        "url": _absolute(page.url),
        "image": image_url,
        "price": f"{price:.2f}".replace(".", ",") + " €" if lang == "de" and price else (f"€{price:.2f}" if price else ""),
        "palette": artwork.palette_list,
    }


def _message(campaign, lang, unsubscribe_url, to):
    subject = (campaign.subject_de if lang == "de" and campaign.subject_de else campaign.subject)
    intro = campaign.intro_de if lang == "de" and campaign.intro_de else campaign.intro
    context = {
        "subject": subject,
        "intro": intro,
        "artwork": _artwork_bits(campaign, lang),
        "lang": lang,
        "unsubscribe_url": unsubscribe_url,
        "site_url": site_base_url(),
    }
    with translation.override(lang):
        html = render_to_string("newsletter/emails/campaign.html", context)
    text = strip_tags(html.replace("</p>", "\n\n").replace("<br>", "\n"))
    text = "\n".join(line.strip() for line in text.splitlines())
    message = EmailMultiAlternatives(subject, text, to=[to])
    message.attach_alternative(html, "text/html")
    message.extra_headers["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    return message


def send_test(campaign, address):
    try:
        message = _message(campaign, "en", site_base_url() + "/newsletter/unsubscribe/test/", address)
        message.subject = "[TEST] " + message.subject
        message.send()
        if campaign.subject_de or campaign.intro_de:
            german = _message(campaign, "de", site_base_url() + "/newsletter/unsubscribe/test/", address)
            german.subject = "[TEST DE] " + german.subject
            german.send()
    except Exception:
        logger.exception("Could not send the test newsletter")


def send_campaign(campaign):
    from .models import Subscriber

    messages = []
    for sub in Subscriber.objects.filter(confirmed=True, unsubscribed_at__isnull=True):
        lang = _lang(sub)
        messages.append(_message(campaign, lang, site_base_url() + sub.unsubscribe_path(), sub.email))
    sent = 0
    connection = get_connection()
    try:
        connection.open()
        for message in messages:
            try:
                message.connection = connection
                sent += message.send() or 0
            except Exception:
                logger.exception("Newsletter failed for %s", message.to)
    finally:
        connection.close()
    campaign.sent_count = sent
    campaign.save_sent_count()
    return sent
