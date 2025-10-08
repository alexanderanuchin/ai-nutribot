from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0007_integrationwebhookevent_updated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="wallettransaction",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]