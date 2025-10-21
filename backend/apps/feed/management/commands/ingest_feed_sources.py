from __future__ import annotations

from django.core.management.base import BaseCommand

from ...ingestion import ingest_sources


class Command(BaseCommand):
    help = "Fetch feed items from configured sources and persist them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit-per-source",
            type=int,
            default=None,
            help="Limit the number of newest items ingested from each source.",
        )

    def handle(self, *args, **options):
        limit_per_source = options.get("limit_per_source")
        result = ingest_sources(items_limit_per_source=limit_per_source)
        summary = (
            f"processed={result['processed']} created={result['created']} "
            f"updated={result['updated']} skipped={result['skipped']}"
        )
        self.stdout.write(self.style.SUCCESS(f"Feed ingestion completed: {summary}"))
