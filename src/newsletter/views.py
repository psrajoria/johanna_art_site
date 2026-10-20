from django import forms
from django.core.cache import cache
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from analytics.models import Event
from analytics.tracking import track

from . import emails
from .models import Subscriber

RATE_LIMIT = 6
RATE_WINDOW = 3600


class SubscribeForm(forms.Form):
    email = forms.EmailField(max_length=254)
    website = forms.CharField(required=False)  # honeypot: humans leave it empty


def _ip(request):
    return request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")


def _page(request, title, text, status=200):
    return render(request, "newsletter/message.html", {"title": title, "text": text}, status=status)


@require_POST
def subscribe(request):
    form = SubscribeForm(request.POST)
    if not form.is_valid():
        return _page(request, _("That email address does not look right."), _("Please go back and try again."), 400)
    if form.cleaned_data["website"]:
        # a bot filled the hidden field: pretend it worked
        return _page(request, _("Almost done!"), _("Check your inbox and confirm your email address."))

    key = f"newsletter-rate-{_ip(request)}"
    count = cache.get(key, 0)
    if count >= RATE_LIMIT:
        return _page(request, _("Too many tries."), _("Please try again a little later."), 429)
    cache.set(key, count + 1, RATE_WINDOW)

    email = form.cleaned_data["email"].strip().lower()
    lang = translation.get_language() or "en"
    subscriber, _created = Subscriber.objects.get_or_create(email=email, defaults={"language": lang[:5]})
    if subscriber.is_active:
        return _page(request, _("You are already on the list."), _("Thank you, that is lovely."))
    subscriber.language = lang[:5]
    subscriber.unsubscribed_at = None
    subscriber.save()
    emails.send_confirmation(subscriber)
    track(request, Event.NEWSLETTER, title="Newsletter")
    return _page(request, _("Almost done!"), _("Check your inbox and confirm your email address."))


def confirm(request, token):
    subscriber = get_object_or_404(Subscriber, token=token)
    subscriber.confirm()
    return _page(request, _("You are subscribed."), _("Thank you! New work and notes from the studio will find you."))


def unsubscribe(request, token):
    if token == "test":  # the link in test emails
        return _page(request, _("This is only a test email."), _("In the real newsletter this link unsubscribes you."))
    subscriber = Subscriber.objects.filter(token=token).first()
    if not subscriber:
        raise Http404
    if request.method == "POST":
        subscriber.unsubscribe()
        return _page(request, _("You are unsubscribed."), _("I will miss you. You can sign up again any time."))
    return render(request, "newsletter/unsubscribe.html", {"subscriber": subscriber})
