from __future__ import annotations

from django.core.management.base import BaseCommand

from ...ingestion import ingest_sources


class Command(BaseCommand):
    help = "Fetch feed items from configured sources and persist them."

    def handle(self, *args, **options):
        result = ingest_sources()
        summary = (
            f"processed={result['processed']} created={result['created']} "
            f"updated={result['updated']} skipped={result['skipped']}"
        )
        self.stdout.write(self.style.SUCCESS(f"Feed ingestion completed: {summary}"))