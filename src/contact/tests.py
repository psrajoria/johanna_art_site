from decimal import Decimal

from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from wagtail.images.models import Image
from wagtail.images.tests.utils import get_test_image_file

from shop.models import ShopSettings, size_estimates

from .models import Inquiry, InquiryUpdate

FORM = {
    "inquiry_type": "commission",
    "name": "Cleo Customer",
    "email": "cleo@example.com",
    "message": "A small painting of our street, please.",
    "size_wanted": "A4",
}


class ContactTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_site", verbosity=0)

    def setUp(self):
        cache.clear()

    def commission(self, **fields):
        data = dict(name="Cleo", email="cleo@example.com", message="Hi", inquiry_type="commission", language="en")
        data.update(fields)
        return Inquiry.objects.create(**data)


class InquiryFlowTests(ContactTestCase):
    def test_commission_request_end_to_end(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("contact:inquiry"), FORM)
        inquiry = Inquiry.objects.get()
        self.assertRedirects(response, reverse("contact:thanks", args=[inquiry.token]))
        self.assertTrue(inquiry.number.startswith("JL-C-"))
        self.assertEqual(mail.outbox[0].to, ["cleo@example.com"])
        self.assertContains(self.client.get(inquiry.get_status_url()), inquiry.number)

    def test_german_visitor_gets_german_mail(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/de/contact/inquiry/", FORM)
        self.assertIn("angekommen", mail.outbox[0].subject)

    def test_status_change_sends_the_right_email_once(self):
        inquiry = self.commission()
        inquiry = Inquiry.objects.get(pk=inquiry.pk)
        inquiry.status = "quoted"
        inquiry.quote_amount = Decimal("120")
        with self.captureOnCommitCallbacks(execute=True):
            inquiry.save()
            inquiry.save()  # saving again without a change sends nothing more
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("120", mail.outbox[0].body)

    def test_status_page_is_private_by_token(self):
        self.assertEqual(self.client.get("/contact/request/not-a-real-token/").status_code, 404)


class CommissionToolsTests(ContactTestCase):
    def test_quote_email_mentions_the_deposit(self):
        inquiry = Inquiry.objects.get(pk=self.commission().pk)
        inquiry.status = "quoted"
        inquiry.quote_amount = Decimal("200")
        inquiry.deposit_amount = Decimal("60")
        with self.captureOnCommitCallbacks(execute=True):
            inquiry.save()
        body = mail.outbox[0].body
        self.assertIn("deposit of EUR 60", body)
        self.assertIn("remaining EUR 140", body)
        self.assertEqual(inquiry.balance_due, Decimal("140"))

    def test_progress_photo_is_emailed_once_and_shown_to_the_customer(self):
        inquiry = Inquiry.objects.get(pk=self.commission().pk)
        image = Image.objects.create(title="wip", file=get_test_image_file())
        inquiry.updates.add(InquiryUpdate(image=image, note="First wash on the sky"))
        with self.captureOnCommitCallbacks(execute=True):
            inquiry.save()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("First wash on the sky", mail.outbox[0].body)

        with self.captureOnCommitCallbacks(execute=True):
            Inquiry.objects.get(pk=inquiry.pk).save()
        self.assertEqual(len(mail.outbox), 1)  # never repeated

        page = self.client.get(inquiry.get_status_url())
        self.assertContains(page, "First wash on the sky")
        self.assertContains(page, "Progress")

    def test_update_can_be_added_without_emailing(self):
        inquiry = Inquiry.objects.get(pk=self.commission().pk)
        inquiry.updates.add(InquiryUpdate(note="Quiet note", notify_customer=False))
        with self.captureOnCommitCallbacks(execute=True):
            inquiry.save()
        self.assertEqual(mail.outbox, [])

    def test_finished_email_asks_for_the_balance(self):
        inquiry = Inquiry.objects.get(pk=self.commission(quote_amount=Decimal("100"), deposit_amount=Decimal("30")).pk)
        inquiry.status = "finished"
        with self.captureOnCommitCallbacks(execute=True):
            inquiry.save()
        self.assertIn("remaining balance of EUR 70", mail.outbox[0].body)

    def test_size_picker_prices(self):
        settings_obj = ShopSettings.objects.first()
        sizes = {s["label"]: s["price"] for s in size_estimates(settings_obj)}
        self.assertEqual(sizes["A4"], 50)  # 30 base + 6.2 x 3.5 = 51.8 -> nearest 5
        self.assertLess(sizes["A5"], sizes["A4"])
        self.assertLess(sizes["A4"], sizes["A3"])
        self.assertTrue(all(price % 5 == 0 for price in sizes.values()))
        settings_obj.commission_base_price = 0
        settings_obj.commission_price_per_100cm2 = 0
        self.assertEqual(size_estimates(settings_obj), [])

    def test_form_shows_the_size_picker(self):
        response = self.client.get(reverse("contact:inquiry"))
        self.assertContains(response, "data-size-picker")
        self.assertContains(response, 'data-size-text="A4')
