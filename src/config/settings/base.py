"""
Base settings for Johanna's art site.

Anything that differs between machines (secrets, hostnames, email, PayPal)
comes from environment variables or a `.env` file next to manage.py.
See `.env.example` for the full list.
"""

from pathlib import Path

import environ

PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_DIR.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

INSTALLED_APPS = [
    "home",
    "search",
    "artworks",
    "blog",
    "shop",
    "contact",
    "analytics",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.contrib.settings",
    "wagtail.contrib.simple_translation",
    "wagtail.contrib.sitemaps",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.locales",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django_filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            PROJECT_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "wagtail.contrib.settings.context_processors.settings",
                "shop.context_processors.cart",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env("DATABASE_PATH", default=str(BASE_DIR / "db.sqlite3")),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGIN_URL = "shop:login"
LOGIN_REDIRECT_URL = "shop:account"
LOGOUT_REDIRECT_URL = "/"

# --- Internationalisation: English (default, served at /) and German (/de/) ---

LANGUAGE_CODE = "en"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("de", "Deutsch"),
]
WAGTAIL_I18N_ENABLED = True
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES
LOCALE_PATHS = [PROJECT_DIR / "locale"]

# --- Static & media ---

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATICFILES_DIRS = [
    PROJECT_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "static"
STATIC_URL = "/static/"

MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))
MEDIA_URL = "/media/"

# Paid digital files live here. It is never served directly: shop.views
# hands files out only to customers with a paid order.
PRIVATE_MEDIA_ROOT = Path(
    env("PRIVATE_MEDIA_ROOT", default=str(BASE_DIR / "private_media"))
)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10_000

# --- Wagtail ---

WAGTAIL_SITE_NAME = "Johanna Lackner"

WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    }
}

WAGTAILADMIN_BASE_URL = env("SITE_URL", default="http://localhost:8000")

WAGTAILDOCS_EXTENSIONS = [
    "csv",
    "docx",
    "key",
    "odt",
    "pdf",
    "pptx",
    "rtf",
    "txt",
    "xlsx",
    "zip",
]
WAGTAILDOCS_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

# Artists upload big photos straight off a phone or scanner.
WAGTAILIMAGES_MAX_UPLOAD_SIZE = 30 * 1024 * 1024  # 30MB
WAGTAILIMAGES_FORMAT_CONVERSIONS = {"webp": "webp", "bmp": "jpeg"}

# --- Email ---
# Order, inquiry and commission notifications are sent from here. Set the
# EMAIL_* variables in `.env` once the domain mailbox exists; until then
# dev prints emails to the console.

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Johanna Lackner <hello@example.com>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

# --- Shop ---

SHOP_CURRENCY = "EUR"
# Inbox that receives "new order / new inquiry" alerts. Can be overridden
# in the admin under Settings > Shop settings.
SHOP_NOTIFY_EMAIL = env("SHOP_NOTIFY_EMAIL", default="")

# A styled page instead of the bare default when a form has gone stale.
CSRF_FAILURE_VIEW = "config.views.csrf_failure"
