import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import RichTextField

from config.panels import ReadOnlyHTMLPanel

from .shipping import ZONE_CHOICES, country_choices


def new_token():
    return secrets.token_urlsafe(24)


@register_setting(icon="form")
class ShopSettings(BaseSiteSetting):
    """Payment details, notification address and shop rules."""

    notify_email = models.EmailField(
        "Order notification email",
        blank=True,
        help_text="Johanna gets an email here for every new order and message.",
    )

    paypal_email = models.EmailField(
        "PayPal account email",
        blank=True,
        default="payments@example.com",
        help_text="Customers are asked to send payment to this PayPal account.",
    )
    paypal_me_handle = models.CharField(
        "PayPal.me name",
        max_length=60,
        blank=True,
        default="johanna-dummy",
        help_text=(
            "Optional. The part after paypal.me/ in your PayPal.me link. If set, "
            "customers get a one-click button with the exact amount filled in."
        ),
    )

    bank_account_holder = models.CharField(max_length=120, blank=True, default="Johanna Lackner")
    bank_iban = models.CharField(
        "IBAN",
        max_length=40,
        blank=True,
        default="DE00 0000 0000 0000 0000 00",
        help_text="Leave empty to hide bank transfer as a payment option.",
    )
    bank_bic = models.CharField("BIC", max_length=20, blank=True)
    bank_name = models.CharField(max_length=120, blank=True)

    payment_instructions = RichTextField(
        blank=True,
        default=(
            "<p>Please send the total amount via PayPal (Goods &amp; Services) or "
            "by bank transfer, and write your <b>order number</b> in the payment "
            "note. As soon as your payment arrives, we will confirm it by email "
            "and get your order ready.</p>"
        ),
    )
    payment_instructions_de = RichTextField(
        "Payment instructions (German)",
        blank=True,
        default=(
            "<p>Bitte sende den Gesamtbetrag per PayPal (Waren &amp; "
            "Dienstleistungen) oder per Überweisung und gib deine "
            "<b>Bestellnummer</b> als Verwendungszweck an. Sobald die Zahlung "
            "eingegangen ist, bestätigen wir dir das per E-Mail und machen deine "
            "Bestellung versandfertig.</p>"
        ),
    )

    free_shipping_over = models.DecimalField(
        "Free shipping in Germany from",
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text="Order value (€) from which shipping within Germany is free. 0 = never.",
    )

    commission_base_price = models.DecimalField(
        "Commission: base price (€)", max_digits=7, decimal_places=2, default=30,
        help_text="Used for the rough price shown on the commission form. Set both prices to 0 to hide the estimate.",
    )
    commission_price_per_100cm2 = models.DecimalField(
        "Commission: price per 100 cm² (€)", max_digits=6, decimal_places=2, default=3.5,
        help_text="Added to the base price for each 100 square centimetres (10 × 10 cm).",
    )

    seller_name = models.CharField(
        "Name on invoices", max_length=120, default="Johanna Lackner",
        help_text="Your full name (or business name) exactly as it must appear on invoices.",
    )
    seller_address = models.TextField(
        "Address on invoices", blank=True,
        help_text="Street, postcode and city, one per line. Required on German invoices.",
    )
    tax_number = models.CharField(
        "Tax number (Steuernummer)", max_length=40, blank=True,
        help_text="From your tax office. Needed on invoices unless you give a VAT ID.",
    )
    vat_id = models.CharField("VAT ID (USt-IdNr.)", max_length=20, blank=True)
    vat_rate = models.DecimalField(
        "VAT rate included in prices (%)", max_digits=4, decimal_places=1, default=19,
        help_text="Only used when you are NOT a small business. Ask your tax advisor.",
    )

    small_business_vat_exempt = models.BooleanField(
        "Small business (Kleinunternehmer, §19 UStG)",
        default=True,
        help_text=(
            "Tick if no VAT is charged. A note is then shown at checkout. "
            "Ask your tax advisor if you are unsure."
        ),
    )

    digital_license = RichTextField(
        "Digital download licence",
        blank=True,
        default=(
            "<p>Digital downloads are for <b>personal use only</b>: you may print "
            "them for yourself or as a gift. You may not resell, redistribute or "
            "use them commercially, and the artwork stays © Johanna Lackner.</p>"
        ),
    )
    digital_license_de = RichTextField(
        "Digital download licence (German)",
        blank=True,
        default=(
            "<p>Digitale Downloads sind nur für den <b>privaten Gebrauch</b>: "
            "Du darfst sie für dich selbst oder als Geschenk ausdrucken. Der "
            "Weiterverkauf, die Weitergabe und die kommerzielle Nutzung sind nicht "
            "erlaubt; das Urheberrecht bleibt bei Johanna Lackner.</p>"
        ),
    )

    panels = [
        FieldPanel("notify_email"),
        MultiFieldPanel(
            [
                FieldPanel("paypal_email"),
                FieldPanel("paypal_me_handle"),
            ],
            heading="PayPal",
        ),
        MultiFieldPanel(
            [
                FieldPanel("bank_account_holder"),
                FieldPanel("bank_iban"),
                FieldPanel("bank_bic"),
                FieldPanel("bank_name"),
            ],
            heading="Bank transfer",
        ),
        FieldPanel("payment_instructions"),
        FieldPanel("payment_instructions_de"),
        FieldPanel("free_shipping_over"),
        MultiFieldPanel(
            [FieldPanel("commission_base_price"), FieldPanel("commission_price_per_100cm2")],
            heading="Rough price on the commission form",
        ),
        MultiFieldPanel(
            [
                FieldPanel("seller_name"),
                FieldPanel("seller_address"),
                FieldPanel("tax_number"),
                FieldPanel("vat_id"),
                FieldPanel("small_business_vat_exempt"),
                FieldPanel("vat_rate"),
            ],
            heading="Business details (printed on invoices)",
        ),
        FieldPanel("digital_license"),
        FieldPanel("digital_license_de"),
    ]

    class Meta:
        verbose_name = "Shop settings"

    @property
    def has_placeholder_details(self):
        return "example.com" in self.paypal_email or self.bank_iban.startswith("DE00")

    @property
    def notification_address(self):
        return self.notify_email or settings.SHOP_NOTIFY_EMAIL

    def instructions(self):
        if translation.get_language() == "de" and self.payment_instructions_de:
            return self.payment_instructions_de
        return self.payment_instructions

    def license_text(self):
        if translation.get_language() == "de" and self.digital_license_de:
            return self.digital_license_de
        return self.digital_license


