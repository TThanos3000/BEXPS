from django.db import migrations


def ensure_completed_status(apps, schema_editor):
    ApplicationStatus = apps.get_model("parmodels", "ApplicationStatus")
    ApplicationStatus.objects.update_or_create(
        code="completed",
        defaults={
            "name": "Выполнено",
            "color_code": "#198754",
            "is_system": True,
            "is_active": True,
        },
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("parmodels", "0012_applicationpriority_color_code_and_more"),
    ]

    operations = [
        migrations.RunPython(ensure_completed_status, noop_reverse),
    ]
