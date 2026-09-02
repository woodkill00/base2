from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0006_importjob_source_artifact")]

    operations = [
        migrations.AlterField(
            model_name="mediaasset",
            name="status",
            field=models.CharField(
                choices=(
                    ("pending", "Pending"),
                    ("validated", "Validated"),
                    ("quarantined", "Quarantined"),
                    ("rejected", "Rejected"),
                    ("deleted", "Deleted"),
                ),
                default="pending",
                max_length=16,
            ),
        )
    ]
