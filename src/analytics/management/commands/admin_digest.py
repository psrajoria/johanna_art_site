"""A short morning email for Johanna: what needs her attention today."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count, F
from django.utils import timezone

from analytics.models import Event, PageView
from artworks.models import Offer
from contact.models import Inquiry
from newsletter.models import Subscriber
from shop.emails import notify_address, site_base_url
from shop.models import Order, WaitlistRequest


def build_digest():
    now = timezone.now()
    yesterday = timezone.localdate() - timedelta(days=1)
    lines = []

    to_pay = Order.objects.filter(status="awaiting_payment").count()
    to_ship = Order.objects.filter(status__in=["paid", "packed"], has_physical=True).count()
    new_msgs = Inquiry.objects.filter(status="new").count()
    open_requests = Inquiry.objects.filter(
        inquiry_type__in=["commission", "print"], status__in=["quoted", "accepted", "in_progress"]
    ).count()

    if to_ship:
        lines.append(f"- {to_ship} order(s) to pack and ship")
    if to_pay:
        lines.append(f"- {to_pay} order(s) waiting for payment")
    if new_msgs:
        lines.append(f"- {new_msgs} new message(s) or request(s) to answer")
    if open_requests:
        lines.append(f"- {open_requests} commission(s) in progress")

    low = Offer.objects.filter(is_active=True, stock__isnull=False, stock__lte=2).select_related("artwork")
    for offer in low[:5]:
        lines.append(f"- Running low: {offer.artwork.title} ({offer.short_label()}): {offer.stock} left")

    waiting = WaitlistRequest.objects.filter(notified_at__isnull=True).count()
    if waiting:
        lines.append(f"- {waiting} person(s) on the waiting list")
    new_subs = Subscriber.objects.filter(confirmed=True, confirmed_at__gte=now - timedelta(days=1)).count()
    if new_subs:
        lines.append(f"- {new_subs} new newsletter subscriber(s)")

    visitors = PageView.objects.filter(day=yesterday).values("visitor").distinct().count()
    hearts = Event.objects.filter(day=yesterday, name="like").count()
    carts = Event.objects.filter(day=yesterday, name__in=["add_to_cart", "buy_now"]).count()
    top = (
        PageView.objects.filter(day=yesterday, kind="artwork")
        .values("title").annotate(n=Count("id")).order_by("-n").first()
    )
    stats = f"Yesterday: {visitors} visitor(s), {hearts} heart(s), {carts} add-to-cart."
    if top:
        stats += f" Most looked at: {top['title']}."

    if not lines:
        lines.append("- Nothing needs your attention. Enjoy painting!")
    body = "Good morning!\n\n" + "\n".join(lines) + "\n\n" + stats + f"\n\nYour admin: {site_base_url()}/admin/\n"
    return body, bool(to_ship or to_pay or new_msgs or open_requests)


class Command(BaseCommand):
    help = "Email the morning summary to the shop notification address."

    def handle(self, *args, **options):
        from django.core.mail import EmailMessage

        to = notify_address()
        if not to:
            self.stdout.write("No notification email set - nothing sent.")
            return
        body, _urgent = build_digest()
        EmailMessage("Your studio this morning", body, to=[to]).send()
        self.stdout.write(f"Digest sent to {to}.")
