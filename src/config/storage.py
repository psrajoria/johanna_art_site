from django.conf import settings
from django.core.files.storage import FileSystemStorage


def private_storage():
    """Storage for files that must never be served by the public /media/ URL."""
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)
