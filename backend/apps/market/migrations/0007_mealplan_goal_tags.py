from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("market", "0006_mealplanaccess_recipeaccess"),
    ]

    operations = [
        migrations.AddField(
            model_name="mealplan",
            name="goal",
            field=models.CharField(
                blank=True,
                choices=[
                    ("weight_loss", "Похудение"),
                    ("muscle_gain", "Набор массы"),
                    ("detox", "Детокс"),
                    ("keto", "Кето"),
                    ("balanced", "Сбалансированное питание"),
                ],
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="mealplan",
            name="tags",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="mealplan",
            name="duration_days",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="mealplan",
            name="total_calories",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="mealplan",
            name="calories_per_day",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="mealplan",
            index=models.Index(
                fields=["goal", "is_published"],
                name="market_plan_goal_pub",
            ),
        ),
        migrations.AddIndex(
            model_name="mealplan",
            index=models.Index(fields=["duration_days"], name="market_plan_duration"),
        ),
        migrations.AddIndex(
            model_name="mealplan",
            index=models.Index(fields=["total_calories"], name="market_plan_calories"),
        ),
    ]
