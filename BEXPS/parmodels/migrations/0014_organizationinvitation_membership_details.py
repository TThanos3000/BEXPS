from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("parmodels", "0013_ensure_completed_application_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizationinvitation",
            name="date_reception",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="organizationinvitation",
            name="department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="invitations",
                to="parmodels.department",
            ),
        ),
        migrations.AddField(
            model_name="organizationinvitation",
            name="position",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
