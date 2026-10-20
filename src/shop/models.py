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
        FieldPanel("small_business_vat_exempt"),
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
