from django.db import models

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.snippets.models import register_snippet


@register_snippet
class Inquiry(models.Model):
    """
    Inquiry saved from the public contact / commission form.
    Johanna can view these in Wagtail admin under Snippets.
    """

    INQUIRY_ARTWORK = "artwork"
    INQUIRY_COMMISSION = "commission"
    INQUIRY_GENERAL = "general"

    INQUIRY_TYPE_CHOICES = [
        (INQUIRY_ARTWORK, "Ask about an artwork"),
        (INQUIRY_COMMISSION, "Commission request"),
        (INQUIRY_GENERAL, "General message"),
    ]

    STATUS_NEW = "new"
    STATUS_REPLIED = "replied"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_REPLIED, "Replied"),
        (STATUS_CLOSED, "Closed"),
    ]

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
        help_text="Optional. Filled when someone asks about a specific artwork.",
    )

    name = models.CharField(max_length=160)
    email = models.EmailField()

    message = models.TextField(
        help_text="The visitor's message.",
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

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("status"),
                FieldPanel("inquiry_type"),
                FieldPanel("artwork"),
            ],
            heading="Inquiry status",
        ),
        MultiFieldPanel(
            [
                FieldPanel("name"),
                FieldPanel("email"),
                FieldPanel("message"),
            ],
            heading="Message",
        ),
        MultiFieldPanel(
            [
                FieldPanel("budget"),
                FieldPanel("deadline"),
                FieldPanel("reference_link"),
            ],
            heading="Commission details",
        ),
    ]

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Inquiry"
        verbose_name_plural = "Inquiries"

    def __str__(self):
        return f"{self.name} — {self.get_inquiry_type_display()}"
