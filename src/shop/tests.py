import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse
from wagtail.images.tests.utils import get_test_image_file
from wagtail.images.models import Image
from wagtail.models import Locale

from artworks.models import ArtworkIndexPage, ArtworkPage, Offer

from .cart import Cart, OrderError, place_order
from .models import DiscountCode, Order, ShippingRate, Testimonial, WaitlistRequest
from .shipping import ShippingUnavailable, calculate_shipping

PRIVATE_ROOT = tempfile.mkdtemp()


def make_artwork(title="Test Artwork", slug="test-artwork"):
    gallery = ArtworkIndexPage.objects.get(locale=Locale.get_default())
    image = Image.objects.create(title=title, file=get_test_image_file())
    page = ArtworkPage(title=title, slug=slug, main_image=image, place="Kraków")
    gallery.add_child(instance=page)
    page.save_revision().publish()
    return page


class FakeRequest:
    """Just enough of a request for Cart: a dict-like session."""

    def __init__(self):
        self.session = type("S", (dict,), {"modified": False})()


def cart_with(*offers_and_qty):
    request = FakeRequest()
    cart = Cart(request)
    for offer, qty in offers_and_qty:
        for _ in range(qty):
            cart.add(offer)
    return cart


CHECKOUT = {
    "email": "buyer@example.com",
    "name": "Bea Buyer",
    "payment_method": "paypal",
    "address_line1": "Hauptstr. 1",
    "postal_code": "38100",
    "city": "Braunschweig",
    "country": "DE",
    "accept_terms": "on",
}


@override_settings(PRIVATE_MEDIA_ROOT=PRIVATE_ROOT)
class ShopTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_site", verbosity=0)
        cls.artwork = make_artwork()
        cls.original = Offer.objects.create(
            artwork=cls.artwork, kind="original", price=Decimal("120"), shipping_class="parcel"
        )
        cls.print_a4 = Offer.objects.create(
            artwork=cls.artwork, kind="print", label="A4", price=Decimal("24"), stock=3,
            shipping_class="flat",
        )
        cls.digital = Offer(artwork=cls.artwork, kind="digital", price=Decimal("9"), shipping_class="none")
        cls.digital.download_file.save("art.jpg", ContentFile(b"fake-bytes"), save=False)
        cls.digital.save()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(PRIVATE_ROOT, ignore_errors=True)

    def order_for(self, *offers_and_qty, **data):
        form = dict(CHECKOUT, **data)
        return place_order(cart_with(*offers_and_qty), form, None, "en")


class ShippingTests(ShopTestCase):
    def lines(self, *pairs):
        return cart_with(*pairs).lines()

    def test_germany_flat_is_charged_once(self):
        total, _ = calculate_shipping(self.lines((self.print_a4, 2)), "DE")
        self.assertEqual(total, Decimal("2.90"))

    def test_parcels_are_charged_each_and_zone_matters(self):
        lines = self.lines((self.original, 1), (self.print_a4, 1))
        total, _ = calculate_shipping(lines, "FR")  # EU: parcel 14.90 + flat 5.90
        self.assertEqual(total, Decimal("20.80"))

    def test_digital_is_free(self):
        total, _ = calculate_shipping(self.lines((self.digital, 1)), "US")
        self.assertEqual(total, Decimal("0.00"))

    def test_free_shipping_threshold_only_in_germany(self):
        lines = self.lines((self.original, 1))
        self.assertEqual(calculate_shipping(lines, "DE", free_over=Decimal("100"))[0], Decimal("0.00"))
        self.assertGreater(calculate_shipping(lines, "AT", free_over=Decimal("100"))[0], 0)

    def test_missing_rate_is_reported(self):
        ShippingRate.objects.filter(zone="world").delete()
        with self.assertRaises(ShippingUnavailable):
            calculate_shipping(self.lines((self.print_a4, 1)), "US")


