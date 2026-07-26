from django.db import migrations

VALID_ROLE_CODES = {
    "SOFTWARE_ENGINEER",
    "SENIOR_SOFTWARE_ENGINEER",
    "QA_ENGINEER",
    "DEVOPS_ENGINEER",
    "TEAM_LEAD",
    "PROJECT_MANAGER",
    "HR",
    "SYSTEM_ADMINISTRATOR",
}


def clear_invalid_roles(apps, schema_editor):
    # 'role' held leftover placeholder data ('doctor') from before this was
    # a real Django field with a defined IT-role taxonomy - clear anything
    # that doesn't match one of the new choice codes rather than leaving
    # stale, meaningless values in place.
    Emp = apps.get_model('emp', 'Emp')
    Emp.objects.exclude(role__in=VALID_ROLE_CODES).update(role='')


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('emp', '0011_alter_emp_role'),
    ]

    operations = [
        migrations.RunPython(clear_invalid_roles, noop_reverse),
    ]
