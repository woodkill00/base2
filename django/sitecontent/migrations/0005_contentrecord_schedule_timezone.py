from django.db import migrations, models


def backfill_scheduled_timezone(apps, schema_editor):
    content_record = apps.get_model('sitecontent', 'ContentRecord')
    content_record.objects.filter(state='scheduled', schedule_timezone='').update(
        schedule_timezone='UTC'
    )


class Migration(migrations.Migration):
    dependencies = [
        ('sitecontent', '0004_contentrelationship_maximum_depth_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contentrecord',
            name='schedule_timezone',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.RunPython(backfill_scheduled_timezone, migrations.RunPython.noop),
    ]