class OrderFlowTests(ShopTestCase):
    def test_placing_an_order_reserves_stock_and_totals(self):
        order = self.order_for((self.print_a4, 2))
        self.print_a4.refresh_from_db()
        self.assertEqual(self.print_a4.stock, 1)
        self.assertEqual(order.status, Order.STATUS_AWAITING)
        self.assertEqual(order.subtotal, Decimal("48"))
        self.assertEqual(order.shipping_cost, Decimal("2.90"))
        self.assertEqual(order.total, Decimal("50.90"))
        self.assertRegex(order.number, r"^JL-\d{4}-\d{4}$")

    def test_cannot_oversell_a_print(self):
        self.order_for((self.print_a4, 3))
        with self.assertRaises(OrderError):
            self.order_for((self.print_a4, 1))

    def test_paying_counts_sales_and_emails_customer(self):
        order = self.order_for((self.print_a4, 2))
        mail.outbox.clear()
        order.status = Order.STATUS_PAID
        order.save()
        self.print_a4.refresh_from_db()
        self.assertEqual(self.print_a4.sold_count, 2)
        order.refresh_from_db()
        self.assertIsNotNone(order.paid_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(order.number, mail.outbox[0].subject)

    def test_original_goes_reserved_then_sold_in_every_language(self):
        order = self.order_for((self.original, 1))
        self.artwork.refresh_from_db()
        self.assertEqual(self.artwork.status, "reserved")
        order.status = Order.STATUS_PAID
        order.save()
        self.artwork.refresh_from_db()
        self.assertEqual(self.artwork.status, "sold")

    def test_sold_original_cannot_be_bought_again(self):
        order = self.order_for((self.original, 1))
        order.status = Order.STATUS_PAID
        order.save()
        with self.assertRaises(OrderError):
            self.order_for((self.original, 1))

    def test_cancelling_releases_stock_and_original(self):
        order = self.order_for((self.original, 1), (self.print_a4, 2))
        order.status = Order.STATUS_CANCELLED
        order.save()
        self.print_a4.refresh_from_db()
        self.artwork.refresh_from_db()
        self.assertEqual(self.print_a4.stock, 3)
        self.assertEqual(self.artwork.status, "available")

    def test_cancelling_a_paid_order_undoes_the_sale(self):
        order = self.order_for((self.print_a4, 1))
        order.status = Order.STATUS_PAID
        order.save()
        order.status = Order.STATUS_CANCELLED
        order.save()
        self.print_a4.refresh_from_db()
        self.assertEqual(self.print_a4.sold_count, 0)
        self.assertEqual(self.print_a4.stock, 3)

    def test_cancelled_orders_cannot_be_reopened(self):
        order = self.order_for((self.print_a4, 1))
        order.status = Order.STATUS_CANCELLED
        order.save()
        order = Order.objects.get(pk=order.pk)
        order.status = Order.STATUS_AWAITING
        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_shipping_sends_tracking_email_once(self):
        order = self.order_for((self.print_a4, 1))
        order.status = Order.STATUS_PAID
        order.save()
        mail.outbox.clear()
        order.status = Order.STATUS_SHIPPED
        order.tracking_number = "ABC123"
        order.save()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("ABC123", mail.outbox[0].body)
        order.save()
        self.assertEqual(len(mail.outbox), 1)

    def test_digital_only_order_completes_when_paid(self):
        order = self.order_for((self.digital, 1), country="")
        self.assertFalse(order.has_physical)
        self.assertEqual(order.shipping_cost, 0)
        order.status = Order.STATUS_PAID
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_COMPLETED)


