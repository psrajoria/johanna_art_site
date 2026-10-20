from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import translation
from django.utils.translation import gettext as _

from analytics.models import Event
from analytics.tracking import track
from artworks.models import ArtworkPage

from . import emails
from .forms import InquiryForm
from .models import Inquiry

# At most this many messages per visitor (by IP) within the window.
RATE_LIMIT = 5
RATE_WINDOW_SECONDS = 60 * 60


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")


def _rate_limited(request):
    key = f"inquiry-rate-{_client_ip(request)}"
    count = cache.get(key, 0)
    if count >= RATE_LIMIT:
        return True
    cache.set(key, count + 1, RATE_WINDOW_SECONDS)
    return False


def inquiry_create(request):
    artwork = None
    artwork_id = request.GET.get("artwork") or request.POST.get("artwork_id")
    if artwork_id and str(artwork_id).isdigit():
        artwork = ArtworkPage.objects.live().public().filter(id=artwork_id).first()

    initial = {}
    requested_type = request.GET.get("type")
    valid_types = dict(Inquiry.INQUIRY_TYPE_CHOICES)
    if artwork and requested_type in valid_types:
        initial["inquiry_type"] = requested_type
    elif artwork:
        initial["inquiry_type"] = Inquiry.INQUIRY_ARTWORK
    elif requested_type in valid_types:
        initial["inquiry_type"] = requested_type

    if request.user.is_authenticated:
        initial["name"] = request.user.get_full_name() or request.user.first_name
        initial["email"] = request.user.email

    if request.method == "POST":
        form = InquiryForm(request.POST, request.FILES)
        if form.is_valid():
            if _rate_limited(request):
                messages.error(
                    request,
                    _("You've sent a lot of messages. Please try again a bit later."),
                )
            else:
                inquiry = form.save(commit=False)
                inquiry.language = translation.get_language()
                if artwork:
                    inquiry.artwork = artwork
                if request.user.is_authenticated:
                    inquiry.user = request.user
                inquiry.save()
                track(request, Event.ENQUIRY, page=artwork, title="" if artwork else "General message")
                transaction.on_commit(lambda: emails.send_received(inquiry))
                return redirect("contact:thanks", token=inquiry.token)
    else:
        form = InquiryForm(initial=initial)

    from shop.cart import shop_settings
    from shop.models import size_estimates

    return render(
        request,
        "contact/inquiry_form.html",
        {"form": form, "artwork": artwork, "size_options": size_estimates(shop_settings())},
    )


def thanks(request, token):
    inquiry = get_object_or_404(Inquiry, token=token)
    return render(request, "contact/thanks.html", {"inquiry": inquiry})


def request_status(request, token):
    """Private status page for a commission or custom print request."""
    inquiry = get_object_or_404(Inquiry, token=token)
    steps = []
    if inquiry.is_request and inquiry.status not in (
        Inquiry.STATUS_DECLINED,
        Inquiry.STATUS_CLOSED,
    ):
        labels = dict(Inquiry.STATUS_CHOICES)
        labels[Inquiry.STATUS_NEW] = _("Request received")
        timeline = Inquiry.TIMELINE
        current = (
            timeline.index(inquiry.status)
            if inquiry.status in timeline
            else 0  # "replied" counts as still being discussed
        )
        for i, status in enumerate(timeline):
            state = "done" if i < current else "current" if i == current else "todo"
            steps.append((labels[status], state))
    from shop.cart import shop_settings

    return render(
        request,
        "contact/request_status.html",
        {"inquiry": inquiry, "steps": steps, "shop": shop_settings()},
    )


@staff_member_required
def reference_image(request, pk):
    """Reference photos are private: only logged-in staff can open them."""
    inquiry = get_object_or_404(Inquiry, pk=pk)
    if not inquiry.reference_image:
        raise Http404
    return FileResponse(inquiry.reference_image.open("rb"))
