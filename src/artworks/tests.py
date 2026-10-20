from django.core.management import call_command
from django.test import TestCase

from shop.tests import make_artwork

from .models import ArtworkPage
from .places import layout, locate


class PlacesTests(TestCase):
    def test_places_are_found_by_english_or_german_name(self):
        self.assertEqual(locate("Kraków"), locate("krakow"))
        self.assertEqual(locate("Lake Garda, Italy"), locate("Gardasee"))
        self.assertEqual(locate("Old town of Prague"), locate("Prague"))
        self.assertIsNone(locate("Nowhereville"))

    def test_layout_fits_the_sheet(self):
        points = [locate(p) for p in ("Lisbon", "Prague", "Venice", "Braunschweig")]
        for x, y in layout(points):
            self.assertTrue(0 < x < 1000 and 0 < y < 560)
        self.assertEqual(layout([(50, 10)]), [(500.0, 280.0)])


class ArtworkPageFeatureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_site", verbosity=0)
        cls.a = make_artwork("Rooftops", "rooftops")
        cls.b = make_artwork("Canal", "canal")
        ArtworkPage.objects.filter(pk=cls.a.pk).update(place="Prague", width_cm=30, height_cm=40)
        ArtworkPage.objects.filter(pk=cls.b.pk).update(place="Venice")

    def test_homepage_shows_the_sketchbook_map_and_gallery_place_filter(self):
        home = self.client.get("/")
        self.assertContains(home, 'id="map"')
        self.assertContains(home, "Prague")
        gallery = self.client.get(f"{self.a.get_parent().url}?place=Prague")
        self.assertContains(gallery, "Rooftops")
        self.assertNotContains(gallery, "Canal")

    def test_map_needs_two_known_places(self):
        ArtworkPage.objects.filter(pk=self.b.pk).update(place="Nowhereville")
        self.assertNotContains(self.client.get("/"), 'id="map"')

    def test_wall_preview_needs_a_size(self):
        self.assertContains(self.client.get(self.a.url), "data-wall-open")
        self.assertNotContains(self.client.get(self.b.url), "data-wall-open")
