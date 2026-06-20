from django.db import models
from modelcluster.fields import ParentalKey

from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page


class ArtworkIndexPage(Page):
    """
    Gallery landing page.
    Editors create this once, then add ArtworkPage children under it.
    """

    intro = RichTextField(
        blank=True,
        help_text="Short introduction shown at the top of the gallery page.",
    )

    max_count = 1
    parent_page_types = ["home.HomePage"]
    subpage_types = ["artworks.ArtworkPage"]

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    def get_context(self, request):
        context = super().get_context(request)

        artworks = (
            ArtworkPage.objects.live()
            .public()
            .descendant_of(self)
            .order_by("-first_published_at")
        )

        selected_category = request.GET.get("category")
        selected_status = request.GET.get("status")

        valid_categories = dict(ArtworkPage.CATEGORY_CHOICES)
        valid_statuses = dict(ArtworkPage.STATUS_CHOICES)

        if selected_category in valid_categories:
            artworks = artworks.filter(category=selected_category)

        if selected_status in valid_statuses:
            artworks = artworks.filter(status=selected_status)

        context["artworks"] = artworks
        context["category_choices"] = ArtworkPage.CATEGORY_CHOICES
        context["status_choices"] = ArtworkPage.STATUS_CHOICES
        context["selected_category"] = selected_category
        context["selected_status"] = selected_status

        return context


class ArtworkPage(Page):
    """
    One artwork / painting / sketch page.
    """

    CATEGORY_TRAVEL = "travel"
    CATEGORY_ARCHITECTURE = "architecture"
    CATEGORY_LANDSCAPE = "landscape"
    CATEGORY_SKETCHBOOK = "sketchbook"
    CATEGORY_COMMISSION = "commission"

    CATEGORY_CHOICES = [
        (CATEGORY_TRAVEL, "Travel Sketches"),
        (CATEGORY_ARCHITECTURE, "Architecture & Facades"),
        (CATEGORY_LANDSCAPE, "Landscapes"),
        (CATEGORY_SKETCHBOOK, "Sketchbook Studies"),
        (CATEGORY_COMMISSION, "Commission Examples"),
    ]

    STATUS_AVAILABLE = "available"
    STATUS_RESERVED = "reserved"
    STATUS_SOLD = "sold"
    STATUS_NOT_FOR_SALE = "not_for_sale"

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_SOLD, "Sold"),
        (STATUS_NOT_FOR_SALE, "Not for sale"),
    ]

    main_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Main image shown in the gallery and artwork detail page.",
    )

    short_description = models.CharField(
        max_length=240,
        blank=True,
        help_text="One short sentence for gallery cards.",
    )

    story = RichTextField(
        blank=True,
        help_text="The memory, place, process, or story behind this artwork.",
    )

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_TRAVEL,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_AVAILABLE,
    )

    place = models.CharField(
        max_length=120,
        blank=True,
        help_text="City/place/location, e.g. Kraków, Prague, Pollença.",
    )

    country = models.CharField(
        max_length=80,
        blank=True,
        help_text="Optional country, e.g. Poland, Czech Republic, Spain.",
    )

    medium = models.CharField(
        max_length=120,
        blank=True,
        default="Watercolour and pencil",
    )

    width_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
    )

    height_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
    )

    year = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional. Leave empty if price should not be shown.",
    )

    currency = models.CharField(
        max_length=8,
        default="€",
    )

    show_price = models.BooleanField(
        default=False,
        help_text="Turn on only if the price should be visible publicly.",
    )

    featured = models.BooleanField(
        default=False,
        help_text="Use later for homepage featured artworks.",
    )

    parent_page_types = ["artworks.ArtworkIndexPage"]
    subpage_types = []

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("main_image"),
                FieldPanel("short_description"),
                FieldPanel("story"),
            ],
            heading="Artwork story",
        ),
        MultiFieldPanel(
            [
                FieldPanel("category"),
                FieldPanel("status"),
                FieldPanel("featured"),
            ],
            heading="Gallery settings",
        ),
        MultiFieldPanel(
            [
                FieldPanel("place"),
                FieldPanel("country"),
                FieldPanel("medium"),
                FieldPanel("width_cm"),
                FieldPanel("height_cm"),
                FieldPanel("year"),
            ],
            heading="Artwork details",
        ),
        MultiFieldPanel(
            [
                FieldPanel("show_price"),
                FieldPanel("price"),
                FieldPanel("currency"),
            ],
            heading="Price",
        ),
        InlinePanel("gallery_images", label="Extra images / process images"),
    ]

    @property
    def size_display(self):
        if self.width_cm and self.height_cm:
            return f"{self.width_cm:g} × {self.height_cm:g} cm"
        return ""

    @property
    def price_display(self):
        if self.show_price and self.price:
            return f"{self.currency}{self.price:g}"
        return ""

    @property
    def location_display(self):
        parts = [part for part in [self.place, self.country] if part]
        return ", ".join(parts)


class ArtworkPageGalleryImage(Orderable):
    """
    Extra image rows attached to an ArtworkPage.
    Useful for details, process, sketchbook photos, or close-ups.
    """

    page = ParentalKey(
        ArtworkPage,
        on_delete=models.CASCADE,
        related_name="gallery_images",
    )

    image = models.ForeignKey(
        "wagtailimages.Image",
        on_delete=models.CASCADE,
        related_name="+",
    )

    caption = models.CharField(
        max_length=240,
        blank=True,
    )

    panels = [
        FieldPanel("image"),
        FieldPanel("caption"),
    ]
