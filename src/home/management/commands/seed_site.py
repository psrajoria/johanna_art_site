"""
Create the page structure (in English and German), site settings and shipping
prices that the site needs to be usable on day one.

Safe to run repeatedly: existing pages are left alone. Johanna then edits all
text in the admin. Legal pages are created as DRAFTS on purpose — they contain
placeholders that must be filled in (and checked by a lawyer) before going live.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import translation
from wagtail.models import Locale, Page, Site

from artworks.models import ArtworkIndexPage
from blog.models import BlogIndexPage
from home.models import HomePage, SiteSettings, StandardPage
from shop.models import ShippingRate, ShopSettings

PLACEHOLDER_NOTE_EN = (
    "PLACEHOLDER — please replace every [bracketed] part with your real details "
    "and have this text checked by a legal professional before you publish it."
)
PLACEHOLDER_NOTE_DE = (
    "PLATZHALTER — bitte ersetze alle [eckigen Klammern] durch deine echten Angaben "
    "und lass den Text von einer Fachperson prüfen, bevor du ihn veröffentlichst."
)


def para(text):
    return {"type": "paragraph", "value": f"<p>{text}</p>"}


def heading(text):
    return {"type": "heading", "value": text}


# --- page content ----------------------------------------------------------
# Each entry: slug, show_in_menus, show_in_footer, live, and per-language
# title/intro/body.

PAGES = [
    {
        "slug": "about",
        "menu": True,
        "footer": False,
        "live": True,
        "en": {
            "title": "About",
            "intro": "Watercolour, pencil, and a lot of looking at the world.",
            "body": [
                heading("Hello, I'm Johanna"),
                para(
                    "I paint and sketch the places I travel to — quiet streets, "
                    "weathered facades, soft landscapes. I work in watercolour and "
                    "pencil, building each piece in thin, patient layers."
                ),
                para(
                    "My motto is <b>just keep layering</b>: a painting rarely works "
                    "on the first wash, and that is the point. Every layer is a "
                    "small decision to keep going."
                ),
                para(
                    "I live and paint in Braunschweig, Germany. Originals, prints and "
                    "digital downloads are all available in the gallery, and I take "
                    "a few commissions each season."
                ),
            ],
        },
        "de": {
            "title": "Über mich",
            "intro": "Aquarell, Bleistift und viel Hinschauen.",
            "body": [
                heading("Hallo, ich bin Johanna"),
                para(
                    "Ich male und skizziere die Orte, die ich bereise — ruhige Gassen, "
                    "verwitterte Fassaden, weiche Landschaften. Ich arbeite mit "
                    "Aquarell und Bleistift und baue jedes Bild in dünnen, geduldigen "
                    "Schichten auf."
                ),
                para(
                    "Mein Motto: <b>just keep layering</b>. Ein Bild gelingt selten mit "
                    "der ersten Lasur — und genau darum geht es. Jede Schicht ist die "
                    "kleine Entscheidung, weiterzumachen."
                ),
                para(
                    "Ich lebe und male in Braunschweig. Originale, Drucke und digitale "
                    "Downloads findest du in der Galerie, und ich nehme jede Saison "
                    "einige Auftragsarbeiten an."
                ),
            ],
        },
    },
    {
        "slug": "commissions",
        "menu": True,
        "footer": False,
        "live": True,
        "en": {
            "title": "Commissions",
            "intro": "A painting of a place that matters to you.",
            "body": [
                para(
                    "Send me a photo of a street, a house, a view from your honeymoon — "
                    "and I will turn it into a watercolour. Every commission is "
                    "painted by hand on cotton paper."
                ),
                {
                    "type": "steps",
                    "value": {
                        "title": "How it works",
                        "steps": [
                            {"title": "Tell me your idea", "text": "Use the contact form: the place, a reference photo, the size you have in mind."},
                            {"title": "Receive a quote", "text": "I reply with a price and an honest timeline. No obligation."},
                            {"title": "Pay and relax", "text": "Once your payment arrives I start painting. You can follow progress on your private request page."},
                            {"title": "It arrives at your door", "text": "Carefully packed and shipped with tracking."},
                        ],
                    },
                },
                {
                    "type": "price_list",
                    "value": {
                        "title": "Guide prices",
                        "rows": [
                            {"label": "A5 sketch", "price": "from 60 €", "note": "Pencil and light wash"},
                            {"label": "A4 watercolour", "price": "from 120 €", "note": "Full painting"},
                            {"label": "A3 watercolour", "price": "from 220 €", "note": "Detailed architecture or landscape"},
                        ],
                    },
                },
                {
                    "type": "faq",
                    "value": {
                        "title": "Questions",
                        "items": [
                            {"question": "How long does a commission take?", "answer": "<p>Usually 2–4 weeks, depending on size. I will tell you a clear date in my quote.</p>"},
                            {"question": "Can I get a print of my commission?", "answer": "<p>Yes — just ask, and I can scan it and make a limited number of prints.</p>"},
                            {"question": "What if I don't like it?", "answer": "<p>I share progress photos along the way, so there are no big surprises at the end.</p>"},
                        ],
                    },
                },
                {"type": "button", "value": {"text": "Request a commission", "page": None, "url": "/contact/inquiry/?type=commission"}},
            ],
        },
        "de": {
            "title": "Auftragsarbeiten",
            "intro": "Ein Bild von einem Ort, der dir etwas bedeutet.",
            "body": [
                para(
                    "Schick mir ein Foto einer Straße, eines Hauses, eines Ausblicks aus "
                    "den Flitterwochen — ich verwandle es in ein Aquarell. Jede "
                    "Auftragsarbeit wird von Hand auf Baumwollpapier gemalt."
                ),
                {
                    "type": "steps",
                    "value": {
                        "title": "So funktioniert es",
                        "steps": [
                            {"title": "Erzähl mir deine Idee", "text": "Nutze das Kontaktformular: der Ort, ein Referenzfoto, die gewünschte Größe."},
                            {"title": "Du bekommst ein Angebot", "text": "Ich antworte mit Preis und ehrlichem Zeitplan. Unverbindlich."},
                            {"title": "Bezahlen und entspannen", "text": "Sobald deine Zahlung da ist, fange ich an. Den Fortschritt verfolgst du auf deiner privaten Anfrageseite."},
                            {"title": "Es kommt zu dir nach Hause", "text": "Sorgfältig verpackt und mit Sendungsverfolgung verschickt."},
                        ],
                    },
                },
                {
                    "type": "price_list",
                    "value": {
                        "title": "Richtpreise",
                        "rows": [
                            {"label": "A5-Skizze", "price": "ab 60 €", "note": "Bleistift und leichte Lasur"},
                            {"label": "A4-Aquarell", "price": "ab 120 €", "note": "Vollständiges Bild"},
                            {"label": "A3-Aquarell", "price": "ab 220 €", "note": "Detailreiche Architektur oder Landschaft"},
                        ],
                    },
                },
                {
                    "type": "faq",
                    "value": {
                        "title": "Fragen",
                        "items": [
                            {"question": "Wie lange dauert eine Auftragsarbeit?", "answer": "<p>Meist 2–4 Wochen, je nach Größe. Im Angebot nenne ich dir einen klaren Termin.</p>"},
                            {"question": "Kann ich einen Druck meiner Auftragsarbeit bekommen?", "answer": "<p>Ja — frag einfach, ich scanne das Bild und mache eine begrenzte Anzahl an Drucken.</p>"},
                            {"question": "Und wenn es mir nicht gefällt?", "answer": "<p>Ich teile unterwegs Fortschrittsfotos, sodass es am Ende keine großen Überraschungen gibt.</p>"},
                        ],
                    },
                },
                {"type": "button", "value": {"text": "Auftrag anfragen", "page": None, "url": "/de/contact/inquiry/?type=commission"}},
            ],
        },
    },
    {
        "slug": "shipping-returns",
        "menu": False,
        "footer": True,
        "live": False,
        "en": {
            "title": "Shipping & returns",
            "intro": PLACEHOLDER_NOTE_EN,
            "body": [
                heading("Shipping"),
                para("Prints ship flat or in a protective tube within 3–5 working days of payment. Originals are packed in a rigid parcel and insured. Shipping costs are shown at checkout."),
                heading("Digital downloads"),
                para("Download links are available on your order page as soon as your payment is confirmed."),
                heading("Returns"),
                para("[Describe your return policy for prints and originals here. Digital downloads and custom commissions are usually excluded.]"),
            ],
        },
        "de": {
            "title": "Versand & Rückgabe",
            "intro": PLACEHOLDER_NOTE_DE,
            "body": [
                heading("Versand"),
                para("Drucke werden innerhalb von 3–5 Werktagen nach Zahlungseingang flach oder in einer Schutzrolle verschickt. Originale werden stabil verpackt und versichert versendet. Die Versandkosten siehst du an der Kasse."),
                heading("Digitale Downloads"),
                para("Download-Links stehen auf deiner Bestellseite bereit, sobald deine Zahlung bestätigt ist."),
                heading("Rückgabe"),
                para("[Hier die Rückgaberegelung für Drucke und Originale beschreiben. Digitale Downloads und individuelle Auftragsarbeiten sind meist ausgeschlossen.]"),
            ],
        },
    },
    {
        "slug": "terms",
        "menu": False,
        "footer": True,
        "live": False,
        "en": {
            "title": "Terms & conditions",
            "intro": PLACEHOLDER_NOTE_EN,
            "body": [
                heading("1. Scope"),
                para("[Name, address]. These terms apply to all orders placed through this website."),
                heading("2. Contract"),
                para("Your order is a binding offer. The contract is concluded when I confirm your payment by email."),
                heading("3. Prices and payment"),
                para("All prices are in euros. [VAT information, e.g. small business regulation §19 UStG.] Payment is made in advance by PayPal or bank transfer."),
                heading("4. Right of withdrawal"),
                para("[Withdrawal information — required by law for consumers in the EU. Digital content and custom-made work need special wording.]"),
                heading("5. Copyright"),
                para("All artworks remain © Johanna Lackner. Digital downloads are licensed for personal use only."),
            ],
        },
        "de": {
            "title": "AGB",
            "intro": PLACEHOLDER_NOTE_DE,
            "body": [
                heading("1. Geltungsbereich"),
                para("[Name, Anschrift]. Diese AGB gelten für alle Bestellungen über diese Website."),
                heading("2. Vertragsschluss"),
                para("Deine Bestellung ist ein verbindliches Angebot. Der Vertrag kommt zustande, wenn ich deine Zahlung per E-Mail bestätige."),
                heading("3. Preise und Zahlung"),
                para("Alle Preise in Euro. [Hinweis zur Umsatzsteuer, z. B. Kleinunternehmerregelung §19 UStG.] Die Zahlung erfolgt im Voraus per PayPal oder Überweisung."),
                heading("4. Widerrufsrecht"),
                para("[Widerrufsbelehrung — für Verbraucher in der EU gesetzlich vorgeschrieben. Digitale Inhalte und Anfertigungen nach Kundenwunsch benötigen besondere Formulierungen.]"),
                heading("5. Urheberrecht"),
                para("Alle Werke bleiben © Johanna Lackner. Digitale Downloads sind nur für den privaten Gebrauch lizenziert."),
            ],
        },
    },
    {
        "slug": "privacy",
        "menu": False,
        "footer": True,
        "live": False,
        "en": {
            "title": "Privacy policy",
            "intro": PLACEHOLDER_NOTE_EN,
            "body": [
                heading("Who is responsible"),
                para("[Name, address, email]"),
                heading("What data is collected"),
                para("When you order or send a message, I store your name, email, address (for shipping) and your message so I can fulfil your request. Orders must be kept for tax reasons for up to 10 years."),
                heading("Cookies"),
                para("This site uses only the technically necessary cookies (shopping cart and login). No tracking or advertising cookies are used. Fonts are hosted on this server."),
                heading("Your rights"),
                para("You can ask at any time for access to, correction of, or deletion of your data. [Add contact for data requests and the competent supervisory authority.]"),
            ],
        },
        "de": {
            "title": "Datenschutzerklärung",
            "intro": PLACEHOLDER_NOTE_DE,
            "body": [
                heading("Verantwortliche Stelle"),
                para("[Name, Anschrift, E-Mail]"),
                heading("Welche Daten erhoben werden"),
                para("Wenn du bestellst oder eine Nachricht sendest, speichere ich deinen Namen, deine E-Mail, deine Adresse (für den Versand) und deine Nachricht, um deine Anfrage zu bearbeiten. Bestelldaten müssen aus steuerlichen Gründen bis zu 10 Jahre aufbewahrt werden."),
                heading("Cookies"),
                para("Diese Seite verwendet nur technisch notwendige Cookies (Warenkorb und Login). Es werden keine Tracking- oder Werbe-Cookies eingesetzt. Schriften werden auf diesem Server gehostet."),
                heading("Deine Rechte"),
                para("Du kannst jederzeit Auskunft, Berichtigung oder Löschung deiner Daten verlangen. [Kontakt für Datenschutzanfragen und zuständige Aufsichtsbehörde ergänzen.]"),
            ],
        },
    },
    {
        "slug": "imprint",
        "menu": False,
        "footer": True,
        "live": False,
        "en": {
            "title": "Legal notice",
            "intro": PLACEHOLDER_NOTE_EN,
            "body": [
                heading("Information according to §5 DDG"),
                para("Johanna [Surname]<br>[Street and number]<br>[Postcode] Braunschweig<br>Germany"),
                heading("Contact"),
                para("Email: [email address]<br>Phone: [optional]"),
                heading("VAT"),
                para("[VAT ID, or: no VAT is charged in accordance with §19 UStG.]"),
            ],
        },
        "de": {
            "title": "Impressum",
            "intro": PLACEHOLDER_NOTE_DE,
            "body": [
                heading("Angaben gemäß §5 DDG"),
                para("Johanna [Nachname]<br>[Straße und Hausnummer]<br>[PLZ] Braunschweig<br>Deutschland"),
                heading("Kontakt"),
                para("E-Mail: [E-Mail-Adresse]<br>Telefon: [optional]"),
                heading("Umsatzsteuer"),
                para("[Umsatzsteuer-ID oder: Gemäß §19 UStG wird keine Umsatzsteuer berechnet.]"),
            ],
        },
    },
]

SHIPPING_DEFAULTS = [
    # zone, class, price, estimate en, estimate de
    ("de", "flat", "2.90", "2–4 working days", "2–4 Werktage"),
    ("de", "parcel", "6.90", "2–4 working days", "2–4 Werktage"),
    ("eu", "flat", "5.90", "4–8 working days", "4–8 Werktage"),
    ("eu", "parcel", "14.90", "4–8 working days", "4–8 Werktage"),
    ("world", "flat", "9.90", "7–14 working days", "7–14 Werktage"),
    ("world", "parcel", "29.90", "7–14 working days", "7–14 Werktage"),
]

HOME_DE = {
    "title": "Startseite",
    "hero_eyebrow": "Aquarell & Skizzen",
    "hero_title": "Orte, Erinnerungen und unperfekte",
    "hero_highlight": "Schichten.",
    "hero_text": (
        "<p>Reiseinspirierte Aquarellskizzen von Johanna Lackner — ruhige Gassen, "
        "weiche Landschaften, Architektur und kleine Momente, festgehalten mit "
        "Bleistift, Farbe und Übung.</p>"
    ),
    "featured_title": "Ein Skizzenbuch voller Orte.",
    "featured_text": (
        "<p>Eine wachsende Sammlung von Reiseskizzen, Architektur, Landschaften "
        "und Studien — jedes Bild mit seinem eigenen Ort, seiner Erinnerung und "
        "Geschichte.</p>"
    ),
    "process_title": "Weiche Schichten, langsames Schauen.",
    "process_text": (
        "<p>Aquarell entsteht in Schichten: helle Lasuren, Bleistiftstriche, "
        "kleine Korrekturen — und die Entscheidung, weiterzumachen, auch wenn "
        "ein Bild nicht perfekt ist.</p>"
    ),
    "shop_title": "Nimm dir ein Stück mit nach Hause.",
    "shop_text": (
        "<p>Original-Gemälde, hochwertige Drucke in mehreren Größen und digitale "
        "Downloads zum Selberdrucken.</p>"
    ),
    "commission_title": "Verwandle einen Ort in eine Aquarell-Erinnerung.",
    "commission_text": (
        "<p>Frag ein individuelles Bild an — nach einem Reisefoto, einer "
        "Lieblingsstraße, einem Haus, einer Fassade oder einem Ort, der dir "
        "etwas bedeutet.</p>"
    ),
}


class Command(BaseCommand):
    help = "Create the default pages (EN + DE), settings and shipping prices."

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            help="The live domain (e.g. johannal.art). Updates the Wagtail site "
            "record so sitemaps and links use it.",
        )

    def handle(self, *args, **options):
        de, _ = Locale.objects.get_or_create(language_code="de")
        en = Locale.get_default()

        home = HomePage.objects.filter(locale=en).first()
        if home is None:
            self.stderr.write("No English HomePage found — run migrate first.")
            return

        site = Site.objects.filter(is_default_site=True).first()
        if site and site.root_page_id != home.pk:
            site.root_page = home
            site.save()
        if site and options.get("domain"):
            site.hostname = options["domain"]
            site.port = 443
            site.site_name = "Johanna Lackner"
            site.save()
            self.stdout.write(f"  site domain set to {options['domain']}")

        home_de = self._translate(home, de)
        self._apply_home_de(home_de)

        gallery = self._ensure(
            home, ArtworkIndexPage, "gallery", "Gallery", menu=True,
            extra={"intro": "<p>Original paintings, fine-art prints and digital downloads — all from the sketchbook.</p>"},
        )
        gallery_de = self._translate(gallery, de)
        self._set(gallery_de, "Galerie", slug="galerie", intro="<p>Original-Gemälde, hochwertige Drucke und digitale Downloads — alles aus dem Skizzenbuch.</p>")

        blog = self._ensure(
            home, BlogIndexPage, "blog", "Blog", menu=True,
            extra={"intro": "<p>Notes on watercolour, travelling and making art.</p>"},
        )
        blog_de = self._translate(blog, de)
        self._set(blog_de, "Blog", slug="blog", intro="<p>Notizen über Aquarell, Reisen und das Malen.</p>")

        for spec in PAGES:
            en_page = self._ensure_standard(home, spec, "en")
            de_page = self._translate(en_page, de)
            self._apply_standard(de_page, spec, "de")

        self._ensure_settings(site)
        self._ensure_shipping()
        self.stdout.write(self.style.SUCCESS("Site structure is ready."))

    # --- helpers ---------------------------------------------------------

    def _ensure(self, parent, model, slug, title, menu, extra=None):
        existing = model.objects.child_of(parent).first()
        if existing:
            return existing
        page = model(title=title, slug=slug, show_in_menus=menu, **(extra or {}))
        parent.add_child(instance=page)
        page.save_revision().publish()
        self.stdout.write(f"  created {title}")
        return page

    def _translate(self, page, locale):
        """Return the translation, creating it if needed (`.is_new` tells which)."""
        existing = page.get_translation_or_none(locale)
        if existing:
            result = existing.specific
            result.is_new = False
            return result
        result = page.copy_for_translation(locale, copy_parents=True).specific
        result.is_new = True
        return result

    def _set(self, page, title, slug=None, **fields):
        """Fill in German text on a new translation (only when still untouched)."""
        is_new = getattr(page, "is_new", True)
        page = page.specific_class.objects.get(pk=page.pk)
        if is_new:
            page.title = title
            if slug:
                page.slug = slug
            for key, value in fields.items():
                setattr(page, key, value)
            page.save()
            page.save_revision().publish()

    def _apply_home_de(self, home_de):
        is_new = getattr(home_de, "is_new", True)
        home_de = HomePage.objects.get(pk=home_de.pk)
        if is_new:
            for key, value in HOME_DE.items():
                setattr(home_de, key, value)
            home_de.slug = "start"
            home_de.save()
            home_de.save_revision().publish()

    def _ensure_standard(self, home, spec, lang):
        existing = StandardPage.objects.child_of(home).filter(slug=spec["slug"]).first()
        if existing:
            return existing
        content = spec[lang]
        page = StandardPage(
            title=content["title"],
            slug=spec["slug"],
            intro=content["intro"],
            body=content["body"],
            show_in_menus=spec["menu"],
            show_in_footer=spec["footer"],
            live=spec["live"],
        )
        home.add_child(instance=page)
        if spec["live"]:
            page.save_revision().publish()
        else:
            page.save_revision()
        self.stdout.write(f"  created {content['title']}" + ("" if spec["live"] else " (draft)"))
        return page

    def _apply_standard(self, de_page, spec, lang):
        is_new = getattr(de_page, "is_new", True)
        de_page = StandardPage.objects.get(pk=de_page.pk)
        if is_new and lang == "de":
            content = spec["de"]
            de_page.title = content["title"]
            de_page.intro = content["intro"]
            de_page.body = content["body"]
            de_page.slug = {
                "about": "ueber-mich",
                "commissions": "auftragsarbeiten",
                "shipping-returns": "versand-rueckgabe",
                "terms": "agb",
                "privacy": "datenschutz",
                "imprint": "impressum",
            }[spec["slug"]]
            de_page.live = spec["live"]
            de_page.save()
            if spec["live"]:
                de_page.save_revision().publish()
            else:
                de_page.save_revision()

    def _ensure_settings(self, site):
        if not site:
            return
        settings_obj = SiteSettings.for_site(site)
        if not settings_obj.contact_email:
            settings_obj.contact_email = "hello@example.com"
            settings_obj.save()
        ShopSettings.for_site(site)

    def _ensure_shipping(self):
        for zone, cls, price, est_en, est_de in SHIPPING_DEFAULTS:
            ShippingRate.objects.get_or_create(
                zone=zone,
                shipping_class=cls,
                defaults={
                    "price": Decimal(price),
                    "delivery_estimate": est_en,
                    "delivery_estimate_de": est_de,
                },
            )
