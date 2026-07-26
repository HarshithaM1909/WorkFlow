from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('emp', '0007_backfill_department'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='emp',
            name='department',
        ),
        migrations.RenameField(
            model_name='emp',
            old_name='department_new',
            new_name='department',
        ),
    ]
