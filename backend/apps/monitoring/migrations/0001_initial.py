from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ApplicationLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("level", models.CharField(choices=[
                    ("DEBUG", "Отладка"),
                    ("INFO", "Информация"),
                    ("WARNING", "Предупреждение"),
                    ("ERROR", "Ошибка"),
                    ("CRITICAL", "Критическая ошибка"),
                ], max_length=16)),
                ("logger_name", models.CharField(db_index=True, max_length=255)),
                ("message", models.TextField()),
                ("request_id", models.CharField(blank=True, max_length=128)),
                ("extra", models.JSONField(blank=True, null=True)),
                ("exc_text", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Событие лога",
                "verbose_name_plural": "События логов",
                "ordering": ["-id"],
            },
        ),
        migrations.AddIndex(
            model_name="applicationlog",
            index=models.Index(fields=["-created_at", "level"], name="monitoring_created_level_idx"),
        ),
        migrations.AddIndex(
            model_name="applicationlog",
            index=models.Index(fields=["logger_name", "level"], name="monitoring_logger_level_idx"),
        ),
    ]