from django.utils.html import format_html

from wagtail.admin.panels import Panel


class ReadOnlyHTMLPanel(Panel):
    """
    Shows a computed, read-only value (a property or method on the model that
    returns HTML-safe text) inside an edit form. Wagtail's own read-only
    FieldPanel only works for real database fields.
    """

    def __init__(self, attr, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attr = attr

    def clone_kwargs(self):
        kwargs = super().clone_kwargs()
        kwargs["attr"] = self.attr
        return kwargs

    class BoundPanel(Panel.BoundPanel):
        def render_html(self, parent_context=None):
            value = getattr(self.instance, self.panel.attr, "")
            if callable(value):
                value = value()
            return format_html('<div class="w-field__wrapper">{}</div>', value or "—")
