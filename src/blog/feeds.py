from django.contrib.syndication.views import Feed
from django.utils import translation
from django.utils.translation import gettext as _

from wagtail.models import Locale

from .models import BlogPostPage


class LatestPostsFeed(Feed):
    """RSS feed of the newest blog posts in the visitor's language."""

    def title(self):
        return _("Johanna L — from the sketchbook")

    def link(self):
        return "/blog/"

    def description(self):
        return _("Notes on watercolour, travelling and making art.")

    def items(self):
        locale = Locale.objects.filter(language_code=translation.get_language()).first()
        posts = BlogPostPage.objects.live().public().order_by("-date")
        if locale:
            posts = posts.filter(locale=locale)
        return posts[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.intro

    def item_link(self, item):
        return item.url

    def item_pubdate(self, item):
        from datetime import datetime

        return datetime.combine(item.date, datetime.min.time())
