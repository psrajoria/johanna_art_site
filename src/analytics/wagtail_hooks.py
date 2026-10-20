from django.template.loader import render_to_string
from django.urls import path, reverse

from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.admin.ui.components import Component

from . import reports
from .tracking import record_page_view


@hooks.register("before_serve_page")
def count_page_view(page, request, serve_args, serve_kwargs):
    record_page_view(page, request)


def insights(request):
    from django.shortcuts import render

    try:
        days = int(request.GET.get("days", 30))
    except ValueError:
        days = 30
    days = days if days in (7, 30, 90) else 30
    return render(request, "analytics/insights.html", {"r": reports.build(days), "ranges": (7, 30, 90)})


@hooks.register("register_admin_urls")
def insights_urls():
    return [path("insights/", insights, name="insights")]


@hooks.register("register_admin_menu_item")
def insights_menu_item():
    return MenuItem("Insights", reverse("insights"), icon_name="view", order=250)


class WeekPanel(Component):
    order = 20

    def render_html(self, parent_context=None):
        return render_to_string("analytics/week_panel.html", {"r": reports.build(7)})


@hooks.register("construct_homepage_panels")
def add_week_panel(request, panels):
    panels.insert(1, WeekPanel())
