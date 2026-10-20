import json
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from wagtail.models import Site

from home.models import HomePage, InstagramPost, SiteSettings


class InstagramTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_site", verbosity=0)
        cls.site = Site.objects.get(is_default_site=True)

    def test_handle_and_footer_link(self):
        settings_obj = SiteSettings.for_site(self.site)
        self.assertEqual(settings_obj.instagram_handle, "@from.j2l")
        response = self.client.get("/")
        self.assertContains(response, "https://www.instagram.com/from.j2l/")
        self.assertContains(response, "Follow @from.j2l")

    def test_strip_without_posts_still_offers_follow_button(self):
        self.assertEqual(HomePage.objects.first().instagram_tiles(), [])

    def test_fetch_command_stores_posts_and_refreshes_token(self):
        settings_obj = SiteSettings.for_site(self.site)
        settings_obj.instagram_access_token = "old"
        settings_obj.save()
        calls = []

        def fake_get(url, timeout=20):
            calls.append(url)
            if "refresh_access_token" in url:
                return json.dumps({"access_token": "new"}).encode()
            if "/me/media" in url:
                return json.dumps({"data": [{
                    "id": "1", "media_type": "IMAGE", "media_url": "https://cdn/x.jpg",
                    "permalink": "https://www.instagram.com/p/abc/", "caption": "Rain in Lisbon",
                    "timestamp": "2026-10-01T10:00:00+0000",
                }]}).encode()
            return b"fake-image-bytes"

        with mock.patch("home.management.commands.fetch_instagram._get", fake_get):
            call_command("fetch_instagram", verbosity=0)
            call_command("fetch_instagram", verbosity=0)  # second run adds nothing

        self.assertEqual(InstagramPost.objects.count(), 1)
        settings_obj.refresh_from_db()
        self.assertEqual(settings_obj.instagram_access_token, "new")
        tiles = HomePage.objects.first().instagram_tiles()
        self.assertEqual(tiles[0]["caption"], "Rain in Lisbon")
        InstagramPost.objects.first().image.delete(save=False)

    def test_hand_picked_posts_show_in_the_strip(self):
        from wagtail.images.models import Image
        from wagtail.images.tests.utils import get_test_image_file

        from home.models import HomePageInstagramPost

        home = HomePage.objects.filter(locale__language_code="en").first()
        image = Image.objects.create(title="Post", file=get_test_image_file())
        HomePageInstagramPost.objects.create(
            page=home, image=image, link="https://www.instagram.com/p/xyz/", caption="Morning wash"
        )
        response = self.client.get("/")
        self.assertContains(response, "https://www.instagram.com/p/xyz/")
        self.assertContains(response, "Morning wash")
