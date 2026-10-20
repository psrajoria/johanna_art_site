from wagtail.permission_policies import ModelPermissionPolicy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from shop.wagtail_hooks import NoAddPermissionPolicy

from .models import Campaign, Subscriber


class SubscriberViewSet(SnippetViewSet):
    model = Subscriber
    icon = "group"
    menu_label = "Subscribers"
    list_display = ["email", "status_label", "language", "subscribed_at"]
    list_filter = ["confirmed", "language"]
    search_fields = ["email"]
    list_export = ["email", "language", "confirmed", "subscribed_at", "confirmed_at", "unsubscribed_at"]
    inspect_view_enabled = True

    @property
    def permission_policy(self):
        # people subscribe themselves; Johanna can look, export and delete (GDPR) but not invent
        return NoAddPermissionPolicy(self.model)


class CampaignViewSet(SnippetViewSet):
    model = Campaign
    icon = "mail"
    menu_label = "Newsletters"
    list_display = ["subject", "status_label", "created_at"]
    search_fields = ["subject"]


class NewsletterGroup(SnippetViewSetGroup):
    menu_label = "Newsletter"
    menu_icon = "mail"
    menu_order = 220
    items = (CampaignViewSet, SubscriberViewSet)


register_snippet(NewsletterGroup)
