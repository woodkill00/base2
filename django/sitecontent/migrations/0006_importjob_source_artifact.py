from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0005_contentrecord_schedule_timezone")]

    operations = [
        migrations.AddField(
            model_name="importjob",
            name="source_format",
            field=models.CharField(
                choices=(("json", "JSON"), ("csv", "CSV")), default="json", max_length=8
            ),
        ),
        migrations.AddField(
            model_name="importjob",
            name="source_object_key",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
