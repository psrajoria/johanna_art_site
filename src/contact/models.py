from django.conf import settings
from django.db import models, transaction
from django.urls import reverse
from django.utils import translation
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from wagtail.admin.panels import FieldPanel, MultiFieldPanel

from config.panels import ReadOnlyHTMLPanel
from config.storage import private_storage
from shop.models import new_token


class Inquiry(models.Model):
    """
    A message from the public contact form: a question about an artwork, a
    custom commission, a print in a custom size, or a general message.

    Commissions and print requests have a status that Johanna moves forward in
    the admin; the customer follows it on a private status page and gets an
    email at the important steps.
    """

    INQUIRY_ARTWORK = "artwork"
    INQUIRY_COMMISSION = "commission"
    INQUIRY_PRINT = "print"
    INQUIRY_GENERAL = "general"

    INQUIRY_TYPE_CHOICES = [
        (INQUIRY_COMMISSION, _("Commission a painting")),
        (INQUIRY_PRINT, _("Print in a custom size")),
        (INQUIRY_ARTWORK, _("Ask about an artwork")),
        (INQUIRY_GENERAL, _("General message")),
    ]

    STATUS_NEW = "new"
    STATUS_REPLIED = "replied"
    STATUS_QUOTED = "quoted"
    STATUS_ACCEPTED = "accepted"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_FINISHED = "finished"
    STATUS_SHIPPED = "shipped"
    STATUS_DECLINED = "declined"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = [
        (STATUS_NEW, _("New")),
        (STATUS_REPLIED, _("Replied")),
        (STATUS_QUOTED, _("Quote sent")),
        (STATUS_ACCEPTED, _("Accepted")),
        (STATUS_IN_PROGRESS, _("In progress")),
        (STATUS_FINISHED, _("Finished")),
        (STATUS_SHIPPED, _("Shipped")),
        (STATUS_DECLINED, _("Declined")),
        (STATUS_CLOSED, _("Closed")),
    ]

    # Statuses that email the customer when Johanna sets them.
    NOTIFY_ON = {
        STATUS_QUOTED,
        STATUS_IN_PROGRESS,
        STATUS_FINISHED,
        STATUS_SHIPPED,
        STATUS_DECLINED,
    }

    # Order of the public progress timeline.
    TIMELINE = [
        STATUS_NEW,
        STATUS_QUOTED,
        STATUS_ACCEPTED,
        STATUS_IN_PROGRESS,
        STATUS_FINISHED,
        STATUS_SHIPPED,
    ]

    number = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    token = models.CharField(
        max_length=40, unique=True, default=new_token, editable=False
    )
    language = models.CharField(max_length=5, default="en", editable=False)

    inquiry_type = models.CharField(
        max_length=30,
        choices=INQUIRY_TYPE_CHOICES,
        default=INQUIRY_GENERAL,
    )

    artwork = models.ForeignKey(
        "artworks.ArtworkPage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inquiries",
        help_text="Filled when someone asks about a specific artwork.",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inquiries",
    )

    name = models.CharField(max_length=160)
    email = models.EmailField()

    message = models.TextField(help_text="The visitor's message.")

    size_wanted = models.CharField(
        max_length=80,
        blank=True,
        help_text="Size the visitor asked for, e.g. A3 or 40 × 50 cm.",
    )
    budget = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional budget, useful for commissions.",
    )
    deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Optional deadline for commission requests.",
    )
    reference_link = models.URLField(
        blank=True,
        help_text="Optional link to a reference photo, Instagram post, cloud folder, etc.",
    )
    reference_image = models.FileField(
        storage=private_storage,
        upload_to="references/%Y/%m/",
        blank=True,
        help_text="Reference photo uploaded by the visitor.",
    )

    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default=STATUS_NEW
    )
    quote_amount = models.DecimalField(
        "Quote (€)",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "The price you quote. It is shown to the customer in the "
            "'Quote sent' email together with the payment details."
        ),
    )
    quote_message = models.TextField(
        blank=True,
        help_text="Optional personal note included in the customer's email.",
    )
    payment_received = models.BooleanField(
        default=False, help_text="Tick when the customer has paid (for your records)."
    )
    carrier = models.CharField(max_length=60, blank=True)
    tracking_number = models.CharField(max_length=80, blank=True)
    internal_notes = models.TextField(
        blank=True, help_text="Only visible to you. Customers never see this."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("number", read_only=True),
                FieldPanel("status"),
                FieldPanel("inquiry_type"),
                FieldPanel("artwork"),
                FieldPanel("created_at", read_only=True),
            ],
            heading="Request",
        ),
        MultiFieldPanel(
            [
                FieldPanel("name", read_only=True),
                FieldPanel("email", read_only=True),
                FieldPanel("message", read_only=True),
            ],
            heading="Message",
        ),
        MultiFieldPanel(
            [
                FieldPanel("size_wanted", read_only=True),
                FieldPanel("budget", read_only=True),
                FieldPanel("deadline", read_only=True),
                FieldPanel("reference_link", read_only=True),
                ReadOnlyHTMLPanel("reference_image_link", heading="Reference photo"),
            ],
            heading="Commission details",
        ),
        MultiFieldPanel(
            [
                FieldPanel("quote_amount"),
                FieldPanel("quote_message"),
                FieldPanel("payment_received"),
                FieldPanel("carrier"),
                FieldPanel("tracking_number"),
            ],
            heading="Quote, payment & delivery",
        ),
        FieldPanel("internal_notes"),
    ]

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Inquiry"
        verbose_name_plural = "Inquiries"

    _loaded_status = None  # the status as stored in the database

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if "status" in field_names:
            instance._loaded_status = instance.status
        return instance

    def __str__(self):
        return f"{self.number or 'New'} — {self.name} — {self.get_inquiry_type_display()}"

    # --- display helpers -------------------------------------------------

    @property
    def status_label(self):
        return self.get_status_display()

    @property
    def type_label(self):
        return self.get_inquiry_type_display()

    @property
    def is_request(self):
        """Commissions and custom prints follow the quote workflow."""
        return self.inquiry_type in (self.INQUIRY_COMMISSION, self.INQUIRY_PRINT)

    @property
    def reference_image_link(self):
        if not self.pk or not self.reference_image:
            return "—"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Open uploaded photo</a>',
            reverse("contact:reference", args=[self.pk]),
        )

    def get_status_url(self):
        with translation.override(self.language):
            return reverse("contact:request_status", args=[self.token])

    # --- state changes ---------------------------------------------------

    def save(self, *args, **kwargs):
        with transaction.atomic():
            creating = self._state.adding
            super().save(*args, **kwargs)
            if creating and not self.number:
                prefix = "JL-C" if self.is_request else "JL-M"
                self.number = f"{prefix}-{self.pk:04d}"
                super().save(update_fields=["number"])
            old = self._loaded_status
            if (
                not creating
                and old
                and old != self.status
                and self.is_request
                and self.status in self.NOTIFY_ON
            ):
                from . import emails

                new_status = self.status
                transaction.on_commit(lambda: emails.send_status_update(self, new_status))
            self._loaded_status = self.status
