from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.contrib.sitemaps.views import sitemap
from wagtail.documents import urls as wagtaildocs_urls

from blog.feeds import LatestPostsFeed
from config import views as config_views
from search import views as search_views


def robots_txt(request):
    base = f"{request.scheme}://{request.get_host()}"
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /django-admin/",
        "Disallow: /shop/",
        "Disallow: /de/shop/",
        "Disallow: /contact/",
        "Disallow: /de/contact/",
        f"Sitemap: {base}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("sitemap.xml", sitemap),
    path("a/", include("analytics.urls")),
    path("robots.txt", robots_txt),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Everything visitors see lives under a language prefix: English at "/" and
# German at "/de/".
urlpatterns += i18n_patterns(
    path("search/", search_views.search, name="search"),
    path("contact/", include("contact.urls")),
    path("shop/", include("shop.urls")),
    path("blog/feed/", LatestPostsFeed(), name="blog_feed"),
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern.
    path("", include(wagtail_urls)),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns = [path("_errors/<int:code>/", config_views.preview_error)] + urlpatterns

handler404 = "config.views.page_not_found"
handler403 = "config.views.permission_denied"
handler400 = "config.views.bad_request"
