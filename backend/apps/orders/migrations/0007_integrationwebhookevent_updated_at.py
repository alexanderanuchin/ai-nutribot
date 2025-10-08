from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0006_paymentattempt_orders_payment_provider_external_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="integrationwebhookevent",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]