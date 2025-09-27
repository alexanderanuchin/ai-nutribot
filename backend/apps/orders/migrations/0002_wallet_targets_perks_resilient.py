# apps/orders/migrations/0002_wallet_targets_perks.py
# Django 5.2.6 — корректная последовательность:
# 1) добавляем модели в state (без DB)
# 2) отдельным RunPython создаём таблицы только если их нет

from django.db import migrations, models
import django.db.models.deletion


def create_tables_if_missing(apps, schema_editor):
    connection = schema_editor.connection
    existing = set(connection.introspection.table_names())

    WalletPerk = apps.get_model("orders", "WalletPerk")
    WalletTarget = apps.get_model("orders", "WalletTarget")

    if WalletPerk._meta.db_table not in existing:
        schema_editor.create_model(WalletPerk)

    if WalletTarget._meta.db_table not in existing:
        schema_editor.create_model(WalletTarget)


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
        # Можно жёстко зафиксировать порядок относительно users, если нужно:
        # ("users", "0005_profile_avatar_preferences_profile_wallet_settings"),
    ]

    operations = [
        # 1) Только меняем состояние: добавляем модели и их метаданные
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="WalletPerk",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("title", models.CharField(max_length=255)),
                        ("description", models.CharField(max_length=255, blank=True)),
                        ("cta_label", models.CharField(max_length=128, blank=True)),
                        ("cta_url", models.URLField(blank=True)),
                        ("is_active", models.BooleanField(default=True)),
                        ("priority", models.PositiveSmallIntegerField(default=0)),
                        ("metadata", models.JSONField(default=dict, blank=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="wallet_perks", to="users.profile")),
                    ],
                    options={
                        "verbose_name": "Перк кошелька",
                        "verbose_name_plural": "Перки кошелька",
                        "ordering": ("priority", "id"),
                        "indexes": [
                            models.Index(fields=["profile", "is_active"], name="orders_wperk_profile_active_idx"),
                        ],
                    },
                ),
                migrations.CreateModel(
                    name="WalletTarget",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("currency", models.CharField(max_length=16, choices=[("STARS", "Telegram Stars"), ("CALO", "CaloCoin")])),
                        ("target_amount", models.DecimalField(max_digits=12, decimal_places=2)),
                        ("priority", models.PositiveSmallIntegerField(default=0)),
                        ("label", models.CharField(max_length=255, blank=True)),
                        ("progress_template", models.CharField(
                            max_length=255, blank=True,
                            help_text="Сообщение при неполном прогрессе. Плейсхолдеры {left}, {target}, {balance}.",
                        )),
                        ("completed_template", models.CharField(
                            max_length=255, blank=True,
                            help_text="Сообщение при достижении цели. Плейсхолдеры {left}, {target}, {balance}.",
                        )),
                        ("is_active", models.BooleanField(default=True)),
                        ("metadata", models.JSONField(default=dict, blank=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="wallet_targets", to="users.profile")),
                    ],
                    options={
                        "verbose_name": "Цель кошелька",
                        "verbose_name_plural": "Цели кошелька",
                        "ordering": ("priority", "currency", "id"),
                        "indexes": [
                            models.Index(fields=["profile", "currency", "is_active"], name="orders_wtarget_profile_curr_active_idx"),
                        ],
                    },
                ),
                migrations.AlterUniqueTogether(
                    name="wallettarget",
                    unique_together={("profile", "currency", "priority")},
                ),
            ],
            database_operations=[],
        ),

        # 2) Теперь у Django есть модели в state, можно безопасно создать таблицы при необходимости
        migrations.RunPython(create_tables_if_missing, migrations.RunPython.noop),
    ]
