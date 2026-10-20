from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models
from django.utils import translation
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey

from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Locale, Orderable, Page

from config.storage import private_storage


class ArtworkIndexPage(Page):
    """
    Gallery landing page.
    Editors create this once, then add ArtworkPage children under it.
    """

    intro = RichTextField(
        blank=True,
        help_text="Short introduction shown at the top of the gallery page.",
    )

    max_count_per_parent = 1
    parent_page_types = ["home.HomePage"]
    subpage_types = ["artworks.ArtworkPage"]

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    PAGE_SIZE = 12

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
        selected_buy = request.GET.get("buy")

        valid_categories = dict(ArtworkPage.CATEGORY_CHOICES)
        valid_statuses = dict(ArtworkPage.STATUS_CHOICES)
        valid_buy = dict(Offer.KIND_CHOICES)

        if selected_category not in valid_categories:
            selected_category = None
        if selected_status not in valid_statuses:
            selected_status = None
        if selected_buy not in valid_buy:
            selected_buy = None

        if selected_category:
            artworks = artworks.filter(category=selected_category)

        if selected_status:
            artworks = artworks.filter(status=selected_status)

        if selected_buy:
            # Offers are managed on the default-language page; match
            # translations through their shared translation key.
            keys = Offer.objects.filter(
                kind=selected_buy,
                is_active=True,
                artwork__locale=Locale.get_default(),
            ).values("artwork__translation_key")
            artworks = artworks.filter(translation_key__in=keys)

        paginator = Paginator(artworks, self.PAGE_SIZE)
        try:
            page_obj = paginator.page(request.GET.get("page", 1))
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        query = request.GET.copy()
        query.pop("page", None)

        context["artworks"] = page_obj
        context["total_count"] = paginator.count
        context["category_choices"] = ArtworkPage.CATEGORY_CHOICES
        context["status_choices"] = ArtworkPage.STATUS_CHOICES
        context["buy_choices"] = Offer.KIND_CHOICES
        context["selected_category"] = selected_category
        context["selected_status"] = selected_status
        context["selected_buy"] = selected_buy
        context["query_string"] = query.urlencode()

        return context


