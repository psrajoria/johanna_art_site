"""
DEVELOPMENT ONLY: fill the site with generated watercolour-style artworks and
two blog posts so the design can be reviewed with real-looking content.

    python manage.py seed_site
    python manage.py seed_demo

Refuses to run when DEBUG is off, so it can never pollute the live site.
"""

import io
import random
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand, CommandError
from PIL import Image as PILImage
from PIL import ImageChops, ImageDraw, ImageFilter
from wagtail.images.models import Image
from wagtail.models import Locale

from artworks.models import ArtworkIndexPage, ArtworkPage, Offer
from blog.models import BlogIndexPage, BlogPostPage

PAPER = (247, 241, 229)

PALETTES = {
    "warm": [(227, 169, 59), (196, 85, 59), (232, 165, 160), (107, 63, 94)],
    "cool": [(91, 131, 168), (134, 169, 139), (232, 165, 160), (59, 98, 133)],
    "earth": [(196, 85, 59), (227, 169, 59), (134, 169, 139), (90, 79, 71)],
    "dusk": [(107, 63, 94), (91, 131, 168), (232, 165, 160), (227, 169, 59)],
}

# title, title_de, place, country, category, palette, kind, w, h, year, en story, de story
ARTWORKS = [
    ("Kraków, Main Square at Dusk", "Krakau, Hauptmarkt in der Dämmerung", "Kraków", "Poland", "travel", "dusk", "town", 30, 40, 2025,
     "The light left the square slowly, one window at a time. I painted this from a café table with cold hands.",
     "Das Licht verließ den Platz langsam, Fenster für Fenster. Ich habe das von einem Café-Tisch aus gemalt, mit kalten Händen."),
    ("Prague Rooftops", "Prager Dächer", "Prague", "Czech Republic", "architecture", "warm", "roofs", 24, 32, 2025,
     "A sea of terracotta tiles seen from the castle hill. The trick was leaving the paper white where the sun hit.",
     "Ein Meer aus Terrakottaziegeln, gesehen vom Burgberg. Der Trick war, das Papier dort weiß zu lassen, wo die Sonne traf."),
    ("Pollença, Morning Steps", "Pollença, Morgentreppen", "Pollença", "Spain", "travel", "earth", "town", 24, 30, 2024,
     "365 steps up to the chapel — and the early light on the stone made every one of them worth it.",
     "365 Stufen hinauf zur Kapelle — und das frühe Licht auf dem Stein hat jede einzelne gelohnt."),
    ("Braunschweig, Burgplatz", "Braunschweig, Burgplatz", "Braunschweig", "Germany", "architecture", "cool", "town", 30, 40, 2025,
     "My own backyard: the lion, the cathedral and a very grey Sunday afternoon that turned out beautiful.",
     "Mein Zuhause: der Löwe, der Dom und ein sehr grauer Sonntagnachmittag, der wunderschön wurde."),
    ("Lake Garda, First Light", "Gardasee, erstes Licht", "Lake Garda", "Italy", "landscape", "cool", "lake", 40, 30, 2024,
     "Mist on the water, mountains dissolving into sky. Mostly wet-on-wet and a lot of patience.",
     "Nebel auf dem Wasser, Berge, die im Himmel verschwimmen. Meist nass-in-nass und viel Geduld."),
    ("Lisbon Tram 28", "Lissabon, Tram 28", "Lisbon", "Portugal", "travel", "warm", "town", 24, 30, 2025,
     "Yellow tram, blue tiles, a hill I did not climb gracefully. Quick sketch, finished with colour back at the hotel.",
     "Gelbe Tram, blaue Kacheln, ein Hügel, den ich nicht elegant erklommen habe. Schnelle Skizze, abends im Hotel koloriert."),
    ("Venice, Peeling Facade", "Venedig, bröckelnde Fassade", "Venice", "Italy", "architecture", "earth", "town", 30, 40, 2023,
     "I love a wall that has stories. Layers of plaster, salt and time — a perfect subject for layering.",
     "Ich liebe Wände mit Geschichten. Schichten aus Putz, Salz und Zeit — das perfekte Motiv zum Schichten."),
    ("Sketchbook: Café in Vienna", "Skizzenbuch: Café in Wien", "Vienna", "Austria", "sketchbook", "dusk", "town", 21, 15, 2025,
     "Pencil and a quick wash, drawn while the coffee went cold. Sketchbook pages are my favourite kind of honest.",
     "Bleistift und eine schnelle Lasur, gezeichnet, während der Kaffee kalt wurde. Skizzenbuchseiten sind meine liebste Form von Ehrlichkeit."),
]

