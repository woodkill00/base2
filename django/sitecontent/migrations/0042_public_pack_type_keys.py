"""Additive validator-state compatibility; no existing content is rewritten."""

from django.core.validators import RegexValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0041_workspace_revision_tenant_scope")]
    operations = [
        migrations.AlterField(
            model_name=model_name,
            name=field_name,
            field=models.CharField(
                max_length=63,
                validators=[
                    RegexValidator(
                        r"\A(?=.{2,63}\Z)[a-z][a-z0-9_]*(?:-[a-z0-9][a-z0-9_]*)*\Z",
                        "Use 2–63 lowercase ASCII letters, digits or underscores, "
                        "with single hyphens followed by a letter or digit.",
                    )
                ],
                **options,
            ),
        )
        for model_name, field_name, options in [
            ("contenttypedefinition", "type_key", {}),
            ("contentrelationship", "target_type", {"blank": True, "default": ""}),
        ]
    ]

    # Preserve the existing field/preset language but disallow the final newline
    # accepted by RegexValidator's old dollar anchor. No row rewrite is performed.
    operations += [
        migrations.AlterField(
            model_name=model_name,
            name=field_name,
            field=models.CharField(
                max_length=63,
                validators=[
                    RegexValidator(
                        r"\A[a-z][a-z0-9_]{1,62}\Z",
                        "Use a lowercase identifier beginning with a letter.",
                    )
                ],
                **options,
            ),
        )
        for model_name, field_name, options in [
            ("contenttypedefinition", "preset_id", {"blank": True, "default": ""}),
            ("contentfielddefinition", "field_key", {}),
            ("contentrelationship", "field_key", {}),
            ("assetbinding", "field_key", {}),
        ]
    ]
