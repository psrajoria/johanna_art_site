import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from wagtail.models import Page

from .models import Event
from .tracking import track


@csrf_exempt
@require_POST
def beacon(request):
    """Browser reports a click (heart, Instagram, wall preview). Whitelisted names only."""
    try:
        data = json.loads(request.body or b"{}")
        name = data.get("name", "")
        if name not in Event.BROWSER_NAMES:
            return HttpResponse(status=204)
        page = None
        if str(data.get("page", "")).isdigit():
            page = Page.objects.filter(pk=int(data["page"])).first()
        track(request, name, page=page, title="" if page else str(data.get("label", ""))[:80])
    except Exception:
        pass
    return HttpResponse(status=204)
