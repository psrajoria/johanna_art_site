"""Tests that drive the Wagtail admin the way Johanna will."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

from artworks.models import Offer
from contact.models import Inquiry

from .models import Order
from .tests import ShopTestCase


class AdminTestCase(ShopTestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser("johanna", "j@example.com", "pw-admin-12345")
        self.client.force_login(self.admin)


class DashboardTests(AdminTestCase):
    def test_dashboard_shows_counters_and_placeholder_warning(self):
        self.order_for((self.print_a4, 1))
        response = self.client.get("/admin/")
        self.assertContains(response, "Your shop at a glance")
        self.assertContains(response, "Awaiting payment")
        self.assertContains(response, "placeholders")  # PayPal/IBAN are still dummies
        self.assertContains(response, "Legal pages are still drafts")
        self.assertContains(response, "No notification email")

    def test_admin_lists_render(self):
        for name in ("wagtailsnippets_shop_order:list", "wagtailsnippets_shop_shippingrate:list",
                     "wagtailsnippets_contact_inquiry:list"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_settings_pages_render(self):
        for model in ("shop/shopsettings", "home/sitesettings"):
            app, name = model.split("/")
            url = reverse("wagtailsettings:edit", args=[app, name])
            with self.subTest(model=model):
                self.assertEqual(self.client.get(url, follow=True).status_code, 200)

    def test_artwork_edit_page_with_offers_renders(self):
        response = self.client.get(reverse("wagtailadmin_pages:edit", args=[self.artwork.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ways to buy")


class OrderAdminTests(AdminTestCase):
    def test_orders_cannot_be_created_by_hand(self):
        response = self.client.get(reverse("wagtailsnippets_shop_order:add"))
        self.assertIn(response.status_code, (302, 403))

    def test_marking_paid_in_the_admin_updates_stock_counts_and_emails(self):
        order = self.order_for((self.print_a4, 2), (self.original, 1))
        mail.outbox.clear()
        url = reverse("wagtailsnippets_shop_order:edit", args=[order.pk])

        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, order.number)
        self.assertContains(page, "Test Artwork")  # items summary

        response = self.client.post(url, {
            "status": Order.STATUS_PAID,
            "payment_method": "paypal",
            "carrier": "", "tracking_number": "", "tracking_url": "", "internal_note": "paid via PayPal",
        })
        self.assertEqual(response.status_code, 302, response.content.decode()[:200] if response.status_code != 302 else "")

        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, Order.STATUS_PAID)
        self.assertIsNotNone(order.paid_at)
        self.print_a4.refresh_from_db()
        self.assertEqual(self.print_a4.sold_count, 2)
        self.artwork.refresh_from_db()
        self.assertEqual(self.artwork.status, "sold")
        self.assertEqual(len(mail.outbox), 1)

    def test_shipping_with_tracking_through_the_admin(self):
        order = self.order_for((self.print_a4, 1))
        order.status = Order.STATUS_PAID
        order.save()
        mail.outbox.clear()
        url = reverse("wagtailsnippets_shop_order:edit", args=[order.pk])
        self.client.post(url, {
            "status": Order.STATUS_SHIPPED, "payment_method": "paypal",
            "carrier": "DHL", "tracking_number": "JJD0001", "tracking_url": "", "internal_note": "",
        })
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_SHIPPED)
        self.assertIsNotNone(order.shipped_at)
        self.assertIn("JJD0001", mail.outbox[0].body)

    def test_reopening_a_cancelled_order_is_refused(self):
        order = self.order_for((self.print_a4, 1))
        order.status = Order.STATUS_CANCELLED
        order.save()
        url = reverse("wagtailsnippets_shop_order:edit", args=[order.pk])
        response = self.client.post(url, {
            "status": Order.STATUS_PAID, "payment_method": "paypal",
            "carrier": "", "tracking_number": "", "tracking_url": "", "internal_note": "",
        })
        self.assertEqual(response.status_code, 200)  # form re-shown with an error
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)


class InquiryTests(AdminTestCase):
    FORM = {
        "inquiry_type": "commission",
        "name": "Cleo Client",
        "email": "cleo@example.com",
        "message": "Could you paint our street?",
        "size_wanted": "A3",
    }

    def post_inquiry(self, **extra):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("contact:inquiry"), dict(self.FORM, **extra))

    def test_commission_request_is_saved_and_confirmed(self):
        self.client.logout()
        response = self.post_inquiry()
        inquiry = Inquiry.objects.get()
        self.assertRedirects(response, reverse("contact:thanks", args=[inquiry.token]))
        self.assertRegex(inquiry.number, r"^JL-C-\d{4}$")
        self.assertEqual(inquiry.language, "en")
        self.assertEqual([m.to for m in mail.outbox], [["cleo@example.com"]])

    def test_message_gets_a_different_number_prefix(self):
        self.post_inquiry(inquiry_type="general")
        self.assertTrue(Inquiry.objects.get().number.startswith("JL-M-"))

    def test_honeypot_and_rate_limit(self):
        self.post_inquiry(website="http://spam.example")
        self.assertFalse(Inquiry.objects.exists())

        from django.core.cache import cache
        cache.clear()
        for _ in range(6):
            self.post_inquiry()
        self.assertEqual(Inquiry.objects.count(), 5)
        cache.clear()

    def test_artwork_link_prefills_and_attaches(self):
        response = self.client.get(f"{reverse('contact:inquiry')}?artwork={self.artwork.pk}&type=print")
        self.assertContains(response, "Test Artwork")
        self.assertEqual(response.context["form"].initial["inquiry_type"], "print")
        self.client.post(reverse("contact:inquiry"), dict(self.FORM, artwork_id=self.artwork.pk, inquiry_type="print"))
        self.assertEqual(Inquiry.objects.get().artwork, self.artwork.page_ptr.specific)

    def test_status_page_is_private_by_token(self):
        self.post_inquiry()
        inquiry = Inquiry.objects.get()
        self.assertContains(self.client.get(reverse("contact:request_status", args=[inquiry.token])), inquiry.number)
        self.assertEqual(self.client.get(reverse("contact:request_status", args=["nope"])).status_code, 404)

    def test_moving_a_commission_forward_emails_the_customer(self):
        self.post_inquiry()
        inquiry = Inquiry.objects.get()
        mail.outbox.clear()
        url = reverse("wagtailsnippets_contact_inquiry:edit", args=[inquiry.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, {
                "status": "quoted", "inquiry_type": "commission", "artwork": "",
                "quote_amount": "180.00", "quote_message": "Happy to!", "carrier": "",
                "tracking_number": "", "internal_notes": "",
            })
        self.assertEqual(response.status_code, 302, response.content.decode()[:200] if response.status_code != 302 else "")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("180", mail.outbox[0].body)
        self.assertIn("Happy to!", mail.outbox[0].body)

        # a silent step ("replied") sends nothing
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            inquiry = Inquiry.objects.get(pk=inquiry.pk)
            inquiry.status = "replied"
            inquiry.save()
        self.assertEqual(len(mail.outbox), 0)

    def test_reference_photos_are_staff_only(self):
        self.post_inquiry()
        inquiry = Inquiry.objects.get()
        url = reverse("contact:reference", args=[inquiry.pk])
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)  # sent to log in
