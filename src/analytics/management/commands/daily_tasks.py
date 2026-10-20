"""Runs the once-a-day jobs. Safe to call every hour: each job runs at most once per day."""

from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.models import TaskRun

MORNING_HOUR = 7


def current_hour():
    return timezone.localtime().hour


class Command(BaseCommand):
    help = "Morning digest, Instagram refresh and old-statistics cleanup (once a day each)."

    def handle(self, *args, **options):
        today = timezone.localdate()
        hour = current_hour()
        jobs = [
            ("digest", MORNING_HOUR, "admin_digest"),
            ("instagram", 0, "fetch_instagram"),
            ("prune", 3, "prune_analytics"),
        ]
        for name, after_hour, command in jobs:
            run, _created = TaskRun.objects.get_or_create(
                name=name, defaults={"last_run": today - timedelta(days=1)}
            )
            if run.last_run >= today or hour < after_hour:
                continue
            try:
                call_command(command)
            except Exception as exc:  # one failing job must not stop the others
                self.stderr.write(f"{command} failed: {exc}")
            run.last_run = today
            run.save()
