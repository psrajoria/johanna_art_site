import json

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from shop.tests import make_artwork

from .models import Event, PageView
from . import reports

UA = {"HTTP_USER_AGENT": "Mozilla/5.0 (Windows NT 10.0) Chrome/120"}


class AnalyticsTests(TestCase):
    def setUp(self):
        from django.utils import translation

        translation.activate("en")

    @classmethod
    def setUpTestData(cls):
        call_command("seed_site", verbosity=0)
        cls.art = make_artwork("Roofs", "roofs")

    def test_visit_is_counted_once_without_personal_data(self):
        self.client.get(self.art.url, **UA)
        view = PageView.objects.get()
        self.assertEqual(view.kind, "artwork")
        self.assertEqual(view.title, "Roofs")
        self.assertEqual(len(view.visitor), 16)

    def test_bots_do_not_track_and_staff_are_ignored(self):
        self.client.get(self.art.url, HTTP_USER_AGENT="Googlebot/2.1")
        self.client.get(self.art.url, HTTP_DNT="1", **UA)
        admin = get_user_model().objects.create_superuser("jo", "j@example.com", "pw")
        self.client.force_login(admin)
        self.client.get(self.art.url, **UA)
        self.assertEqual(PageView.objects.count(), 0)

    def test_heart_beacon_and_report(self):
        for name in ("like", "like", "unlike"):
            self.client.post(
                "/a/e/", json.dumps({"name": name, "page": self.art.pk}),
                content_type="application/json", **UA,
            )
        # unknown names from a browser are ignored
        self.client.post("/a/e/", json.dumps({"name": "order"}), content_type="application/json", **UA)
        self.assertEqual(Event.objects.count(), 3)
        self.client.get(self.art.url, **UA)
        data = reports.build(7)
        self.assertEqual(data["hearts"], 1)
        self.assertEqual(data["artworks"][0]["hearts"], 1)
        self.assertEqual(data["loved"][0]["title"], "Roofs")

    def test_insights_page_for_staff(self):
        admin = get_user_model().objects.create_superuser("jo", "j@example.com", "pw")
        self.client.force_login(admin)
        response = self.client.get("/admin/insights/")
        self.assertContains(response, "Insights")
        self.assertContains(self.client.get("/admin/"), "Your visitors this week")


class DigestTests(TestCase):
    def setUp(self):
        from django.utils import translation

        translation.activate("en")

    @classmethod
    def setUpTestData(cls):
        call_command("seed_site", verbosity=0)

    def test_digest_lists_what_needs_attention(self):
        from analytics.management.commands.admin_digest import build_digest
        from contact.models import Inquiry

        Inquiry.objects.create(name="A", email="a@example.com", message="Hi", inquiry_type="general")
        body, urgent = build_digest()
        self.assertTrue(urgent)
        self.assertIn("1 new message", body)

    def test_digest_email_goes_to_the_notification_address(self):
        from django.core import mail
        from shop.models import ShopSettings
        from wagtail.models import Site

        shop = ShopSettings.for_site(Site.objects.get(is_default_site=True))
        shop.notify_email = "jo@example.com"
        shop.save()
        call_command("admin_digest", verbosity=0)
        self.assertEqual(mail.outbox[0].to, ["jo@example.com"])
        self.assertIn("Good morning", mail.outbox[0].body)

    def test_daily_tasks_run_each_job_once_per_day(self):
        from unittest import mock

        from analytics.models import TaskRun

        with mock.patch("analytics.management.commands.daily_tasks.call_command") as run, mock.patch(
            "analytics.management.commands.daily_tasks.current_hour", return_value=12
        ):
            call_command("daily_tasks", verbosity=0)
            first = run.call_count
            call_command("daily_tasks", verbosity=0)
        self.assertEqual(first, 3)
        self.assertEqual(run.call_count, 3)  # nothing repeated
        self.assertEqual(TaskRun.objects.count(), 3)
