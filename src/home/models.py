from django.db import models

from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Orderable, Page

from .blocks import page_blocks


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
            "Travel-inspired watercolour sketches by Johanna Lackner — quiet streets, "
            "soft landscapes, architecture, and small moments captured through "
            "pencil, colour, and practice."
        ),
    )

    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=(
            "Optional. Leave empty to show your first featured artwork "
            "(or the newest one)."
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

    process_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional photo of Johanna at work, her desk or her sketchbook.",
    )

    shop_title = models.CharField(
        max_length=160,
        blank=True,
        default="Take a piece home.",
    )

    shop_text = RichTextField(
        blank=True,
        default=(
            "Original paintings, fine-art prints in several sizes, and digital "
            "downloads you can print yourself."
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
                FieldPanel("hero_image"),
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
                FieldPanel("process_image"),
            ],
            heading="Process section",
        ),
        MultiFieldPanel(
            [
                FieldPanel("shop_title"),
                FieldPanel("shop_text"),
            ],
            heading="Shop section",
        ),
        MultiFieldPanel(
            [
                FieldPanel("commission_title"),
                FieldPanel("commission_text"),
            ],
            heading="Commission section",
        ),
        MultiFieldPanel(
            [
                InlinePanel("instagram_posts", label="Instagram post", max_num=9),
            ],
            heading="Instagram strip: pick your favourite posts",
            help_text=(
                "Add a photo from a post and paste the link of that post. "
                "If Instagram is connected in Settings, Site settings, the newest posts "
                "appear here automatically and this list is not needed."
            ),
        ),
    ]

    def sketch_map(self, artworks, gallery_page):
        """Pins for the 'where the sketchbook has been' map (None when fewer than two places are known)."""
        from urllib.parse import quote

        from artworks.places import layout, locate

        places = {}
        for art in artworks.exclude(place="").order_by("year", "first_published_at"):
            coords = locate(art.place)
            if not coords:
                continue
            key = art.place.strip().lower()
            entry = places.setdefault(
                key, {"place": art.place.strip(), "coords": coords, "count": 0, "colour": "", "url": art.url}
            )
            entry["count"] += 1
            if not entry["colour"] and art.palette_list:
                entry["colour"] = art.palette_list[0]
        pins = list(places.values())
        if len(pins) < 2:
            return None
        width, height = 1000.0, 560.0
        for pin, (x, y) in zip(pins, layout([p["coords"] for p in pins], width, height)):
            pin["x"], pin["y"] = round(x, 1), round(y, 1)
            pin["left"], pin["top"] = round(x / width * 100, 2), round(y / height * 100, 2)
            pin["colour"] = pin["colour"] or "#c4553b"
            if gallery_page:
                pin["url"] = f"{gallery_page.url}?place={quote(pin['place'])}"
        return {
            "pins": pins,
            "route": " ".join(f"{p['x']},{p['y']}" for p in pins),
            "width": int(width),
            "height": int(height),
        }

    def instagram_tiles(self):
        """Posts for the homepage strip: automatic ones if connected, else her manual picks."""
        tiles = []
        for post in InstagramPost.objects.all()[:9]:
            if post.image:
                tiles.append({"link": post.permalink, "caption": post.caption, "url": post.image.url})
        if tiles:
            return tiles
        for item in self.instagram_posts.all():
            if not item.image_id:
                continue
            rendition = item.image.get_rendition("fill-480x480|format-webp")
            tiles.append({"link": item.link, "caption": item.caption, "url": rendition.url})
        return tiles

    def get_context(self, request):
        context = super().get_context(request)

        # Import here to avoid circular imports during Django startup.
        from artworks.models import ArtworkIndexPage, ArtworkPage
        from blog.models import BlogIndexPage, BlogPostPage

        artworks = ArtworkPage.objects.live().public().filter(locale=self.locale)

        featured_artworks = list(
            artworks.filter(featured=True).order_by("-first_published_at")[:3]
        )
        latest_artworks = list(artworks.order_by("-first_published_at")[:6])

        hero_artwork = None
        if featured_artworks:
            hero_artwork = featured_artworks[0]
        elif latest_artworks:
            hero_artwork = latest_artworks[0]

        places = []
        for place in artworks.exclude(place="").values_list("place", flat=True):
            if place not in places:
                places.append(place)

        context["gallery_page"] = ArtworkIndexPage.objects.live().child_of(self).first()
        context["blog_page"] = BlogIndexPage.objects.live().child_of(self).first()
        context["featured_artworks"] = featured_artworks
        context["latest_artworks"] = latest_artworks
        context["hero_artwork"] = hero_artwork
        context["places"] = places[:14]
        context["instagram_tiles"] = self.instagram_tiles()
        context["sketch_map"] = self.sketch_map(artworks, context["gallery_page"])
        from shop.models import Testimonial

        language = request.LANGUAGE_CODE if hasattr(request, "LANGUAGE_CODE") else "en"
        context["testimonials"] = [
            {"t": t, "text": t.text_for(language)}
            for t in Testimonial.objects.filter(published=True)[:3]
        ]
        context["latest_posts"] = list(
            BlogPostPage.objects.live().public().filter(locale=self.locale)
            .order_by("-date")[:3]
        )

        return context