class ArtworkPage(Page):
    """
    One artwork / painting / sketch page.

    What can be bought (original, prints, digital download) is described by
    the `offers` below. The same artwork page exists once per language; offers
    and the sold/available status are always read from the default-language
    page so stock can never disagree between English and German.
    """

    CATEGORY_TRAVEL = "travel"
    CATEGORY_ARCHITECTURE = "architecture"
    CATEGORY_LANDSCAPE = "landscape"
    CATEGORY_SKETCHBOOK = "sketchbook"
    CATEGORY_COMMISSION = "commission"

    CATEGORY_CHOICES = [
        (CATEGORY_TRAVEL, _("Travel Sketches")),
        (CATEGORY_ARCHITECTURE, _("Architecture & Facades")),
        (CATEGORY_LANDSCAPE, _("Landscapes")),
        (CATEGORY_SKETCHBOOK, _("Sketchbook Studies")),
        (CATEGORY_COMMISSION, _("Commission Examples")),
    ]

    STATUS_AVAILABLE = "available"
    STATUS_RESERVED = "reserved"
    STATUS_SOLD = "sold"
    STATUS_NOT_FOR_SALE = "not_for_sale"

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, _("Available")),
        (STATUS_RESERVED, _("Reserved")),
        (STATUS_SOLD, _("Sold")),
        (STATUS_NOT_FOR_SALE, _("Not for sale")),
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

    sketch_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional: a photo of the pencil sketch or first wash, taken from the same "
        "angle. Visitors can drag a slider from the sketch to the finished painting.",
    )

    price_visible = models.BooleanField(
        "show price and allow buying",
        default=True,
        help_text="Untick to keep the price private: visitors then see 'Price on request' "
        "and can message you instead. Buying is switched off while this is unticked. "
        "(Set this on the English page; the German page follows it.)",
    )

    palette = models.CharField(
        max_length=80,
        blank=True,
        editable=False,
        help_text="Main colours of the painting, found automatically.",
    )
    palette_source_id = models.PositiveIntegerField(null=True, editable=False)

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
        help_text=(
            "Status of the ORIGINAL painting. It changes automatically when "
            "someone orders it; change it by hand for sales made elsewhere. "
            "(Shared by the English and German versions.)"
        ),
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

    featured = models.BooleanField(
        default=False,
        help_text="Show this artwork in the featured section on the homepage.",
    )

    parent_page_types = ["artworks.ArtworkIndexPage"]
    subpage_types = []

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("main_image"),
                FieldPanel("sketch_image"),
                FieldPanel("short_description"),
                FieldPanel("story"),
            ],
            heading="Artwork story",
        ),
        MultiFieldPanel(
            [
                FieldPanel("category"),
                FieldPanel("status"),
                FieldPanel("price_visible"),
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
        InlinePanel(
            "offers",
            label="Ways to buy",
            help_text=(
                "Original, prints and digital downloads. Prices, stock and files "
                "are managed on the ENGLISH page only; the German page shows "
                "them automatically."
            ),
        ),
        InlinePanel("gallery_images", label="Extra images / process images"),
    ]

    # --- shared (language independent) data -------------------------------

    @cached_property
    def commerce_page(self):
        """The default-language version of this artwork (may be self)."""
        default = Locale.get_default()
        if self.locale_id == default.pk:
            return self
        return (
            ArtworkPage.objects.filter(
                translation_key=self.translation_key, locale=default
            ).first()
            or self
        )

    @property
    def prices_shown(self):
        return self.commerce_page.price_visible

    @property
    def palette_list(self):
        return [c for c in self.palette.split(",") if c]

    def _refresh_palette(self):
        """Pick the painting's main colours (used for swatches and image placeholders)."""
        if not self.main_image_id or self.palette_source_id == self.main_image_id:
            return
        try:
            from PIL import Image as PILImage

            with self.main_image.file.open("rb") as fh:
                img = PILImage.open(fh)
                img.thumbnail((96, 96))
                img = img.convert("RGB").quantize(colors=6, method=PILImage.Quantize.MEDIANCUT)
                pal = img.getpalette()[: 6 * 3]
                counts = sorted(img.getcolors(), reverse=True)
            colours = []
            for _count, idx in counts:
                r, g, b = pal[idx * 3 : idx * 3 + 3]
                # skip near-white paper and near-black so swatches show the paint
                if min(r, g, b) > 238 or max(r, g, b) < 24:
                    continue
                colours.append("#%02x%02x%02x" % (r, g, b))
            self.palette = ",".join(colours[:5])
            self.palette_source_id = self.main_image_id
        except Exception:
            # a missing or unreadable file must never block saving the page
            self.palette = ""

    def save(self, *args, **kwargs):
        self._refresh_palette()
        # Keep the original's status identical across languages, even when a
        # German page is published from an older revision.
        if self.pk and self.locale_id != Locale.get_default().pk:
            source = (
                ArtworkPage.objects.filter(
                    translation_key=self.translation_key,
                    locale=Locale.get_default(),
                )
                .values_list("status", flat=True)
                .first()
            )
            if source:
                self.status = source
        super().save(*args, **kwargs)
        if self.locale_id == Locale.get_default().pk:
            ArtworkPage.objects.filter(translation_key=self.translation_key).exclude(
                pk=self.pk
            ).update(status=self.status)

    def set_status(self, status):
        """Change the original's status for every language version."""
        ArtworkPage.objects.filter(translation_key=self.translation_key).update(
            status=status
        )
        self.status = status

    @cached_property
    def active_offers(self):
        return list(self.commerce_page.offers.filter(is_active=True))

    @cached_property
    def purchasable_offers(self):
        if not self.prices_shown:
            return []
        return [o for o in self.active_offers if o.is_purchasable(self.status)]

    @property
    def original_offer(self):
        return next((o for o in self.active_offers if o.kind == Offer.KIND_ORIGINAL), None)

    @property
    def from_price(self):
        prices = [o.price for o in self.purchasable_offers]
        return min(prices) if prices else None

    @property
    def badges(self):
        """Short labels for cards: [(css modifier, text), ...]."""
        badges = []
        original = self.original_offer
        if original:
            if self.status == self.STATUS_AVAILABLE:
                badges.append(("available", _("Original available")))
            elif self.status == self.STATUS_RESERVED:
                badges.append(("reserved", _("Original reserved")))
            elif self.status == self.STATUS_SOLD:
                badges.append(("sold", _("Original sold")))
            else:
                badges.append(("not_for_sale", _("Not for sale")))
        elif not self.active_offers:
            badges.append(
                ("not_for_sale", _("Not for sale"))
                if self.status == self.STATUS_NOT_FOR_SALE
                else (self.status, self.get_status_display())
            )

        if self.active_offers and not self.prices_shown:
            badges.append(("extra", _("Price on request")))

        for kind, text in (
            (Offer.KIND_PRINT, _("Prints")),
            (Offer.KIND_DIGITAL, _("Digital")),
        ):
            if any(
                o.kind == kind and o.is_purchasable(self.status)
                for o in self.active_offers
            ):
                badges.append(("extra", text))
        return badges

    @property
    def size_display(self):
        if self.width_cm and self.height_cm:
            return f"{self.width_cm.normalize():f} × {self.height_cm.normalize():f} cm"
        return ""

    @property
    def location_display(self):
        parts = [part for part in [self.place, self.country] if part]
        return ", ".join(parts)

    def get_context(self, request):
        context = super().get_context(request)
        context["offers"] = self.active_offers
        context["related_artworks"] = list(
            ArtworkPage.objects.live()
            .public()
            .filter(locale=self.locale, category=self.category)
            .exclude(pk=self.pk)
            .order_by("-first_published_at")[:3]
        )
        return context


class Offer(Orderable):
    """
    Something a visitor can buy from an artwork: the original painting,
    a print (one row per size/paper), or a digital download.
    """

    KIND_ORIGINAL = "original"
    KIND_PRINT = "print"
    KIND_DIGITAL = "digital"

    KIND_CHOICES = [
        (KIND_ORIGINAL, _("Original painting")),
        (KIND_PRINT, _("Print")),
        (KIND_DIGITAL, _("Digital download")),
    ]

    SHIPPING_NONE = "none"
    SHIPPING_FLAT = "flat"
    SHIPPING_PARCEL = "parcel"

    SHIPPING_CHOICES = [
        (SHIPPING_NONE, _("No shipping (digital)")),
        (SHIPPING_FLAT, _("Flat / tube (prints, cards)")),
        (SHIPPING_PARCEL, _("Parcel (originals, framed, large)")),
    ]

    artwork = ParentalKey(
        ArtworkPage,
        on_delete=models.CASCADE,
        related_name="offers",
    )

    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_PRINT)

    label = models.CharField(
        max_length=160,
        blank=True,
        help_text="e.g. 'A4 · 250g cotton paper'. Empty for the original and downloads.",
    )
    label_de = models.CharField(
        "Label (German)",
        max_length=160,
        blank=True,
        help_text="German version of the label above.",
    )

    price = models.DecimalField(max_digits=8, decimal_places=2)

    stock = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "How many are available. Leave EMPTY for unlimited — use this for "
            "digital downloads and prints made on demand. Not used for the "
            "original (its availability is the artwork's status)."
        ),
    )

    sold_count = models.PositiveIntegerField(
        default=0,
        editable=False,
        help_text="How many have been sold (counted when an order is paid).",
    )

    shipping_class = models.CharField(
        max_length=20,
        choices=SHIPPING_CHOICES,
        default=SHIPPING_FLAT,
        help_text="Decides the shipping price. Digital downloads must use 'No shipping'.",
    )

    download_file = models.FileField(
        storage=private_storage,
        upload_to="digital/",
        blank=True,
        help_text=(
            "Digital downloads only: the high-resolution file customers receive "
            "after payment (JPG, PNG, PDF or ZIP). It is stored privately."
        ),
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Untick to hide this option without deleting it.",
    )

    panels = [
        FieldPanel("kind"),
        FieldPanel("label"),
        FieldPanel("label_de"),
        FieldPanel("price"),
        FieldPanel("stock"),
        FieldPanel("shipping_class"),
        FieldPanel("download_file"),
        FieldPanel("is_active"),
    ]

    class Meta(Orderable.Meta):
        verbose_name = "way to buy"
        verbose_name_plural = "ways to buy"

    def __str__(self):
        return f"{self.artwork.title} — {self.display_label()}"

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        if self.kind == self.KIND_DIGITAL:
            self.shipping_class = self.SHIPPING_NONE
        elif self.shipping_class == self.SHIPPING_NONE:
            raise ValidationError(
                {"shipping_class": "Physical items need a shipping type."}
            )
        if self.kind == self.KIND_ORIGINAL:
            self.stock = None

    @property
    def is_physical(self):
        return self.kind != self.KIND_DIGITAL

    def display_label(self):
        """Human label in the active language."""
        base = self.get_kind_display()
        label = self.label
        if translation.get_language() == "de" and self.label_de:
            label = self.label_de
        return f"{base} · {label}" if label else base

    def short_label(self):
        label = self.label
        if translation.get_language() == "de" and self.label_de:
            label = self.label_de
        return label or self.get_kind_display()

    def is_purchasable(self, artwork_status):
        if not self.is_active or not self.artwork.price_visible:
            return False
        if self.kind == self.KIND_ORIGINAL:
            return artwork_status == ArtworkPage.STATUS_AVAILABLE
        if self.kind == self.KIND_DIGITAL and not self.download_file:
            return False
        return self.stock is None or self.stock > 0

    @property
    def purchasable(self):
        return self.is_purchasable(self.artwork.status)

    @property
    def stock_note(self):
        """Counter text shown next to an offer."""
        if self.kind == self.KIND_ORIGINAL or self.stock is None:
            return ""
        if self.stock == 0:
            return _("Sold out")
        if self.stock <= 3:
            return _("Only %(n)d left") % {"n": self.stock}
        return ""


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
