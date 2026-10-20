from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.models import Event, PageView


class Command(BaseCommand):
    help = "Delete visit statistics older than a year (keeps the database small)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=400)

    def handle(self, *args, **options):
        cutoff = timezone.localdate() - timedelta(days=options["days"])
        views = PageView.objects.filter(day__lt=cutoff).delete()[0]
        events = Event.objects.filter(day__lt=cutoff).delete()[0]
        self.stdout.write(f"Removed {views} page views and {events} events older than {cutoff}.")