class HomePageInstagramPost(Orderable):
    """A post she picked by hand for the homepage Instagram strip."""

    page = ParentalKey(HomePage, on_delete=models.CASCADE, related_name="instagram_posts")
    image = models.ForeignKey(
        "wagtailimages.Image",
        on_delete=models.CASCADE,
        related_name="+",
        help_text="The photo from the post (use your original file).",
    )
    link = models.URLField(
        "Post link",
        blank=True,
        help_text="Optional. Open the post on Instagram, copy the address and paste it here.",
    )
    caption = models.CharField(max_length=160, blank=True)

    panels = [FieldPanel("image"), FieldPanel("link"), FieldPanel("caption")]


class InstagramPost(models.Model):
    """Fetched automatically from Instagram (see manage.py fetch_instagram)."""

    instagram_id = models.CharField(max_length=40, unique=True)
    permalink = models.URLField()
    caption = models.CharField(max_length=160, blank=True)
    image = models.ImageField(upload_to="instagram/")
    posted_at = models.DateTimeField()

    class Meta:
        ordering = ["-posted_at"]


class StandardPage(Page):
    """
    A flexible page for About, legal pages, the commission guide, and anything
    else made of headings, text, images, quotes, buttons, FAQs and price lists.
    """

    intro = models.TextField(
        blank=True,
        help_text="Optional short introduction shown under the title.",
    )

    body = StreamField(page_blocks(), blank=True)

    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional image shown next to the title.",
    )

    show_in_footer = models.BooleanField(
        default=False,
        help_text="Show a link to this page in the footer (good for legal pages).",
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("hero_image"),
        FieldPanel("body"),
    ]

    promote_panels = Page.promote_panels + [FieldPanel("show_in_footer")]

    parent_page_types = ["home.HomePage", "home.StandardPage"]


@register_setting(icon="cog")
class SiteSettings(BaseSiteSetting):
    """Site-wide texts and links: the footer, contact details, social links."""

    tagline = models.CharField(max_length=160, default="Just Keep Layering")
    tagline_de = models.CharField(
        "Tagline (German)", max_length=160, blank=True, default="Just Keep Layering"
    )

    footer_text = models.CharField(
        max_length=240,
        default="Watercolour painting and sketching inspired by travelling.",
    )
    footer_text_de = models.CharField(
        "Footer text (German)",
        max_length=240,
        blank=True,
        default="Aquarelle und Skizzen, inspiriert vom Reisen.",
    )

    contact_email = models.EmailField(
        blank=True,
        help_text="Shown in the footer and on the contact page.",
    )

    instagram_url = models.URLField(
        blank=True,
        default="https://www.instagram.com/from.j2l/",
        help_text="Her Instagram profile. Shown in the footer and on the homepage.",
    )
    instagram_access_token = models.CharField(
        max_length=400,
        blank=True,
        help_text=(
            "Optional, for showing new Instagram posts automatically. Needs a Creator or "
            "Business Instagram account; ask your site helper for the short setup."
        ),
    )
    pinterest_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)

    default_share_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Preview image when a page without its own image is shared.",
    )

    analytics_snippet = models.TextField(
        blank=True,
        help_text=(
            "Optional. Paste a cookieless analytics script (e.g. Plausible). "
            "Leave empty for none. Do not paste anything that sets cookies "
            "without adding a cookie banner first."
        ),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("tagline"),
                FieldPanel("tagline_de"),
                FieldPanel("footer_text"),
                FieldPanel("footer_text_de"),
            ],
            heading="Texts",
        ),
        FieldPanel("contact_email"),
        MultiFieldPanel(
            [
                FieldPanel("instagram_url"),
                FieldPanel("instagram_access_token"),
                FieldPanel("pinterest_url"),
                FieldPanel("facebook_url"),
                FieldPanel("youtube_url"),
            ],
            heading="Social links",
        ),
        FieldPanel("default_share_image"),
        FieldPanel("analytics_snippet"),
    ]

    @property
    def instagram_handle(self):
        parts = [p for p in self.instagram_url.split("/") if p]
        return "@" + parts[-1] if parts and "instagram.com" in self.instagram_url else ""

    class Meta:
        verbose_name = "Site settings"