class ShippingRate(models.Model):
    """Price for one shipping type within one zone."""

    zone = models.CharField(max_length=10, choices=ZONE_CHOICES)
    shipping_class = models.CharField(
        max_length=20,
        choices=[
            ("flat", _("Flat / tube (prints, cards)")),
            ("parcel", _("Parcel (originals, framed, large)")),
        ],
    )
    price = models.DecimalField(max_digits=6, decimal_places=2)
    delivery_estimate = models.CharField(
        max_length=80, blank=True, help_text="e.g. 3–5 working days"
    )
    delivery_estimate_de = models.CharField(
        "Delivery estimate (German)",
        max_length=80,
        blank=True,
        help_text="e.g. 3–5 Werktage",
    )

    panels = [
        FieldPanel("zone"),
        FieldPanel("shipping_class"),
        FieldPanel("price"),
        FieldPanel("delivery_estimate"),
        FieldPanel("delivery_estimate_de"),
    ]

    class Meta:
        ordering = ["zone", "shipping_class"]
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "shipping_class"], name="unique_rate_per_zone_class"
            )
        ]
        verbose_name = "shipping price"
        verbose_name_plural = "shipping prices"

    def __str__(self):
        return f"{self.get_zone_display()} · {self.get_shipping_class_display()} · €{self.price}"

    def estimate(self):
        if translation.get_language() == "de" and self.delivery_estimate_de:
            return self.delivery_estimate_de
        return self.delivery_estimate


