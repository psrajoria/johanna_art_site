from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Development-only key. Production reads SECRET_KEY from the environment.
SECRET_KEY = "django-insecure-dev-only-key-do-not-use-in-production"

ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

try:
    from .local import *
except ImportError:
    pass
