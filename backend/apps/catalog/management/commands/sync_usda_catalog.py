"""Management command to synchronise the catalogue with the USDA dataset."""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.etl.usda import (
    DEFAULT_SOURCE_URL,
    USDAFoodExtractor,
    USDAFoodImporter,
    USDAFoodTransformer,
)


class Command(BaseCommand):
    help = "Import and enrich menu items from the USDA open dataset"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of items processed (after filtering).",
        )
        parser.add_argument(
            "--min-calories",
            type=float,
            default=150.0,
            help="Discard entries with fewer calories to avoid condiments.",
        )
        parser.add_argument(
            "--groups",
            nargs="+",
            default=None,
            help="Restrict the import to specific USDA food groups.",
        )
        parser.add_argument(
            "--source-url",
            default=DEFAULT_SOURCE_URL,
            help="Override the default USDA dataset URL (useful for testing).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Download and transform data without touching the database.",
        )

    def handle(self, *args, **options):
        extractor = USDAFoodExtractor(source_url=options["source_url"])
        transformer = USDAFoodTransformer(
            allowed_groups=options["groups"],
            min_calories=options["min_calories"],
        )
        importer = USDAFoodImporter(extractor=extractor, transformer=transformer)
        try:
            result = importer.run(limit=options["limit"], dry_run=options["dry_run"])
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

        if options["dry_run"]:
            preview_titles = ", ".join(item.title for item in result.get("preview", []))
            message = (
                f"Dry run completed. {result['total']} items prepared."
                + (f" Preview: {preview_titles}" if preview_titles else "")
            )
            self.stdout.write(self.style.WARNING(message))
            return

        self.stdout.write(
            self.style.SUCCESS(
                "USDA import complete: "
                f"{result['total']} processed, {result['created']} created, {result['updated']} updated."
            )
        )