class Order(models.Model):
    STATUS_AWAITING = "awaiting_payment"
    STATUS_PAID = "paid"
    STATUS_PACKED = "packed"
    STATUS_SHIPPED = "shipped"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_AWAITING, _("Awaiting payment")),
        (STATUS_PAID, _("Paid")),
        (STATUS_PACKED, _("Being prepared")),
        (STATUS_SHIPPED, _("Shipped")),
        (STATUS_COMPLETED, _("Completed")),
        (STATUS_CANCELLED, _("Cancelled")),
    ]

    PAYMENT_PAYPAL = "paypal"
    PAYMENT_BANK = "bank"
    PAYMENT_CHOICES = [
        (PAYMENT_PAYPAL, "PayPal"),
        (PAYMENT_BANK, _("Bank transfer")),
    ]

    number = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    token = models.CharField(
        max_length=40, unique=True, default=new_token, editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    language = models.CharField(max_length=5, default="en", editable=False)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_AWAITING
    )
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_PAYPAL
    )

    name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)

    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=2, choices=country_choices, blank=True)

    customer_note = models.TextField(blank=True)

    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    invoice_number = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    discount_code = models.CharField(max_length=40, blank=True, editable=False)
    discount_amount = models.DecimalField(max_digits=9, decimal_places=2, default=0, editable=False)
    shipping_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    has_physical = models.BooleanField(default=False, editable=False)
    has_digital = models.BooleanField(default=False, editable=False)

    carrier = models.CharField(max_length=60, blank=True, help_text="e.g. DHL, Deutsche Post")
    tracking_number = models.CharField(max_length=80, blank=True)
    tracking_url = models.URLField(blank=True)
    internal_note = models.TextField(
        blank=True, help_text="Only visible to you. Customers never see this."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True, editable=False)
    shipped_at = models.DateTimeField(null=True, blank=True, editable=False)

    DOWNLOAD_DAYS = 60
    MAX_DOWNLOADS = 10

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("number", read_only=True),
                FieldPanel("status"),
                FieldPanel("payment_method"),
                FieldPanel("created_at", read_only=True),
            ],
            heading="Order",
        ),
        MultiFieldPanel(
            [ReadOnlyHTMLPanel("items_summary")],
            heading="What was ordered",
        ),
        MultiFieldPanel(
            [ReadOnlyHTMLPanel("documents_links")],
            heading="Documents",
        ),
        MultiFieldPanel(
            [
                FieldPanel("subtotal", read_only=True),
                FieldPanel("shipping_cost", read_only=True),
                FieldPanel("total", read_only=True),
            ],
            heading="Amounts (€)",
        ),
        MultiFieldPanel(
            [
                FieldPanel("name", read_only=True),
                FieldPanel("email", read_only=True),
                FieldPanel("phone", read_only=True),
                ReadOnlyHTMLPanel("address_display", heading="Address"),
                FieldPanel("customer_note", read_only=True),
            ],
            heading="Customer",
        ),
        MultiFieldPanel(
            [
                FieldPanel("carrier"),
                FieldPanel("tracking_number"),
                FieldPanel("tracking_url"),
            ],
            heading="Shipping",
        ),
        FieldPanel("internal_note"),
    ]

    class Meta:
        ordering = ["-created_at"]

    _loaded_status = None  # the status as stored in the database

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if "status" in field_names:
            instance._loaded_status = instance.status
        return instance

    def __str__(self):
        return f"{self.number or 'New order'} — {self.name}"

    # --- display helpers -------------------------------------------------

    @property
    def status_label(self):
        return self.get_status_display()

    @property
    def customer_name(self):
        return self.name

    INVOICE_STATUSES = ("paid", "packed", "shipped", "completed")

    @property
    def can_have_invoice(self):
        return self.status in self.INVOICE_STATUSES

    def ensure_invoice_number(self):
        """Invoice numbers run R-2026-0001, R-2026-0002 ... without gaps (a German requirement)."""
        if self.invoice_number or not self.can_have_invoice:
            return self.invoice_number
        with transaction.atomic():
            year = (self.paid_at or timezone.now()).year
            prefix = f"R-{year}-"
            last = (
                Order.objects.select_for_update()
                .filter(invoice_number__startswith=prefix)
                .order_by("-invoice_number")
                .first()
            )
            seq = int(last.invoice_number.rsplit("-", 1)[1]) + 1 if last else 1
            self.invoice_number = f"{prefix}{seq:04d}"
            Order.objects.filter(pk=self.pk).update(invoice_number=self.invoice_number)
        return self.invoice_number

    @property
    def documents_links(self):
        if not self.pk:
            return ""
        return format_html(
            '<a class="button button-small" href="{}" target="_blank">Invoice (PDF)</a> '
            '<a class="button button-small button-secondary" href="{}" target="_blank">Packing slip (PDF)</a>',
            reverse("shop_admin_document", args=[self.pk, "invoice"]),
            reverse("shop_admin_document", args=[self.pk, "packing-slip"]),
        )

    @property
    def items_summary(self):
        rows = [
            (item.quantity, item.title, item.option_label, item.line_total)
            for item in self.items.all()
        ]
        return format_html(
            "<ul>{}</ul>",
            format_html_join(
                "",
                "<li>{}× <strong>{}</strong> — {} (€{})</li>",
                rows,
            ),
        )

    @property
    def address_display(self):
        parts = [
            self.address_line1,
            self.address_line2,
            f"{self.postal_code} {self.city}".strip(),
            self.get_country_display() if self.country else "",
        ]
        return format_html_join(
            "", "{}<br>", ((p,) for p in parts if p)
        ) or "—"

    @property
    def is_paid(self):
        return self.status in (
            self.STATUS_PAID,
            self.STATUS_PACKED,
            self.STATUS_SHIPPED,
            self.STATUS_COMPLETED,
        )

    @property
    def downloads_available(self):
        if not (self.has_digital and self.is_paid and self.paid_at):
            return False
        return timezone.now() <= self.paid_at + timedelta(days=self.DOWNLOAD_DAYS)

    @property
    def download_expires(self):
        return self.paid_at + timedelta(days=self.DOWNLOAD_DAYS) if self.paid_at else None

    def get_absolute_url(self):
        with translation.override(self.language):
            return reverse("shop:order", args=[self.token])

    # --- validation & state changes -------------------------------------

    def clean(self):
        super().clean()
        if (
            self._loaded_status == self.STATUS_CANCELLED
            and self.status != self.STATUS_CANCELLED
        ):
            raise ValidationError(
                {
                    "status": "A cancelled order can't be reopened (its stock was "
                    "already released). Ask the customer to place a new order."
                }
            )

    def save(self, *args, **kwargs):
        with transaction.atomic():
            creating = self._state.adding
            super().save(*args, **kwargs)
            if creating and not self.number:
                self.number = f"JL-{timezone.localdate().year}-{self.pk:04d}"
                super().save(update_fields=["number"])
            old = self._loaded_status
            if not creating and old and old != self.status:
                self._handle_status_change(old, self.status)
            self._loaded_status = self.status

    def _handle_status_change(self, old, new):
        from . import emails

        was_paid = old in (
            self.STATUS_PAID,
            self.STATUS_PACKED,
            self.STATUS_SHIPPED,
            self.STATUS_COMPLETED,
        )
        now_paid = new in (
            self.STATUS_PAID,
            self.STATUS_PACKED,
            self.STATUS_SHIPPED,
            self.STATUS_COMPLETED,
        )

        if now_paid and not was_paid:
            self._record_payment()
            emails.send_payment_received(self)
        elif was_paid and not now_paid and new != self.STATUS_CANCELLED:
            # Moved back to "awaiting payment" by mistake: undo the sale.
            self._undo_sale()

        if new == self.STATUS_CANCELLED:
            if was_paid:
                self._undo_sale()
            self._release_stock()
            self._release_discount()
            emails.send_cancelled(self)

        if new == self.STATUS_SHIPPED and not self.shipped_at:
            self.shipped_at = timezone.now()
            super().save(update_fields=["shipped_at"])
            emails.send_shipped(self)

        # A digital-only order is finished as soon as it is paid.
        if (
            new == self.STATUS_PAID
            and self.has_digital
            and not self.has_physical
        ):
            self.status = self.STATUS_COMPLETED
            super().save(update_fields=["status"])

    def _record_payment(self):
        self.paid_at = self.paid_at or timezone.now()
        super().save(update_fields=["paid_at"])
        for item in self.items.select_related("offer", "offer__artwork"):
            if item.offer_id:
                type(item.offer).objects.filter(pk=item.offer_id).update(
                    sold_count=models.F("sold_count") + item.quantity
                )
                if item.kind == "original":
                    item.offer.artwork.set_status("sold")

    def _undo_sale(self):
        self.paid_at = None
        super().save(update_fields=["paid_at"])
        for item in self.items.select_related("offer", "offer__artwork"):
            if item.offer_id:
                type(item.offer).objects.filter(
                    pk=item.offer_id, sold_count__gte=item.quantity
                ).update(sold_count=models.F("sold_count") - item.quantity)

    def _release_discount(self):
        """A cancelled order gives its discount code (or gift card balance) back."""
        if not self.discount_code:
            return
        code = DiscountCode.objects.filter(code=self.discount_code).first()
        if not code:
            return
        code.used_count = max(code.used_count - 1, 0)
        if code.kind == DiscountCode.GIFT:
            code.remaining = (code.remaining or 0) + self.discount_amount
        code.save()

    def _release_stock(self):
        for item in self.items.select_related("offer", "offer__artwork"):
            offer = item.offer
            if not offer:
                continue
            if item.kind == "original":
                if offer.artwork.status in ("reserved", "sold"):
                    offer.artwork.set_status("available")
            elif offer.stock is not None:
                type(offer).objects.filter(pk=offer.pk).update(
                    stock=models.F("stock") + item.quantity
                )
                offer.artwork.notify_waitlist()


