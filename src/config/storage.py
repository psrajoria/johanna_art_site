import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateStorage(FileSystemStorage):
    """Files that must never be served by the public /media/ URL.

    The folder is read from settings.PRIVATE_MEDIA_ROOT every time it is used,
    so tests and deployments can point it somewhere else.
    """

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)


def private_storage():
    return PrivateStorage()
