"""Pull her newest Instagram posts onto the site (needs a Creator/Business account and a token).

Run it daily from cron. It also renews the access token, which otherwise expires after 60 days.
"""

import json
from datetime import datetime
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime

from home.models import InstagramPost, SiteSettings

API = "https://graph.instagram.com"
FIELDS = "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp"


def _get(url, timeout=20):
    with urlopen(url, timeout=timeout) as response:  # noqa: S310 - fixed https hosts
        return response.read()


class Command(BaseCommand):
    help = "Fetch the newest Instagram posts (uses the token in Site settings)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=9)

    def handle(self, *args, **options):
        settings_obj = SiteSettings.objects.exclude(instagram_access_token="").first()
        if not settings_obj:
            self.stdout.write("No Instagram access token set - nothing to do.")
            return
        token = settings_obj.instagram_access_token

        try:
            refreshed = json.loads(
                _get(
                    f"{API}/refresh_access_token?"
                    + urlencode({"grant_type": "ig_refresh_token", "access_token": token})
                )
            )
            if refreshed.get("access_token"):
                settings_obj.instagram_access_token = refreshed["access_token"]
                settings_obj.save(update_fields=["instagram_access_token"])
                token = refreshed["access_token"]
            data = json.loads(
                _get(
                    f"{API}/me/media?"
                    + urlencode({"fields": FIELDS, "limit": options["limit"], "access_token": token})
                )
            )
        except (URLError, ValueError) as exc:
            raise CommandError(f"Instagram could not be reached: {exc}")

        created = 0
        for item in data.get("data", []):
            if item.get("media_type") == "VIDEO":
                image_url = item.get("thumbnail_url")
            else:
                image_url = item.get("media_url")
            if not image_url or InstagramPost.objects.filter(instagram_id=item["id"]).exists():
                continue
            try:
                content = _get(image_url)
            except URLError:
                continue
            post = InstagramPost(
                instagram_id=item["id"],
                permalink=item.get("permalink", ""),
                caption=(item.get("caption") or "")[:160],
                posted_at=parse_datetime(item["timestamp"].replace("+0000", "+00:00")) or datetime.now(),
            )
            post.image.save(f"{item['id']}.jpg", ContentFile(content), save=True)
            created += 1

        # keep only the newest few on disk
        for old in InstagramPost.objects.all()[options["limit"] * 2:]:
            old.image.delete(save=False)
            old.delete()
        self.stdout.write(f"Instagram: {created} new post(s).")
