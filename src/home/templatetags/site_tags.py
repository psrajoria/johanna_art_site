from decimal import Decimal, InvalidOperation

from django import template
from django.urls import translate_url
from django.utils import translation
from django.conf import settings

from wagtail.models import Locale, Site

register = template.Library()


def _current_root(request):
    site = Site.find_for_request(request)
    if not site:
        return None
    root = site.root_page
    language = translation.get_language()
    locale = Locale.objects.filter(language_code=language).first()
    if locale and root.locale_id != locale.pk:
        root = root.get_translation_or_none(locale) or root
    return root.specific


@register.simple_tag(takes_context=True)
def menu_pages(context):
    """Top navigation: the homepage's live children ticked 'Show in menus'."""
    request = context.get("request")
    root = _current_root(request) if request else None
    if not root:
        return []
    return list(root.get_children().live().in_menu().specific())


@register.simple_tag(takes_context=True)
def footer_pages(context):
    """Footer links: standard pages ticked 'Show in footer'."""
    from home.models import StandardPage

    request = context.get("request")
    root = _current_root(request) if request else None
    if not root:
        return []
    return list(
        StandardPage.objects.live().public().filter(
            show_in_footer=True, locale=root.locale
        ).order_by("path")
    )


@register.simple_tag(takes_context=True)
def home_url(context):
    request = context.get("request")
    root = _current_root(request) if request else None
    return root.url if root and root.url else "/"


@register.simple_tag(takes_context=True)
def language_links(context):
    """
    One entry per language: {code, name, url, active}. On Wagtail pages the
    link goes to the translated page; elsewhere to the same view in that language.
    """
    request = context["request"]
    page = context.get("page")
    current = translation.get_language()
    links = []
    for code, name in settings.LANGUAGES:
        url = None
        if page is not None and getattr(page, "pk", None):
            locale = Locale.objects.filter(language_code=code).first()
            translated = page.get_translation_or_none(locale) if locale else None
            if translated is not None and translated.live:
                url = translated.url
            elif code == page.locale.language_code:
                url = page.url
        if url is None:
            if page is not None and getattr(page, "pk", None):
                # No translation of this page yet: go to that language's homepage.
                with translation.override(code):
                    root = _current_root(request)
                url = root.url if root else "/"
            else:
                url = translate_url(request.get_full_path(), code)
        links.append(
            {"code": code, "name": name, "url": url, "active": code == current}
        )
    return links


@register.simple_tag(takes_context=True)
def alternate_links(context):
    """hreflang alternates for search engines (Wagtail pages only)."""
    page = context.get("page")
    request = context.get("request")
    if page is None or not getattr(page, "pk", None) or request is None:
        return []
    alternates = []
    for translation_page in page.get_translations(inclusive=True).live().public():
        url = translation_page.get_full_url(request)
        if url:
            alternates.append((translation_page.locale.language_code, url))
    return alternates


@register.filter
def localized(obj, name):
    """`{{ settings_obj|localized:"tagline" }}` -> tagline_de on German pages."""
    if translation.get_language() == "de":
        value = getattr(obj, f"{name}_de", "")
        if value:
            return value
    return getattr(obj, name, "")


@register.filter
def euro(value):
    """12.5 -> '€12.50' in English, '12,50 €' in German."""
    try:
        amount = Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return value
    text = f"{amount:,.2f}"
    if translation.get_language() == "de":
        text = text.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{text} €"
    return f"€{text}"


@register.filter
def cm(value):
    """Trim trailing zeros from a Decimal size."""
    try:
        return f"{Decimal(value):g}"
    except (InvalidOperation, TypeError, ValueError):
        return value


@register.filter
def startswith(path, prefix):
    """True when `path` is inside the section at `prefix` (never for the homepage)."""
    if not prefix or prefix in ("/", "/de/"):
        return False
    return path.startswith(prefix)
