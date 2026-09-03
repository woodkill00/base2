from django.db import migrations, models


def populate_projection_fields(apps, schema_editor):
    ExportJob = apps.get_model('sitecontent', 'ExportJob')
    ContentFieldDefinition = apps.get_model('sitecontent', 'ContentFieldDefinition')
    for job in ExportJob.objects.filter(projection_fields=[]).iterator(chunk_size=200):
        fields = list(
            ContentFieldDefinition.objects.filter(definition_id=job.definition_id)
            .order_by('order', 'field_key')
            .values_list('field_key', flat=True)[:64]
        )
        job.projection_fields = fields or ['title']
        job.save(update_fields=['projection_fields'])


class Migration(migrations.Migration):
    dependencies = [('sitecontent', '0007_mediaasset_rejected_status')]

    operations = [
        migrations.AddField(
            model_name='exportjob',
            name='projection_fields',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(populate_projection_fields, migrations.RunPython.noop),
    ]
