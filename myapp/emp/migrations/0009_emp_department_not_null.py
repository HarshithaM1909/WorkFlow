import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emp', '0008_swap_department_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emp',
            name='department',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='employees', to='emp.department'),
        ),
    ]
