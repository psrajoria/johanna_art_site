import json

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from shop.tests import make_artwork

from .models import Event, PageView
from . import reports

UA = {"HTTP_USER_AGENT": "Mozilla/5.0 (Windows NT 10.0) Chrome/120"}


class AnalyticsTests(TestCase):
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