SIZE_PRESETS = [
    ("A6", 10.5, 14.8),
    ("A5", 14.8, 21.0),
    ("A4", 21.0, 29.7),
    ("A3", 29.7, 42.0),
    ("30 × 40 cm", 30, 40),
    ("A2", 42.0, 59.4),
    ("50 × 70 cm", 50, 70),
]


def size_estimates(settings_obj):
    """Sizes with a rough commission price, for the visual size picker."""
    if not settings_obj:
        return []
    base, rate = settings_obj.commission_base_price, settings_obj.commission_price_per_100cm2
    if not base and not rate:
        return []
    out = []
    for label, width, height in SIZE_PRESETS:
        price = float(base) + width * height / 100 * float(rate)
        out.append(
            {
                "label": label,
                "width": width,
                "height": height,
                "price": int(round(price / 5.0) * 5),  # round to a friendly 5 €
                "text": f"{label} ({width:g} × {height:g} cm)" if "cm" not in label else label,
            }
        )
    return out


class DiscountCode(models.Model):
    """A code customers type in the cart: a percentage, a fixed amount, free shipping or a gift card."""

    PERCENT = "percent"
    FIXED = "fixed"
    FREE_SHIPPING = "free_shipping"
    GIFT = "gift"
    KIND_CHOICES = [
        (PERCENT, "Percent off"),
        (FIXED, "Fixed amount off"),
        (FREE_SHIPPING, "Free shipping"),
        (GIFT, "Gift card (balance is used up over time)"),
    ]

    code = models.CharField(max_length=40, unique=True, help_text="What the customer types, e.g. SUMMER10. Capitals are added automatically.")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=PERCENT)
    value = models.DecimalField(
        max_digits=7, decimal_places=2, default=0,
        help_text="Percent (e.g. 10) or euros (e.g. 15). For a gift card: its value. Not needed for free shipping.",
    )
    remaining = models.DecimalField(
        "Gift card balance left", max_digits=7, decimal_places=2, null=True, blank=True, editable=False
    )
    min_order = models.DecimalField(
        "Minimum order (€)", max_digits=7, decimal_places=2, null=True, blank=True,
        help_text="Optional. The code only works from this order value.",
    )
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True, help_text="Optional. Last day the code works.")
    max_uses = models.PositiveIntegerField(
        null=True, blank=True, help_text="Optional. How many orders may use it. Empty = unlimited."
    )
    used_count = models.PositiveIntegerField(default=0, editable=False)
    active = models.BooleanField(default=True)
    note = models.CharField(max_length=200, blank=True, help_text="For you only, e.g. who the gift card is for.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        if self.kind == self.GIFT and self.remaining is None:
            self.remaining = self.value
        super().save(*args, **kwargs)

    @property
    def summary(self):
        if self.kind == self.PERCENT:
            return f"{self.value.normalize():f}% off"
        if self.kind == self.FIXED:
            return f"€{self.value} off"
        if self.kind == self.FREE_SHIPPING:
            return "Free shipping"
        return f"Gift card, €{self.remaining} left"

    @property
    def uses_label(self):
        return f"{self.used_count} / {self.max_uses}" if self.max_uses else str(self.used_count)

    def problem(self, subtotal, today=None):
        """Why this code cannot be used right now ('' when it can)."""
        from django.utils import timezone

        today = today or timezone.localdate()
        if not self.active:
            return _("This code is not valid.")
        if self.valid_from and today < self.valid_from:
            return _("This code is not valid yet.")
        if self.valid_until and today > self.valid_until:
            return _("This code has expired.")
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return _("This code has been used up.")
        if self.kind == self.GIFT and (self.remaining or 0) <= 0:
            return _("This gift card has been used up.")
        if self.min_order and subtotal < self.min_order:
            return _("This code needs an order of at least €%(amount)s.") % {"amount": self.min_order}
        return ""

    def amounts(self, subtotal):
        """(amount off the goods, whether shipping becomes free)."""
        from decimal import ROUND_HALF_UP, Decimal

        cent = Decimal("0.01")
        if self.kind == self.PERCENT:
            off = (subtotal * self.value / 100).quantize(cent, ROUND_HALF_UP)
        elif self.kind == self.FIXED:
            off = self.value
        elif self.kind == self.GIFT:
            off = self.remaining or Decimal("0")
        else:
            return Decimal("0.00"), True
        return min(off, subtotal).quantize(cent), False


class WaitlistRequest(models.Model):
    """Someone wants to be told when a sold-out print or a reserved original is available."""

    offer = models.ForeignKey("artworks.Offer", on_delete=models.CASCADE, related_name="waitlist")
    email = models.EmailField()
    language = models.CharField(max_length=5, default="en")
    created_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("offer", "email")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} for {self.offer}"

    @property
    def artwork_title(self):
        return self.offer.artwork.title

    @property
    def status_label(self):
        return "Told it is back" if self.notified_at else "Waiting"


class OrderItem(models.Model):
    """What was bought, with prices and names frozen at order time."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    offer = models.ForeignKey(
        "artworks.Offer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_items",
    )
    title = models.CharField(max_length=255)
    option_label = models.CharField(max_length=200, blank=True)
    kind = models.CharField(max_length=20)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    download_name = models.CharField(max_length=300, blank=True)
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity}× {self.title}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    @property
    def is_digital(self):
        return self.kind == "digital"

    @property
    def can_download(self):
        return (
            self.is_digital
            and bool(self.download_name)
            and self.order.downloads_available
            and self.download_count < Order.MAX_DOWNLOADS
        )