POSTS = [
    ("Why I paint in layers", "Warum ich in Schichten male", "layering", "Schichten",
     "Patience, pigment and the joy of letting a wash dry.",
     "Geduld, Pigment und die Freude, eine Lasur trocknen zu lassen.",
     ["Watercolour rewards patience. A first wash is never the painting — it is the start of a conversation with the paper.",
      "I build each piece in three or four layers: a pale underpainting, the main shapes, then small darks and details. In between, I wait. Waiting is half of the technique.",
      "It also taught me something outside the studio: a thing does not have to be right the first time to become beautiful."],
     ["Watercolour is built in layers. Aquarell entsteht in Schichten. Die erste Lasur ist nie das Bild — sie ist der Anfang eines Gesprächs mit dem Papier.",
      "Ich baue jedes Bild in drei oder vier Schichten auf: eine helle Untermalung, die Hauptformen, dann kleine Dunkelheiten und Details. Dazwischen warte ich. Warten ist die halbe Technik.",
      "Es hat mir auch etwas außerhalb des Ateliers beigebracht: Etwas muss nicht beim ersten Mal richtig sein, um schön zu werden."]),
    ("What's in my travel sketch kit", "Was in meinem Reise-Skizzen-Set steckt", "travel", "Reisen",
     "A small bag, a few pans of colour and one very battered brush.",
     "Eine kleine Tasche, ein paar Näpfchen Farbe und ein sehr mitgenommener Pinsel.",
     ["Everything I need fits in a pencil case: a pocket watercolour set, a waterbrush, a 2B pencil and a small sketchbook with cotton paper.",
      "Less gear means more looking. When I only have six colours, I notice what a place is really made of."],
     ["Alles, was ich brauche, passt in ein Mäppchen: ein Taschen-Aquarellkasten, ein Wassertankpinsel, ein 2B-Bleistift und ein kleines Skizzenbuch mit Baumwollpapier.",
      "Weniger Ausrüstung heißt mehr Hinschauen. Wenn ich nur sechs Farben habe, erkenne ich, woraus ein Ort wirklich besteht."]),
]


