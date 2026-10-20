from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from wagtail.models import Locale

from .emails import send_email, site_base_url

SUBJECTS = {
    "en": "{title} is available again",
    "de": "{title} ist wieder verfügbar",
}


def _artwork_url(artwork, lang):
    page = artwork
    try:
        page = artwork.get_translation_or_none(Locale.objects.get(language_code=lang)) or artwork
    except Locale.DoesNotExist:
        pass
    url = page.url or ""
    return url if url.startswith("http") else site_base_url() + url


def notify_available(artwork):
    """Email everyone waiting for an offer of this artwork that is purchasable again."""
    from artworks.models import ArtworkPage, Offer

    from .models import WaitlistRequest

    waiting = WaitlistRequest.objects.filter(offer__artwork=artwork, notified_at__isnull=True)
    if not waiting.exists():
        return 0
    # read fresh values: callers may hold a stale in-memory page
    artwork = ArtworkPage.objects.get(pk=artwork.pk)
    offers = {
        o.pk: o
        for o in Offer.objects.filter(artwork=artwork, is_active=True)
        if o.is_purchasable(artwork.status)
    }
    if not offers:
        return 0
    sent = 0
    for request in waiting.filter(offer_id__in=offers):
        lang = request.language if request.language in ("en", "de") else "en"
        offer = offers[request.offer_id]
        send_email(
            SUBJECTS[lang].format(title=artwork.title),
            "waitlist_available",
            {"title": artwork.title, "offer": offer.display_label, "url": _artwork_url(artwork, lang)},
            request.email,
            lang,
        )
        request.notified_at = timezone.now()
        request.save(update_fields=["notified_at"])
        sent += 1
    return sent
