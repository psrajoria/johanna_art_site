import secrets

from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField


def _token():
    return secrets.token_urlsafe(24)


class Subscriber(models.Model):
    """Someone who asked for the newsletter. Counts only after they confirm by email."""

    email = models.EmailField(unique=True)
    language = models.CharField(max_length=5, default="en")
    token = models.CharField(max_length=40, unique=True, default=_token, editable=False)
    confirmed = models.BooleanField(default=False)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-subscribed_at"]

    def __str__(self):
        return self.email

    @property
    def is_active(self):
        return self.confirmed and self.unsubscribed_at is None

    @property
    def status_label(self):
        if self.unsubscribed_at:
            return "Unsubscribed"
        return "Subscribed" if self.confirmed else "Waiting for confirmation"

    def confirm(self):
        self.confirmed = True
        self.confirmed_at = timezone.now()
        self.unsubscribed_at = None
        self.save()

    def unsubscribe(self):
        self.unsubscribed_at = timezone.now()
        self.save()

    def confirm_path(self):
        return reverse("newsletter:confirm", args=[self.token])

    def unsubscribe_path(self):
        return reverse("newsletter:unsubscribe", args=[self.token])


class Campaign(models.Model):
    """One newsletter. Write it, send yourself a test, then tick 'send' and save."""

    subject = models.CharField(max_length=140)
    subject_de = models.CharField("Subject (German)", max_length=140, blank=True)
    intro = RichTextField(
        features=["bold", "italic", "link"],
        help_text="A few warm words, as if you were writing to a friend.",
    )
    intro_de = RichTextField(
        "Text (German)", features=["bold", "italic", "link"], blank=True,
        help_text="Subscribers who joined on the German site get this version. Leave empty to send the English text.",
    )
    artwork = models.ForeignKey(
        "artworks.ArtworkPage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional: show one artwork with a big picture and a button.",
    )

    send_test_to = models.EmailField(
        "Send a test to",
        blank=True,
        help_text="Type your own email and save: you get a preview. (The box empties afterwards.)",
    )
    send_now = models.BooleanField(
        "Send to all subscribers now",
        default=False,
        help_text="Tick and save to send. This cannot be undone, so send yourself a test first.",
    )
    sent_at = models.DateTimeField(null=True, blank=True, editable=False)
    sent_count = models.PositiveIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    panels = [
        MultiFieldPanel(
            [FieldPanel("subject"), FieldPanel("intro"), FieldPanel("artwork")],
            heading="Newsletter",
        ),
        MultiFieldPanel(
            [FieldPanel("subject_de"), FieldPanel("intro_de")],
            heading="German version (optional)",
        ),
        MultiFieldPanel(
            [FieldPanel("send_test_to"), FieldPanel("send_now")],
            heading="Test and send",
        ),
    ]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.subject

    @property
    def status_label(self):
        return f"Sent to {self.sent_count}" if self.sent_at else "Draft"

    def save_sent_count(self):
        Campaign.objects.filter(pk=self.pk).update(sent_count=self.sent_count)

    def save(self, *args, **kwargs):
        test_to = self.send_test_to
        send_now = self.send_now and not self.sent_at
        self.send_test_to = ""
        self.send_now = False
        super().save(*args, **kwargs)

        from . import emails

        if test_to:
            transaction.on_commit(lambda: emails.send_test(self, test_to))
        if send_now:
            self.sent_at = timezone.now()
            self.sent_count = 0
            super().save(update_fields=["sent_at", "sent_count"])
            transaction.on_commit(lambda: emails.send_campaign(self))
