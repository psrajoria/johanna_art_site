from django.db import models

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class HomePage(Page):
    """
    Homepage for Johanna's art portfolio.
    Shows editable intro text and real featured artworks.
    """

    hero_eyebrow = models.CharField(
        max_length=120,
        blank=True,
        default="Watercolour painting & sketching",
    )

    hero_title = models.CharField(
        max_length=160,
        blank=True,
        default="Places, memories, and imperfect",
    )

    hero_highlight = models.CharField(
        max_length=80,
        blank=True,
        default="layers.",
    )

    hero_text = RichTextField(
        blank=True,
        default=(
            "Travel-inspired watercolour sketches by Johanna L — quiet streets, "
            "soft landscapes, architecture, and small moments captured through "
            "pencil, colour, and practice."
        ),
    )

    featured_title = models.CharField(
        max_length=160,
        blank=True,
        default="A sketchbook of places.",
    )

    featured_text = RichTextField(
        blank=True,
        default=(
            "A growing collection of travel sketches, architecture, landscapes, "
            "and process studies — each artwork with its own place, memory, and story."
        ),
    )

    process_title = models.CharField(
        max_length=160,
        blank=True,
        default="Soft layers, slow looking.",
    )

    process_text = RichTextField(
        blank=True,
        default=(
            "Watercolour is built in layers: light washes, pencil marks, "
            "small corrections, and the decision to keep going even when a piece "
            "is not perfect."
        ),
    )

    commission_title = models.CharField(
        max_length=160,
        blank=True,
        default="Turn a place into a watercolour memory.",
    )

    commission_text = RichTextField(
        blank=True,
        default=(
            "Request a custom painting from a travel photo, favourite street, "
            "house, facade, landscape, or meaningful place."
        ),
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("hero_eyebrow"),
                FieldPanel("hero_title"),
                FieldPanel("hero_highlight"),
                FieldPanel("hero_text"),
            ],
            heading="Hero section",
        ),
        MultiFieldPanel(
            [
                FieldPanel("featured_title"),
                FieldPanel("featured_text"),
            ],
            heading="Featured artworks section",
        ),
        MultiFieldPanel(
            [
                FieldPanel("process_title"),
                FieldPanel("process_text"),
            ],
            heading="Process section",
        ),
        MultiFieldPanel(
            [
                FieldPanel("commission_title"),
                FieldPanel("commission_text"),
            ],
            heading="Commission section",
        ),
    ]

    def get_context(self, request):
        context = super().get_context(request)

        # Import here to avoid circular imports during Django startup.
        from artworks.models import ArtworkPage

        featured_artworks = list(
            ArtworkPage.objects.live()
            .public()
            .filter(featured=True)
            .order_by("-first_published_at")[:3]
        )

        latest_artworks = list(
            ArtworkPage.objects.live().public().order_by("-first_published_at")[:6]
        )

        hero_artwork = None
        if featured_artworks:
            hero_artwork = featured_artworks[0]
        elif latest_artworks:
            hero_artwork = latest_artworks[0]

        context["featured_artworks"] = featured_artworks
        context["latest_artworks"] = latest_artworks
        context["hero_artwork"] = hero_artwork

        return context
