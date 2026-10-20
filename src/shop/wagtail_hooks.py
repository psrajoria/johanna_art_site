from django.db.models import Count, Sum
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from wagtail import hooks
from wagtail.models import Locale
from wagtail.admin.ui.components import Component
from wagtail.permission_policies import ModelPermissionPolicy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from artworks.models import Offer
from home.models import StandardPage
from contact.models import Inquiry

from .cart import shop_settings
from .models import DiscountCode, Order, ShippingRate, WaitlistRequest


class NoAddPermissionPolicy(ModelPermissionPolicy):
    """Orders are created by customers at checkout, never by hand."""

    def user_has_permission(self, user, action):
        if action == "add":
            return False
        return super().user_has_permission(user, action)


class OrderViewSet(SnippetViewSet):
    model = Order
    icon = "form"
    menu_label = "Orders"
    menu_order = 100
    list_display = ["number", "customer_name", "status_label", "total", "created_at"]
    list_filter = ["status", "payment_method"]
    search_fields = ["number", "name", "email"]
    ordering = ["-created_at"]

    @property
    def permission_policy(self):
        return NoAddPermissionPolicy(self.model)


class ShippingRateViewSet(SnippetViewSet):
    model = ShippingRate
    icon = "globe"
    menu_label = "Shipping prices"
    menu_order = 200
    list_display = ["zone", "shipping_class", "price", "delivery_estimate"]


class WaitlistViewSet(SnippetViewSet):
    model = WaitlistRequest
    icon = "time"
    menu_label = "Waiting list"
    menu_order = 150
    list_display = ["email", "artwork_title", "status_label", "created_at"]
    list_filter = ["notified_at"]
    search_fields = ["email"]
    list_export = ["email", "language", "created_at", "notified_at"]

    @property
    def permission_policy(self):
        return NoAddPermissionPolicy(self.model)


class DiscountCodeViewSet(SnippetViewSet):
    model = DiscountCode
    icon = "tag"
    menu_label = "Discount codes & gift cards"
    menu_order = 160
    list_display = ["code", "summary", "uses_label", "valid_until", "active"]
    list_filter = ["kind", "active"]
    search_fields = ["code", "note"]


class ShopGroup(SnippetViewSetGroup):
    menu_label = "Shop"
    menu_icon = "tag"
    menu_order = 200
    items = (OrderViewSet, WaitlistViewSet, DiscountCodeViewSet, ShippingRateViewSet)


class InquiryViewSet(SnippetViewSet):
    model = Inquiry
    icon = "mail"
    menu_label = "Messages & commissions"
    menu_order = 210
    add_to_admin_menu = True
    list_display = ["number", "name", "type_label", "status_label", "created_at"]
    list_filter = ["status", "inquiry_type"]
    search_fields = ["number", "name", "email", "message"]
    ordering = ["-created_at"]

    @property
    def permission_policy(self):
        return NoAddPermissionPolicy(self.model)


register_snippet(ShopGroup)
register_snippet(InquiryViewSet)


class ShopSummaryPanel(Component):
    """Dashboard panel: what needs Johanna's attention right now."""

    order = 20

    def render_html(self, parent_context=None):
        paid_states = [
            Order.STATUS_PAID,
            Order.STATUS_PACKED,
            Order.STATUS_SHIPPED,
            Order.STATUS_COMPLETED,
        ]
        month_start = timezone.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        def orders_url(status):
            return reverse("wagtailsnippets_shop_order:list") + f"?status={status}"

        def inquiries_url(status):
            return reverse("wagtailsnippets_contact_inquiry:list") + f"?status={status}"

        to_ship = Order.objects.filter(
            status__in=[Order.STATUS_PAID, Order.STATUS_PACKED], has_physical=True
        ).count()
        open_requests = Inquiry.objects.filter(
            inquiry_type__in=[Inquiry.INQUIRY_COMMISSION, Inquiry.INQUIRY_PRINT],
            status__in=[
                Inquiry.STATUS_QUOTED,
                Inquiry.STATUS_ACCEPTED,
                Inquiry.STATUS_IN_PROGRESS,
            ],
        ).count()

        month = Order.objects.filter(
            status__in=paid_states, paid_at__gte=month_start
        ).aggregate(total=Sum("total"), count=Count("id"))

        low_stock = [
            offer
            for offer in Offer.objects.filter(
                is_active=True, stock__isnull=False, stock__lte=3
            )
            .exclude(kind=Offer.KIND_ORIGINAL)
            .select_related("artwork")[:8]
        ]

        shop = shop_settings()
        legal_drafts = StandardPage.objects.filter(
            show_in_footer=True, live=False, locale=Locale.get_default()
        )
        warnings = []
        if shop and shop.has_placeholder_details:
            warnings.append(
                {
                    "text": "Your PayPal / bank details are still placeholders — customers would be asked to pay the wrong account.",
                    "link": reverse("wagtailsettings:edit", args=["shop", "shopsettings"]),
                    "action": "Update shop settings",
                }
            )
        if shop and not shop.notification_address:
            warnings.append(
                {
                    "text": "No notification email is set, so you won't be told about new orders or messages.",
                    "link": reverse("wagtailsettings:edit", args=["shop", "shopsettings"]),
                    "action": "Add your email",
                }
            )
        if legal_drafts.exists():
            warnings.append(
                {
                    "text": "Legal pages are still drafts (%s). Fill in your details, have them checked, and publish them before launch."
                    % ", ".join(legal_drafts.values_list("title", flat=True)),
                    "link": reverse("wagtailadmin_explore", args=[legal_drafts.first().get_parent().pk]),
                    "action": "Open pages",
                }
            )
        context = {
            "warnings": warnings,
            "cards": [
                {
                    "label": "Awaiting payment",
                    "count": Order.objects.filter(
                        status=Order.STATUS_AWAITING
                    ).count(),
                    "url": orders_url(Order.STATUS_AWAITING),
                },
                {"label": "To ship", "count": to_ship, "url": orders_url(Order.STATUS_PAID)},
                {
                    "label": "New messages",
                    "count": Inquiry.objects.filter(status=Inquiry.STATUS_NEW).count(),
                    "url": inquiries_url(Inquiry.STATUS_NEW),
                },
                {
                    "label": "Open commissions",
                    "count": open_requests,
                    "url": reverse("wagtailsnippets_contact_inquiry:list"),
                },
            ],
            "month_total": month["total"] or 0,
            "month_count": month["count"] or 0,
            "items_sold": Offer.objects.aggregate(n=Sum("sold_count"))["n"] or 0,
            "low_stock": low_stock,
        }
        return render_to_string("shop/admin/summary_panel.html", context)


@hooks.register("construct_homepage_panels")
def add_shop_summary(request, panels):
    panels.insert(0, ShopSummaryPanel())
