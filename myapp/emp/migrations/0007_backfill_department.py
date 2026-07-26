from django.db import migrations

DEPARTMENT_NAMES = {
    'CSE': 'Computer Science and Engineering',
    'ME': 'Mechanical Engineering',
    'EEE': 'Electrical and Electronics Engineering',
    'UNASSIGNED': 'Unassigned',
}

# Seed the historical CSE/ME/EEE options even if no employee currently
# uses one of them, so the dropdown keeps offering all three going forward.
SEED_CODES = ['CSE', 'ME', 'EEE']


def backfill_departments(apps, schema_editor):
    Emp = apps.get_model('emp', 'Emp')
    Department = apps.get_model('emp', 'Department')

    for code in SEED_CODES:
        Department.objects.get_or_create(code=code, defaults={'name': DEPARTMENT_NAMES[code]})

    for emp in Emp.objects.all():
        code = (emp.department or '').strip() or 'UNASSIGNED'
        department, _ = Department.objects.get_or_create(
            code=code,
            defaults={'name': DEPARTMENT_NAMES.get(code, code)},
        )
        emp.department_new = department
        emp.save(update_fields=['department_new'])


def restore_department_strings(apps, schema_editor):
    Emp = apps.get_model('emp', 'Emp')
    for emp in Emp.objects.all():
        if emp.department_new_id:
            emp.department = emp.department_new.code
            emp.save(update_fields=['department'])


class Migration(migrations.Migration):

    dependencies = [
        ('emp', '0006_department_emp_department_new'),
    ]

    operations = [
        migrations.RunPython(backfill_departments, restore_department_strings),
    ]
