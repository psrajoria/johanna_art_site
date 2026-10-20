from django.utils.translation import gettext_lazy as _

import re

from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock


class ImageWithCaptionBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    caption = blocks.CharBlock(required=False)
    wide = blocks.BooleanBlock(
        required=False,
        default=False,
        label=_("Show wide"),
        help_text=_("Stretch this image wider than the text column."),
    )

    class Meta:
        icon = "image"
        label = _("Image")
        template = "blocks/image_block.html"


YOUTUBE_ID = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/))([\w-]{11})")


class VideoBlock(blocks.StructBlock):
    """A time-lapse or studio clip: an uploaded video file, or a YouTube link that only loads on click."""

    poster = ImageChooserBlock(label=_("Cover image"))
    video_file = DocumentChooserBlock(
        required=False,
        label=_("Video file (MP4)"),
        help_text=_("Upload an .mp4 under Documents and choose it here. Keep it short (under 50 MB)."),
    )
    youtube_url = blocks.URLBlock(
        required=False,
        label=_("or YouTube link"),
        help_text=_("Only used when no video file is chosen. Visitors only contact YouTube when they press play."),
    )
    caption = blocks.CharBlock(required=False)

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        match = YOUTUBE_ID.search(value.get("youtube_url") or "")
        context["youtube_id"] = match.group(1) if match else ""
        return context

    class Meta:
        icon = "media"
        label = _("Video")
        template = "blocks/video_block.html"


class QuoteBlock(blocks.StructBlock):
    text = blocks.TextBlock()
    attribution = blocks.CharBlock(required=False)

    class Meta:
        icon = "openquote"
        label = _("Quote")
        template = "blocks/quote_block.html"


class ButtonBlock(blocks.StructBlock):
    text = blocks.CharBlock()
    page = blocks.PageChooserBlock(required=False)
    url = blocks.URLBlock(
        required=False,
        help_text=_("Only used when no page is chosen above."),
    )

    class Meta:
        icon = "link"
        label = _("Button")
        template = "blocks/button_block.html"


class FAQItemBlock(blocks.StructBlock):
    question = blocks.CharBlock()
    answer = blocks.RichTextBlock(features=["bold", "italic", "link", "ul", "ol"])


class FAQBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False)
    items = blocks.ListBlock(FAQItemBlock())

    class Meta:
        icon = "help"
        label = _("Questions & answers")
        template = "blocks/faq_block.html"


class PriceRowBlock(blocks.StructBlock):
    label = blocks.CharBlock(help_text=_("e.g. A5 sketch, A4 watercolour"))
    price = blocks.CharBlock(help_text=_("e.g. from 60 €"))
    note = blocks.CharBlock(required=False)


class PriceListBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False)
    rows = blocks.ListBlock(PriceRowBlock())

    class Meta:
        icon = "list-ul"
        label = _("Price list")
        template = "blocks/price_list_block.html"


class ProcessStepBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    text = blocks.TextBlock()


class StepsBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False)
    steps = blocks.ListBlock(ProcessStepBlock())

    class Meta:
        icon = "order"
        label = _("Numbered steps")
        template = "blocks/steps_block.html"


def body_blocks():
    """Content blocks shared by generic pages and blog posts."""
    return [
        ("heading", blocks.CharBlock(
            icon="title", label=_("Heading"), template="blocks/heading_block.html"
        )),
        ("paragraph", blocks.RichTextBlock(
            icon="pilcrow",
            label=_("Text"),
            features=[
                "h3", "h4", "bold", "italic", "link", "ul", "ol", "hr", "blockquote",
            ],
        )),
        ("image", ImageWithCaptionBlock()),
        ("quote", QuoteBlock()),
        ("button", ButtonBlock()),
        ("video", VideoBlock()),
    ]


def page_blocks():
    return body_blocks() + [
        ("faq", FAQBlock()),
        ("price_list", PriceListBlock()),
        ("steps", StepsBlock()),
    ]
