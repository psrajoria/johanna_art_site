from django.db import models


class PageView(models.Model):
    """One visit to one page. No cookies, no IP address, no personal data is stored."""

    day = models.DateField(db_index=True)
    group = models.CharField(
        max_length=40, blank=True, db_index=True,
        help_text="Same for the English and German version of a page.",
    )
    kind = models.CharField(max_length=12, db_index=True)
    title = models.CharField(max_length=200, blank=True)
    path = models.CharField(max_length=255)
    lang = models.CharField(max_length=5, blank=True)
    referrer = models.CharField(max_length=120, blank=True)
    device = models.CharField(max_length=8, blank=True)
    visitor = models.CharField(max_length=16, help_text="Anonymous, changes every day.")

    class Meta:
        indexes = [models.Index(fields=["day", "kind"])]


class Event(models.Model):
    LIKE = "like"
    UNLIKE = "unlike"
    ADD_TO_CART = "add_to_cart"
    BUY_NOW = "buy_now"
    ENQUIRY = "enquiry"
    ORDER = "order"
    INSTAGRAM = "instagram"
    WALL_PREVIEW = "wall_preview"
    NEWSLETTER = "newsletter"
    WAITLIST = "waitlist"
    SHARE = "share"

    NAMES = [
        (LIKE, "Heart"), (UNLIKE, "Heart removed"), (ADD_TO_CART, "Added to cart"),
        (BUY_NOW, "Buy now"), (ENQUIRY, "Message or commission"), (ORDER, "Order placed"),
        (INSTAGRAM, "Instagram click"), (WALL_PREVIEW, "Wall preview used"),
        (NEWSLETTER, "Newsletter sign-up"), (WAITLIST, "Waiting list"), (SHARE, "Shared"),
    ]
    # names a visitor's browser may report by itself
    BROWSER_NAMES = {LIKE, UNLIKE, INSTAGRAM, WALL_PREVIEW, SHARE}

    day = models.DateField(db_index=True)
    name = models.CharField(max_length=20, choices=NAMES, db_index=True)
    group = models.CharField(max_length=40, blank=True, db_index=True)
    title = models.CharField(max_length=200, blank=True)
    visitor = models.CharField(max_length=16, blank=True)