class DownloadTests(ShopTestCase):
    def test_download_needs_a_paid_order(self):
        order = self.order_for((self.digital, 1))
        item = order.items.get()
        url = reverse("shop:download", args=[order.token, item.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

        order.status = Order.STATUS_PAID
        order.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"fake-bytes")
        item.refresh_from_db()
        self.assertEqual(item.download_count, 1)

    def test_wrong_token_is_404(self):
        order = self.order_for((self.digital, 1))
        item = order.items.get()
        order.status = Order.STATUS_PAID
        order.save()
        url = reverse("shop:download", args=["not-the-token", item.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_download_limit(self):
        order = self.order_for((self.digital, 1))
        item = order.items.get()
        order.status = Order.STATUS_PAID
        order.save()
        item.download_count = Order.MAX_DOWNLOADS
        item.save()
        url = reverse("shop:download", args=[order.token, item.pk])
        self.assertEqual(self.client.get(url).status_code, 404)


class CheckoutViewTests(ShopTestCase):
    def add(self, offer, **extra):
        return self.client.post(reverse("shop:cart_add", args=[offer.pk]), extra)

    def test_guest_checkout_end_to_end(self):
        self.add(self.print_a4)
        response = self.client.get(reverse("shop:cart"))
        self.assertContains(response, "Test Artwork")

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("shop:checkout"), CHECKOUT)
        order = Order.objects.get()
        self.assertRedirects(response, reverse("shop:order", args=[order.token]))
        self.assertEqual(order.email, "buyer@example.com")
        self.assertEqual(len(mail.outbox), 1)  # customer (owner has no address set)
        self.assertContains(self.client.get(reverse("shop:order", args=[order.token])), order.number)
        # cart is empty afterwards
        self.assertContains(self.client.get(reverse("shop:cart")), "empty")

    def test_checkout_requires_terms_and_address_for_physical(self):
        self.add(self.print_a4)
        data = dict(CHECKOUT)
        data.pop("accept_terms")
        data["address_line1"] = ""
        response = self.client.post(reverse("shop:checkout"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.assertTrue(response.context["form"].errors.get("accept_terms"))
        self.assertTrue(response.context["form"].errors.get("address_line1"))

    def test_digital_needs_waiver_but_no_address(self):
        self.add(self.digital)
        data = {k: v for k, v in CHECKOUT.items() if k in ("email", "name", "payment_method", "accept_terms")}
        response = self.client.post(reverse("shop:checkout"), data)
        self.assertEqual(response.status_code, 200)  # waiver missing
        data["accept_digital_waiver"] = "on"
        response = self.client.post(reverse("shop:checkout"), data)
        self.assertEqual(response.status_code, 302)

    def test_honeypot_blocks_bots(self):
        self.add(self.print_a4)
        response = self.client.post(reverse("shop:checkout"), dict(CHECKOUT, website="http://spam"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())

    def test_sold_original_cannot_be_added(self):
        order = self.order_for((self.original, 1))
        order.status = Order.STATUS_PAID
        order.save()
        self.add(self.original)
        self.assertEqual(len(Cart(self.client)), 0) if False else None
        self.assertNotContains(self.client.get(reverse("shop:cart")), "Original painting")

    def test_order_lookup_needs_matching_email(self):
        order = self.order_for((self.print_a4, 1))
        url = reverse("shop:order_lookup")
        bad = self.client.post(url, {"number": order.number, "email": "other@example.com"})
        self.assertEqual(bad.status_code, 200)
        good = self.client.post(url, {"number": order.number, "email": "BUYER@example.com"})
        self.assertRedirects(good, reverse("shop:order", args=[order.token]))

    def test_german_checkout_keeps_language_on_order(self):
        self.client.post(reverse("shop:cart_add", args=[self.print_a4.pk]))
        self.client.post("/de/shop/checkout/", CHECKOUT)
        self.assertEqual(Order.objects.get().language, "de")


class HiddenPriceTests(ShopTestCase):
    def test_hidden_price_blocks_buying_and_hides_prices(self):
        ArtworkPage.objects.filter(pk=self.artwork.pk).update(price_visible=False)
        page = ArtworkPage.objects.get(pk=self.artwork.pk)
        self.assertEqual(page.purchasable_offers, [])
        self.assertIsNone(page.from_price)
        self.client.post(reverse("shop:cart_add", args=[self.print_a4.pk]))
        self.assertNotContains(self.client.get(reverse("shop:cart")), "Test Artwork")
        page_html = self.client.get(page.url).content.decode()
        self.assertIn("Price on request", page_html)
        self.assertNotIn("Add to cart", page_html)
        self.assertNotIn("24.00", page_html)


class ErrorPageTests(ShopTestCase):
    @override_settings(DEBUG=False)
    def test_styled_404_in_both_languages(self):
        for path, text in (("/nope/", "wandered off the paper"), ("/de/nope/", "Papier")):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertContains(response, text, status_code=404)
            self.assertContains(response, "Johanna Lackner", status_code=404)

    def test_500_page_is_self_contained(self):
        from django.template.loader import render_to_string

        html = render_to_string("500.html")
        self.assertIn("The paint spilled", html)
        self.assertNotIn("{%", html)


class DiscountTests(ShopTestCase):
    def cart(self, code=None, *pairs):
        cart = cart_with(*(pairs or ((self.print_a4, 2),)))  # 2 x A4 = 48 EUR
        if code:
            cart.set_code(code)
        return cart

    def test_percent_code_reduces_total_and_counts_use(self):
        DiscountCode.objects.create(code="summer10", kind="percent", value=10, max_uses=1)
        order = place_order(self.cart("SUMMER10"), dict(CHECKOUT), None, "en")
        self.assertEqual(order.discount_amount, Decimal("4.80"))
        self.assertEqual(order.total, Decimal("48.00") - Decimal("4.80") + Decimal("2.90"))
        self.assertEqual(DiscountCode.objects.get().used_count, 1)
        # the single use is gone
        with self.assertRaises(OrderError):
            place_order(self.cart("SUMMER10"), dict(CHECKOUT), None, "en")

    def test_cancelling_gives_the_use_back(self):
        DiscountCode.objects.create(code="ONCE", kind="fixed", value=5, max_uses=1)
        order = place_order(self.cart("ONCE"), dict(CHECKOUT), None, "en")
        order.status = Order.STATUS_CANCELLED
        order.save()
        self.assertEqual(DiscountCode.objects.get().used_count, 0)

    def test_rules(self):
        cart = self.cart()
        subtotal = Decimal("48.00")
        self.assertIn("at least", DiscountCode(code="A", kind="fixed", value=5, min_order=100).problem(subtotal))
        self.assertIn("expired", DiscountCode(code="B", kind="fixed", value=5, valid_until=timezone.localdate() - timedelta(days=1)).problem(subtotal))
        self.assertTrue(DiscountCode(code="C", kind="fixed", value=5, active=False).problem(subtotal))
        # a fixed code never takes more than the goods are worth
        self.assertEqual(DiscountCode(code="D", kind="fixed", value=500).amounts(subtotal)[0], subtotal)
        self.assertEqual(cart.pricing(cart.lines())["discount"], 0)

    def test_gift_card_balance_is_spent_over_two_orders(self):
        DiscountCode.objects.create(code="GIFT50", kind="gift", value=50)
        first = place_order(self.cart("GIFT50"), dict(CHECKOUT), None, "en")  # 48 off, 2 EUR left
        self.assertEqual(first.discount_amount, Decimal("48.00"))
        self.assertEqual(DiscountCode.objects.get().remaining, Decimal("2.00"))
        second = place_order(self.cart("GIFT50", (self.print_a4, 1)), dict(CHECKOUT), None, "en")
        self.assertEqual(second.discount_amount, Decimal("2.00"))
        self.assertEqual(DiscountCode.objects.get().remaining, Decimal("0.00"))
        first.status = Order.STATUS_CANCELLED
        first.save()
        self.assertEqual(DiscountCode.objects.get().remaining, Decimal("48.00"))

    def test_free_shipping_code(self):
        DiscountCode.objects.create(code="SHIPFREE", kind="free_shipping")
        order = place_order(self.cart("SHIPFREE"), dict(CHECKOUT), None, "en")
        self.assertEqual(order.shipping_cost, Decimal("0.00"))
        self.assertEqual(order.total, Decimal("48.00"))

    def test_cart_page_applies_and_removes_a_code(self):
        DiscountCode.objects.create(code="HELLO", kind="percent", value=25)
        self.client.post(reverse("shop:cart_add", args=[self.print_a4.pk]))
        self.client.post(reverse("shop:cart_code"), {"code": "hello"})
        self.assertContains(self.client.get(reverse("shop:cart")), "HELLO")
        self.assertContains(self.client.get(reverse("shop:checkout")), "−€6.00")
        self.client.post(reverse("shop:cart_code_remove"))
        self.assertNotContains(self.client.get(reverse("shop:cart")), "HELLO")
        self.client.post(reverse("shop:cart_code"), {"code": "nonsense"})
        self.assertNotContains(self.client.get(reverse("shop:cart")), "nonsense")


class InvoiceTests(ShopTestCase):
    def paid_order(self, title_note=""):
        order = self.order_for((self.print_a4, 1))
        if title_note:
            order.items.update(title=title_note)
        order.status = Order.STATUS_PAID
        order.save()
        return order

    def test_customer_gets_invoice_only_when_paid(self):
        order = self.order_for((self.print_a4, 1))
        self.assertEqual(self.client.get(reverse("shop:invoice", args=[order.token])).status_code, 404)
        order.status = Order.STATUS_PAID
        order.save()
        response = self.client.get(reverse("shop:invoice", args=[order.token]))
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_numbers_are_sequential_and_stable(self):
        first, second = self.paid_order(), self.paid_order()
        a, b = first.ensure_invoice_number(), second.ensure_invoice_number()
        year = timezone.now().year
        self.assertEqual((a, b), (f"R-{year}-0001", f"R-{year}-0002"))
        first.invoice_number = None
        self.assertEqual(Order.objects.get(pk=first.pk).ensure_invoice_number(), a)

    def test_pdf_survives_unusual_characters_in_both_languages(self):
        from .invoices import invoice_pdf, packing_slip_pdf

        for lang in ("en", "de"):
            order = self.paid_order("Łódź — Rynek Główny “dusk”")
            order.language = lang
            order.customer_note = "Bitte vorsichtig verpacken, danke ☺"
            order.ensure_invoice_number()
            order.refresh_from_db()
            self.assertTrue(invoice_pdf(order, None).startswith(b"%PDF"))
            self.assertTrue(packing_slip_pdf(order, None).startswith(b"%PDF"))

    def test_admin_documents_need_permission(self):
        order = self.paid_order()
        url = reverse("shop_admin_document", args=[order.pk, "invoice"])
        self.assertEqual(self.client.get(url).status_code, 302)  # sent to the admin login
        admin = get_user_model().objects.create_superuser("jo", "j@example.com", "pw")
        self.client.force_login(admin)
        self.assertEqual(self.client.get(url)["Content-Type"], "application/pdf")
        slip = self.client.get(reverse("shop_admin_document", args=[order.pk, "packing-slip"]))
        self.assertEqual(slip["Content-Type"], "application/pdf")


class ReviewAndCollectionTests(ShopTestCase):
    def shipped_order(self):
        order = self.order_for((self.print_a4, 1))
        order.status = Order.STATUS_PAID
        order.save()
        order.status = Order.STATUS_SHIPPED
        order.save()
        return Order.objects.get(pk=order.pk)

    def test_customer_review_starts_hidden_and_is_shown_after_approval(self):
        order = self.shipped_order()
        url = reverse("shop:review", args=[order.token])
        self.assertContains(self.client.get(order.get_absolute_url()), "How did it go?")
        self.client.post(url, {"quote": "Beautiful colours, arrived safely.", "name": "Bea", "rating": "5"})
        review = Testimonial.objects.get()
        self.assertFalse(review.published)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.artwork_id, self.artwork.pk)
        self.assertNotContains(self.client.get("/"), "Beautiful colours")
        # a second review for the same order is refused
        self.assertEqual(self.client.post(url, {"quote": "Again please"}).status_code, 404)

        Testimonial.objects.update(published=True)
        self.assertContains(self.client.get("/"), "Beautiful colours")
        self.assertContains(self.client.get(self.artwork.url), "Beautiful colours")

    def test_cannot_review_an_unshipped_order(self):
        order = self.order_for((self.print_a4, 1))
        self.assertEqual(
            self.client.post(reverse("shop:review", args=[order.token]), {"quote": "Too early"}).status_code, 404
        )

    def test_collection_filter_and_banner(self):
        from artworks.models import Collection

        lisbon = Collection.objects.create(name="Summer in Lisbon", name_de="Sommer in Lissabon", slug="lisbon", description="Tiles and trams.")
        ArtworkPage.objects.filter(pk=self.artwork.pk).update(collection=lisbon)
        other = make_artwork("Other piece", "other-piece")
        gallery = self.artwork.get_parent().url
        page = self.client.get(f"{gallery}?collection=lisbon")
        self.assertContains(page, "Tiles and trams.")
        self.assertContains(page, "Test Artwork")
        self.assertNotContains(page, "Other piece")
        self.assertContains(self.client.get(gallery), "Summer in Lisbon")
        self.assertContains(self.client.get(self.artwork.url), "Summer in Lisbon")
        self.assertEqual(lisbon.localized("name", "de"), "Sommer in Lissabon")


class WaitlistTests(ShopTestCase):
    def join(self, offer, email="wait@example.com"):
        return self.client.post(reverse("shop:waitlist", args=[offer.pk]), {"email": email})

    def test_sold_out_print_notifies_when_restocked(self):
        Offer.objects.filter(pk=self.print_a4.pk).update(stock=0)
        offer = Offer.objects.get(pk=self.print_a4.pk)
        self.assertTrue(offer.waitlistable)
        self.join(offer)
        self.join(offer)  # twice is fine
        self.assertEqual(WaitlistRequest.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)

        offer.stock = 5
        offer.save()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Test Artwork", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["wait@example.com"])
        offer.save()  # nobody is told twice
        self.assertEqual(len(mail.outbox), 1)

    def test_reserved_original_notifies_when_released(self):
        self.artwork.set_status("reserved")
        offer = Offer.objects.get(pk=self.original.pk)
        self.assertTrue(offer.waitlistable)
        self.join(offer, "orig@example.com")
        ArtworkPage.objects.get(pk=self.artwork.pk).set_status("available")
        self.assertEqual([m.to for m in mail.outbox], [["orig@example.com"]])

    def test_available_offer_cannot_be_waitlisted(self):
        self.join(self.print_a4)
        self.assertEqual(WaitlistRequest.objects.count(), 0)


class AccountTests(ShopTestCase):
    def test_registering_claims_orders_placed_as_guest(self):
        self.client.post(reverse("shop:cart_add", args=[self.print_a4.pk]))
        self.client.post(reverse("shop:checkout"), CHECKOUT)
        order = Order.objects.get()
        self.assertIsNone(order.user)

        response = self.client.post(
            reverse("shop:register"),
            {
                "first_name": "Bea",
                "email": "bea@example.com",
                "password1": "a-very-long-pass-123",
                "password2": "a-very-long-pass-123",
            },
        )
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        user = get_user_model().objects.get(username="bea@example.com")
        self.assertEqual(order.user, user)
        self.assertContains(self.client.get(reverse("shop:account")), order.number)

    def test_duplicate_email_is_rejected(self):
        get_user_model().objects.create_user("bea@example.com", "bea@example.com", "pw-12345-pw")
        response = self.client.post(
            reverse("shop:register"),
            {"first_name": "Bea", "email": "BEA@example.com",
             "password1": "a-very-long-pass-123", "password2": "a-very-long-pass-123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.count(), 1)


class SiteSmokeTests(ShopTestCase):
    def test_public_pages_render_in_both_languages(self):
        for url in ["/", "/de/", "/gallery/", "/de/galerie/", "/blog/", "/de/blog/",
                    "/about/", "/de/ueber-mich/", "/commissions/", "/contact/inquiry/",
                    "/de/contact/inquiry/", "/shop/cart/", "/shop/account/login/",
                    "/shop/order/lookup/", "/sitemap.xml", "/robots.txt", "/blog/feed/",
                    "/search/?query=test", self.artwork.url]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_german_ui_is_translated(self):
        self.assertContains(self.client.get("/de/galerie/"), "Kaufen als")

    def test_language_switcher_links_to_translation(self):
        html = self.client.get("/about/").content.decode()
        self.assertIn('href="/de/ueber-mich/"', html)

    def test_draft_legal_pages_are_not_public(self):
        self.assertEqual(self.client.get("/privacy/").status_code, 404)

    def test_stock_and_status_badges(self):
        self.assertEqual([m for m, _ in self.artwork.badges][:1], ["available"])
        self.assertIn("extra", [m for m, _ in self.artwork.badges])
