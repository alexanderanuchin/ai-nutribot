from __future__ import annotations

from django.contrib.postgres.indexes import GinIndex
from django.db import migrations


def create_metadata_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":  # pragma: no cover - depends on backend
        return
    statements = [
        "CREATE INDEX IF NOT EXISTS market_store_metadata_gin ON market_store USING GIN (metadata jsonb_path_ops)",
        "CREATE INDEX IF NOT EXISTS market_product_metadata_gin ON market_product USING GIN (metadata jsonb_path_ops)",
        "CREATE INDEX IF NOT EXISTS market_recipe_metadata_gin ON market_recipe USING GIN (metadata jsonb_path_ops)",
    ]
    for statement in statements:
        schema_editor.execute(statement)


def drop_metadata_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":  # pragma: no cover - depends on backend
        return
    statements = [
        "DROP INDEX IF EXISTS market_store_metadata_gin",
        "DROP INDEX IF EXISTS market_product_metadata_gin",
        "DROP INDEX IF EXISTS market_recipe_metadata_gin",
    ]
    for statement in statements:
        schema_editor.execute(statement)


class Migration(migrations.Migration):
    dependencies = [
        ("market", "0002_product_metadata"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddIndex(
                    model_name="store",
                    index=GinIndex(
                        fields=["metadata"],
                        name="market_store_metadata_gin",
                        opclasses=["jsonb_path_ops"],
                    ),
                ),
                migrations.AddIndex(
                    model_name="product",
                    index=GinIndex(
                        fields=["metadata"],
                        name="market_product_metadata_gin",
                        opclasses=["jsonb_path_ops"],
                    ),
                ),
                migrations.AddIndex(
                    model_name="recipe",
                    index=GinIndex(
                        fields=["metadata"],
                        name="market_recipe_metadata_gin",
                        opclasses=["jsonb_path_ops"],
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(create_metadata_indexes, reverse_code=drop_metadata_indexes),
            ],
        ),
    ]
