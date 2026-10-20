"""Privacy-friendly visit counting: no cookies, no IP stored, honours Do-Not-Track."""

import hashlib
import re
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone

from .models import Event, PageView

BOT = re.compile(
    r"bot|crawl|spider|slurp|facebookexternalhit|preview|monitor|uptime|headless|curl|wget|python-requests",
    re.I,
)
MOBILE = re.compile(r"mobile|android|iphone|ipad", re.I)

KINDS = {"ArtworkPage": "artwork", "BlogPostPage": "blog", "HomePage": "home"}


def _wanted(request):
    if request.META.get("HTTP_DNT") == "1" or request.META.get("HTTP_SEC_GPC") == "1":
        return False
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and user.is_staff:
        return False  # her own visits should not count
    return not BOT.search(request.META.get("HTTP_USER_AGENT", ""))


def visitor_id(request):
    """An anonymous id that changes every day, so nobody can be followed over time."""
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
    raw = f"{settings.SECRET_KEY}|{timezone.localdate()}|{ip}|{request.META.get('HTTP_USER_AGENT', '')}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _referrer_host(request):
    ref = request.META.get("HTTP_REFERER", "")
    if not ref:
        return ""
    host = urlparse(ref).netloc.lower().removeprefix("www.")
    return "" if host == request.get_host().lower().removeprefix("www.") else host[:120]


def _default_locale_title(page):
    try:
        from wagtail.models import Locale

        default = Locale.get_default()
        if page.locale_id != default.pk:
            source = page.get_translation_or_none(default)
            if source:
                return source.title
    except Exception:
        pass
    return page.title


def record_page_view(page, request):
    try:
        if request.method != "GET" or not _wanted(request):
            return
        PageView.objects.create(
            day=timezone.localdate(),
            group=str(page.translation_key),
            kind=KINDS.get(page.specific_class.__name__, "page"),
            title=_default_locale_title(page)[:200],
            path=request.path[:255],
            lang=(getattr(request, "LANGUAGE_CODE", "") or "")[:5],
            referrer=_referrer_host(request),
            device="mobile" if MOBILE.search(request.META.get("HTTP_USER_AGENT", "")) else "desktop",
            visitor=visitor_id(request),
        )
    except Exception:
        pass  # counting visitors must never break a page


def track(request, name, page=None, title=""):
    """Record something a visitor did (added to cart, sent a message, …)."""
    try:
        if not _wanted(request):
            return
        group = str(page.translation_key) if page is not None else ""
        if page is not None and not title:
            title = _default_locale_title(page)
        Event.objects.create(
            day=timezone.localdate(), name=name, group=group, title=title[:200],
            visitor=visitor_id(request),
        )
    except Exception:
        pass