def watercolour(seed, palette, kind, size=(900, 1125)):
    """Procedurally paint something that reads as a loose watercolour."""
    rng = random.Random(seed)
    w, h = size
    colours = PALETTES[palette]
    img = PILImage.new("RGB", size, PAPER)

    def wash(box, colour, alpha, blur):
        layer = PILImage.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse(box, fill=colour + (alpha,))
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
        img.paste(layer, (0, 0), layer)

    # sky
    for i in range(5):
        c = rng.choice(colours)
        cx, cy = rng.randint(0, w), rng.randint(0, int(h * 0.35))
        r = rng.randint(w // 3, w // 2)
        wash((cx - r, cy - r // 2, cx + r, cy + r // 2), c, rng.randint(70, 130), 55)

    horizon = int(h * rng.uniform(0.52, 0.64))
    draw_layer = PILImage.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(draw_layer)
    ink = PILImage.new("RGBA", size, (0, 0, 0, 0))
    ink_d = ImageDraw.Draw(ink)

    if kind in ("town", "roofs"):
        x = -20
        while x < w:
            bw = rng.randint(70, 150)
            bh = rng.randint(120, 330) if kind == "town" else rng.randint(60, 150)
            top = horizon - bh
            c = rng.choice(colours)
            c = tuple(min(255, int(v * rng.uniform(0.85, 1.1))) for v in c)
            draw.rectangle((x, top, x + bw, horizon + 60), fill=c + (rng.randint(150, 215),))
            if kind == "roofs":
                draw.polygon([(x - 8, top), (x + bw / 2, top - rng.randint(30, 60)), (x + bw + 8, top)], fill=c + (230,))
            for wy in range(top + 24, horizon, 44):
                for wx in range(x + 14, x + bw - 18, 30):
                    ink_d.rectangle((wx, wy, wx + 12, wy + 20), outline=(60, 50, 46, 120), width=2)
            jx = rng.randint(-3, 3)
            ink_d.rectangle((x + jx, top, x + bw + jx, horizon + 60), outline=(55, 46, 42, 170), width=2)
            x += bw + rng.randint(-14, 8)
    elif kind == "lake":
        for i in range(4):
            c = colours[i % len(colours)]
            pts = [(0, horizon)]
            for px in range(0, w + 60, 60):
                pts.append((px, horizon - rng.randint(60, 220) * (1 - abs(px - w / 2) / w)))
            pts.append((w, horizon))
            draw.polygon(pts, fill=c + (110,))
        wash((-100, horizon, w + 100, h + 200), colours[0], 90, 60)

    img.paste(draw_layer.filter(ImageFilter.GaussianBlur(1.6)), (0, 0), draw_layer.filter(ImageFilter.GaussianBlur(1.6)))

    # foreground / water wash
    for i in range(4):
        c = rng.choice(colours)
        cx, cy = rng.randint(0, w), rng.randint(horizon, h)
        r = rng.randint(w // 4, w // 2)
        wash((cx - r, cy - r // 3, cx + r, cy + r // 3), c, rng.randint(60, 120), 45)

    img.paste(ink.filter(ImageFilter.GaussianBlur(0.6)), (0, 0), ink)

    # paper grain + soft vignette
    grain = PILImage.effect_noise(size, 28).convert("RGB")
    img = ImageChops.multiply(img, ImageChops.blend(PILImage.new("RGB", size, (255, 255, 255)), grain, 0.18))
    vignette = PILImage.new("L", size, 0)
    ImageDraw.Draw(vignette).ellipse((-w * 0.2, -h * 0.2, w * 1.2, h * 1.2), fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(120))
    img = PILImage.composite(img, PILImage.new("RGB", size, PAPER), vignette.point(lambda v: 150 + v * 105 // 255))
    return img


def as_wagtail_image(title, pil, quality=88):
    buffer = io.BytesIO()
    pil.save(buffer, "JPEG", quality=quality)
    name = f"{title.lower().replace(' ', '-')}.jpg"
    return Image.objects.create(title=title, file=ImageFile(buffer, name=name))


class Command(BaseCommand):
    help = "Development only: create generated demo artworks and blog posts."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo only runs with DEBUG on (development).")

        en = Locale.get_default()
        de = Locale.objects.get(language_code="de")
        gallery = ArtworkIndexPage.objects.filter(locale=en).first()
        blog = BlogIndexPage.objects.filter(locale=en).first()
        if not gallery or not blog:
            raise CommandError("Run `python manage.py seed_site` first.")

        gallery_de = gallery.get_translation_or_none(de)
        blog_de = blog.get_translation_or_none(de)

        for i, data in enumerate(ARTWORKS):
            (title, title_de, place, country, category, palette, kind, wcm, hcm, year, story, story_de) = data
            if ArtworkPage.objects.filter(title=title, locale=en).exists():
                continue
            self.stdout.write(f"  painting {title} …")
            image = as_wagtail_image(title, watercolour(100 + i, palette, kind))
            page = ArtworkPage(
                title=title,
                slug=title.lower().replace(",", "").replace(" ", "-").replace(":", ""),
                main_image=image,
                short_description=story.split(". ")[0].rstrip(".") + ".",
                story=f"<p>{story}</p>",
                category=category,
                place=place,
                country=country,
                width_cm=Decimal(wcm),
                height_cm=Decimal(hcm),
                year=year,
                featured=i < 3,
            )
            gallery.add_child(instance=page)
            page.save_revision().publish()

            # ways to buy
            orig = Offer(artwork=page, kind="original", price=Decimal(80 + 25 * (i % 4)), shipping_class="parcel")
            orig.save()
            if i in (1, 3, 5):
                # a print with limited stock, one made on demand
                Offer(artwork=page, kind="print", label="A4 · 250g cotton paper", label_de="A4 · 250g Baumwollpapier",
                      price=Decimal("24"), stock=3 if i == 1 else None, shipping_class="flat").save()
                Offer(artwork=page, kind="print", label="A3 · 250g cotton paper", label_de="A3 · 250g Baumwollpapier",
                      price=Decimal("38"), stock=None, shipping_class="flat").save()
            if i in (0, 1, 2, 4, 6):
                digital = Offer(artwork=page, kind="digital", price=Decimal("9"), shipping_class="none")
                digital.download_file.save(
                    f"{page.slug}-hires.jpg",
                    ContentFile(_jpeg_bytes(watercolour(100 + i, palette, kind, size=(2400, 3000)))),
                    save=False,
                )
                digital.save()

            # gallery extras on the first piece
            if i == 0:
                from artworks.models import ArtworkPageGalleryImage

                for j in range(2):
                    extra = as_wagtail_image(f"{title} detail {j + 1}", watercolour(900 + j, palette, kind, size=(800, 640)))
                    ArtworkPageGalleryImage.objects.create(page=page, image=extra, caption=["Detail of the light", "Pencil underdrawing"][j])

            if gallery_de:
                translated = page.copy_for_translation(de, copy_parents=True).specific
                translated = ArtworkPage.objects.get(pk=translated.pk)
                translated.title = title_de
                translated.slug = translated.slug + "-de"
                translated.short_description = story_de.split(". ")[0].rstrip(".") + "."
                translated.story = f"<p>{story_de}</p>"
                translated.country = {"Poland": "Polen", "Czech Republic": "Tschechien", "Spain": "Spanien",
                                      "Germany": "Deutschland", "Italy": "Italien", "Portugal": "Portugal",
                                      "Austria": "Österreich"}.get(country, country)
                translated.save()
                translated.save_revision().publish()

        from taggit.models import Tag  # noqa: F401

        for i, (t, t_de, tag, tag_de, intro, intro_de, paras, paras_de) in enumerate(POSTS):
            if BlogPostPage.objects.filter(title=t, locale=en).exists():
                continue
            self.stdout.write(f"  writing {t} …")
            cover = as_wagtail_image(f"blog {i}", watercolour(500 + i, "warm" if i else "cool", "town", size=(1400, 933)))
            body = [{"type": "paragraph", "value": f"<p>{p}</p>"} for p in paras]
            body.insert(1, {"type": "heading", "value": "Layer by layer"})
            post = BlogPostPage(title=t, slug=t.lower().replace("'", "").replace(" ", "-"), hero_image=cover,
                                intro=intro, body=body)
            blog.add_child(instance=post)
            post.tags.add(tag)
            post.save()
            post.save_revision().publish()
            if blog_de:
                tr = post.copy_for_translation(de, copy_parents=True).specific
                tr = BlogPostPage.objects.get(pk=tr.pk)
                tr.title = t_de
                tr.slug = tr.slug + "-de"
                tr.intro = intro_de
                tr.body = [{"type": "paragraph", "value": f"<p>{p}</p>"} for p in paras_de]
                tr.save()
                tr.save_revision().publish()

        self.stdout.write(self.style.SUCCESS("Demo content created."))


def _jpeg_bytes(pil):
    buffer = io.BytesIO()
    pil.save(buffer, "JPEG", quality=90)
    return buffer.getvalue()
