import math
import re

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models
from django.utils import timezone
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import Tag, TaggedItemBase

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtail.search import index

from home.blocks import body_blocks


class BlogIndexPage(Page):
    """The blog landing page. Posts are created as children of this page."""

    intro = RichTextField(
        blank=True,
        help_text="Short introduction shown at the top of the blog.",
    )

    max_count_per_parent = 1
    parent_page_types = ["home.HomePage"]
    subpage_types = ["blog.BlogPostPage"]

    content_panels = Page.content_panels + [FieldPanel("intro")]

    PAGE_SIZE = 9

    def get_context(self, request):
        context = super().get_context(request)

        posts = (
            BlogPostPage.objects.live().public().descendant_of(self).order_by("-date")
        )

        selected_tag = request.GET.get("tag")
        if selected_tag:
            posts = posts.filter(tags__slug=selected_tag)

        paginator = Paginator(posts, self.PAGE_SIZE)
        try:
            page_obj = paginator.page(request.GET.get("page", 1))
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        used_tags = (
            Tag.objects.filter(
                blog_blogposttag_items__content_object__in=BlogPostPage.objects.live()
                .public()
                .descendant_of(self)
            )
            .distinct()
            .order_by("name")
        )

        query = request.GET.copy()
        query.pop("page", None)

        context["posts"] = page_obj
        context["tags"] = used_tags
        context["selected_tag"] = selected_tag
        context["query_string"] = query.urlencode()
        return context


class BlogPostTag(TaggedItemBase):
    content_object = ParentalKey(
        "blog.BlogPostPage",
        related_name="tagged_items",
        on_delete=models.CASCADE,
    )


class BlogPostPage(Page):
    date = models.DateField(default=timezone.localdate)

    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Large image at the top of the post and on blog cards.",
    )

    intro = models.CharField(
        max_length=300,
        blank=True,
        help_text="One or two sentences shown on blog cards and in search results.",
    )

    body = StreamField(body_blocks(), blank=True)

    tags = ClusterTaggableManager(through=BlogPostTag, blank=True)

    related_artwork = models.ForeignKey(
        "artworks.ArtworkPage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional: link this post to an artwork it talks about.",
    )

    parent_page_types = ["blog.BlogIndexPage"]
    subpage_types = []

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("date"), FieldPanel("tags"), FieldPanel("related_artwork")],
            heading="Post details",
        ),
        FieldPanel("hero_image"),
        FieldPanel("intro"),
        FieldPanel("body"),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
    ]

    @property
    def reading_minutes(self):
        text = " ".join(
            re.sub(r"<[^>]+>", " ", str(block.value)) for block in self.body
        )
        return max(1, math.ceil(len(text.split()) / 200))

    def get_context(self, request):
        context = super().get_context(request)
        context["more_posts"] = list(
            BlogPostPage.objects.live()
            .public()
            .filter(locale=self.locale)
            .exclude(pk=self.pk)
            .order_by("-date")[:2]
        )
        return context
