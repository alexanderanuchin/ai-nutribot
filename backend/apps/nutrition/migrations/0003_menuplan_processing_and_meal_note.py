from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nutrition", "0002_menuplan_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="menuplan",
            name="status",
            field=models.CharField(
                choices=[
                    ("generated", "Сгенерирован"),
                    ("accepted", "Принят"),
                    ("rejected", "Отклонён"),
                    ("recalculated", "Пересчитан"),
                    ("processing", "В обработке"),
                ],
                default="generated",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="planmeal",
            name="user_note",
            field=models.TextField(blank=True, default=""),
        ),
    ]