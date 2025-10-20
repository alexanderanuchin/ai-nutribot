from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("feed", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="newsarticle",
            name="tonality",
            field=models.CharField(
                choices=[
                    ("positive", "Positive"),
                    ("neutral", "Neutral"),
                    ("negative", "Negative"),
                ],
                db_index=True,
                default="neutral",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="newsarticle",
            name="source_categories",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="newsarticle",
            name="ingested_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="newsarticle",
            name="ingestion_source",
            field=models.CharField(blank=True, max_length=64, default=""),
        ),
        migrations.AddField(
            model_name="newsarticle",
            name="ingestion_rid",
            field=models.CharField(blank=True, max_length=128, default=""),
        ),
        migrations.AddField(
            model_name="newsarticle",
            name="ingestion_metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]