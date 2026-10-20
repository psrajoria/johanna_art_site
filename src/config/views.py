from django.shortcuts import render
from django.utils.translation import gettext as _


def _error(request, status, code, title, text):
    return render(
        request,
        "error.html",
        {"code": code, "title": title, "text": text},
        status=status,
    )


def page_not_found(request, exception=None):
    return _error(
        request,
        404,
        "404",
        _("This page wandered off the paper."),
        _("The link may be old, or the artwork may have moved on to a new wall."),
    )


def permission_denied(request, exception=None):
    return _error(
        request,
        403,
        "403",
        _("This corner of the studio is private."),
        _("You do not have access to this page. If you think that is a mistake, please write to us."),
    )


def bad_request(request, exception=None):
    return _error(
        request,
        400,
        "400",
        _("That request got smudged."),
        _("Something about the request did not look right. Please go back and try again."),
    )


def csrf_failure(request, reason=""):
    return _error(
        request,
        403,
        "403",
        _("Your page went stale."),
        _("The form was open for a long time or cookies are switched off. Please go back, reload the page and send it again."),
    )


def preview_error(request, code):
    """Development only: look at an error page without having to break the site."""
    from django.http import Http404
    from django.template.loader import render_to_string
    from django.http import HttpResponse

    handlers = {400: bad_request, 403: permission_denied, 404: page_not_found}
    if code == 500:
        return HttpResponse(render_to_string("500.html"))
    if code == 4030:  # a stale form
        return csrf_failure(request)
    if code not in handlers:
        raise Http404
    return handlers[code](request)
