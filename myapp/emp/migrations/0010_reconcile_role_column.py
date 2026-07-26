from django.db import migrations, models


class Migration(migrations.Migration):
    """The `role` column already exists on the live emp_emp table - it was
    added directly on Supabase at some point, outside Django's migration
    history entirely (confirmed via git log: no migration or model in this
    repo's history ever declared it). It was NOT NULL with no default,
    which meant every INSERT (admin, add_emp view, anything) failed.

    We can't just AddField it normally - on the live DB the column is
    already there, so a plain ALTER TABLE ADD COLUMN would fail. But a
    *fresh* database (a clean clone, the test-database build) never had
    it at all, so the fix has to work both ways: `ADD COLUMN IF NOT
    EXISTS` creates it on a fresh DB, and is a no-op on the live one where
    it already exists; the SET DEFAULT/backfill/SET NOT NULL steps then
    bring either starting point to the same final, well-defined state.
    """

    dependencies = [
        ('emp', '0009_emp_department_not_null'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='emp',
                    name='role',
                    field=models.CharField(max_length=100, blank=True, default=''),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE emp_emp ADD COLUMN IF NOT EXISTS role varchar(100) NOT NULL DEFAULT '';"
                        "ALTER TABLE emp_emp ALTER COLUMN role SET DEFAULT '';"
                        "UPDATE emp_emp SET role = '' WHERE role IS NULL;"
                        "ALTER TABLE emp_emp ALTER COLUMN role SET NOT NULL;"
                    ),
                    reverse_sql="ALTER TABLE emp_emp ALTER COLUMN role DROP DEFAULT;",
                ),
            ],
        ),
    ]
