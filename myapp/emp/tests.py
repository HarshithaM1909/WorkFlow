import datetime

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import Attendance, Emp, LeaveRequest, Testimonial


def make_emp(**kwargs):
    defaults = {
        'name': 'Jane Doe',
        'emp_id': 'E100',
        'phone': '9999999999',
        'address': 'Somewhere',
        'working': True,
    }
    defaults.update(kwargs)
    return Emp.objects.create(**defaults)


class LeaveRequestModelTests(TestCase):
    def setUp(self):
        self.emp = make_emp()
        self.reviewer = User.objects.create_user('manager', password='pw')

    def test_clean_rejects_end_before_start(self):
        leave = LeaveRequest(
            employee=self.emp,
            start_date=datetime.date(2026, 1, 10),
            end_date=datetime.date(2026, 1, 5),
            reason='Trip',
        )
        with self.assertRaises(ValidationError):
            leave.clean()

    def test_approve_sets_status_and_reviewer(self):
        leave = LeaveRequest.objects.create(
            employee=self.emp,
            start_date=datetime.date(2026, 1, 5),
            end_date=datetime.date(2026, 1, 10),
            reason='Trip',
        )
        leave.approve(self.reviewer)
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.Status.APPROVED)
        self.assertEqual(leave.reviewed_by, self.reviewer)
        self.assertIsNotNone(leave.reviewed_at)

    def test_cannot_approve_twice(self):
        leave = LeaveRequest.objects.create(
            employee=self.emp,
            start_date=datetime.date(2026, 1, 5),
            end_date=datetime.date(2026, 1, 10),
            reason='Trip',
            status=LeaveRequest.Status.APPROVED,
        )
        with self.assertRaises(ValueError):
            leave.approve(self.reviewer)

    def test_reject_sets_status_and_note(self):
        leave = LeaveRequest.objects.create(
            employee=self.emp,
            start_date=datetime.date(2026, 1, 5),
            end_date=datetime.date(2026, 1, 10),
            reason='Trip',
        )
        leave.reject(self.reviewer, note='Understaffed that week')
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.Status.REJECTED)
        self.assertEqual(leave.review_note, 'Understaffed that week')


class AttendanceModelTests(TestCase):
    def setUp(self):
        self.emp = make_emp()

    def test_unique_attendance_per_employee_per_day(self):
        Attendance.objects.create(employee=self.emp, date=datetime.date(2026, 1, 1))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Attendance.objects.create(employee=self.emp, date=datetime.date(2026, 1, 1))


class DeleteEmpViewTests(TestCase):
    def setUp(self):
        self.emp = make_emp()
        self.user = User.objects.create_user('staffer', password='pw')
        self.user.user_permissions.add(Permission.objects.get(codename='delete_emp'))
        self.client.force_login(self.user)

    def test_get_shows_confirmation_without_deleting(self):
        response = self.client.get(f'/emp/delete-emp/{self.emp.id}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Emp.objects.filter(id=self.emp.id).exists())

    def test_post_deletes(self):
        response = self.client.post(f'/emp/delete-emp/{self.emp.id}')
        self.assertRedirects(response, '/emp/home/')
        self.assertFalse(Emp.objects.filter(id=self.emp.id).exists())

    def test_get_404s_for_unknown_id(self):
        response = self.client.get('/emp/delete-emp/999999')
        self.assertEqual(response.status_code, 404)


class AddEmpViewTests(TestCase):
    """Regression coverage for the orphaned `role` column bug: emp_emp had a
    NOT NULL `role` column that predated any Django migration, so every
    insert (admin and this view) failed until `role` was added to the model
    and the DB constraint relaxed (migration 0010)."""

    def setUp(self):
        self.user = User.objects.create_user('adder', password='pw')
        self.user.user_permissions.add(Permission.objects.get(codename='add_emp'))
        self.client.force_login(self.user)

    def test_add_emp_with_role_succeeds(self):
        response = self.client.post('/emp/add-emp/', {
            'name': 'Mallesh',
            'emp_id': '3',
            'phone': '9901059087',
            'address': 'Bangalore',
            'role': Emp.Role.SOFTWARE_ENGINEER,
            'working': 'on',
        })
        self.assertRedirects(response, '/emp/home/')
        emp = Emp.objects.get(emp_id='3')
        self.assertEqual(emp.role, Emp.Role.SOFTWARE_ENGINEER)

    def test_add_emp_without_role_defaults_to_blank(self):
        response = self.client.post('/emp/add-emp/', {
            'name': 'Shanthala',
            'emp_id': '4',
            'phone': '9876543211',
            'address': 'Hesarghatta',
            'working': 'on',
        })
        self.assertRedirects(response, '/emp/home/')
        emp = Emp.objects.get(emp_id='4')
        self.assertEqual(emp.role, '')

    def test_add_emp_missing_name_reshows_form_with_errors(self):
        response = self.client.post('/emp/add-emp/', {
            'name': '',
            'emp_id': '5',
            'phone': '9876543212',
            'address': 'Mysuru',
            'working': 'on',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Emp.objects.filter(emp_id='5').exists())
        self.assertTrue(response.context['form'].errors)

    def test_add_emp_duplicate_emp_id_rejected(self):
        make_emp(emp_id='dup-1')
        response = self.client.post('/emp/add-emp/', {
            'name': 'Second Person',
            'emp_id': 'dup-1',
            'phone': '9876543213',
            'address': 'Mysuru',
            'working': 'on',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Emp.objects.filter(emp_id='dup-1').count(), 1)
        self.assertIn('emp_id', response.context['form'].errors)


class UpdateEmpViewTests(TestCase):
    def setUp(self):
        self.emp = make_emp()
        self.user = User.objects.create_user('updater', password='pw')
        self.user.user_permissions.add(Permission.objects.get(codename='change_emp'))
        self.client.force_login(self.user)

    def test_post_updates_fields(self):
        response = self.client.post(f'/emp/update-emp/{self.emp.id}', {
            'name': 'Jane Updated',
            'emp_id': self.emp.emp_id,
            'phone': '8888888888',
            'address': 'New Address',
            'role': Emp.Role.TEAM_LEAD,
            'working': 'on',
        })
        self.assertRedirects(response, '/emp/home/')
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.name, 'Jane Updated')
        self.assertEqual(self.emp.role, Emp.Role.TEAM_LEAD)

    def test_get_404s_for_unknown_id(self):
        response = self.client.get('/emp/update-emp/999999')
        self.assertEqual(response.status_code, 404)


class LeaveRequestViewTests(TestCase):
    def setUp(self):
        self.emp = make_emp()
        self.employee_user = User.objects.create_user('employee', password='pw')
        self.emp.user = self.employee_user
        self.emp.save()

        self.manager = User.objects.create_user('manager', password='pw')
        self.manager.user_permissions.add(Permission.objects.get(codename='approve_leaverequest'))

    def test_anonymous_redirected_from_leave_queue(self):
        response = self.client.get(reverse('leave_queue'))
        self.assertEqual(response.status_code, 302)

    def test_non_manager_cannot_access_leave_queue(self):
        self.client.force_login(self.employee_user)
        response = self.client.get(reverse('leave_queue'))
        self.assertEqual(response.status_code, 403)

    def test_employee_can_submit_leave_request(self):
        self.client.force_login(self.employee_user)
        response = self.client.post(reverse('leave_request_create'), {
            'start_date': '2026-08-01',
            'end_date': '2026-08-03',
            'reason': 'Family event',
        })
        self.assertRedirects(response, '/emp/leave/my-requests/')
        self.assertEqual(LeaveRequest.objects.filter(employee=self.emp).count(), 1)

    def test_manager_can_approve_pending_request(self):
        leave = LeaveRequest.objects.create(
            employee=self.emp,
            start_date=datetime.date(2026, 8, 1),
            end_date=datetime.date(2026, 8, 3),
            reason='Family event',
        )
        self.client.force_login(self.manager)
        response = self.client.post(reverse('leave_approve', args=[leave.id]))
        self.assertRedirects(response, '/emp/leave/queue/')
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.Status.APPROVED)

    def test_user_without_employee_profile_redirected_from_leave_request(self):
        lone_user = User.objects.create_user('nobody', password='pw')
        self.client.force_login(lone_user)
        response = self.client.get(reverse('leave_request_create'))
        self.assertRedirects(response, '/emp/home/')


class TemplateRenderingTests(TestCase):
    """Exercises full template rendering (not just redirects) for the new pages."""

    def setUp(self):
        self.emp = make_emp()
        self.superuser = User.objects.create_superuser('root', 'root@example.com', 'pw')

    def test_home_page_renders_with_action_buttons_for_superuser(self):
        self.client.force_login(self.superuser)
        response = self.client.get('/emp/home/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete')
        self.assertContains(response, 'Update')

    def test_attendance_mark_page_renders_for_superuser(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('attendance_mark'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.emp.name)

    def test_leave_queue_page_renders_for_superuser(self):
        LeaveRequest.objects.create(
            employee=self.emp,
            start_date=datetime.date(2026, 8, 1),
            end_date=datetime.date(2026, 8, 3),
            reason='Family event',
        )
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('leave_queue'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.emp.name)

    def test_leave_my_requests_page_renders_for_linked_employee(self):
        employee_user = User.objects.create_user('employee2', password='pw')
        self.emp.user = employee_user
        self.emp.save()
        LeaveRequest.objects.create(
            employee=self.emp,
            start_date=datetime.date(2026, 8, 1),
            end_date=datetime.date(2026, 8, 3),
            reason='Family event',
        )
        self.client.force_login(employee_user)
        response = self.client.get(reverse('leave_my_requests'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Family event')

    def test_attendance_history_page_renders_for_superuser(self):
        Attendance.objects.create(employee=self.emp, date=datetime.date(2026, 1, 1))
        self.client.force_login(self.superuser)
        response = self.client.get(f"{reverse('attendance_history')}?emp_id={self.emp.id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.emp.name)


class DashboardViewTests(TestCase):
    def setUp(self):
        self.eng1 = make_emp(name='Alice', emp_id='D1', role=Emp.Role.SOFTWARE_ENGINEER, working=True)
        self.eng2 = make_emp(name='Bob', emp_id='D2', role=Emp.Role.SOFTWARE_ENGINEER, working=True)
        self.qa1 = make_emp(name='Carl', emp_id='D3', role=Emp.Role.QA_ENGINEER, working=False)

        Testimonial.objects.create(name='X', testimonial='great', rating=4, picture='testimonials/x.jpg')
        Testimonial.objects.create(name='Y', testimonial='ok', rating=2, picture='testimonials/y.jpg')

        LeaveRequest.objects.create(
            employee=self.eng1,
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 1, 2),
            reason='Trip',
        )

        today = datetime.date(2026, 7, 24)
        Attendance.objects.create(employee=self.eng1, date=today, status=Attendance.Status.PRESENT)
        Attendance.objects.create(employee=self.eng2, date=today, status=Attendance.Status.ABSENT)

        self.viewer = User.objects.create_user('viewer', password='pw')
        self.viewer.user_permissions.add(Permission.objects.get(codename='view_dashboard'))
        self.outsider = User.objects.create_user('outsider', password='pw')

    def test_requires_permission(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_redirected(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_aggregates_correctly(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

        stats = response.context['stats']
        self.assertEqual(stats['total_employees'], 3)
        self.assertEqual(stats['working_employees'], 2)
        self.assertEqual(stats['pending_leaves'], 1)
        self.assertEqual(stats['avg_rating'], 3.0)
        self.assertEqual(stats['testimonial_count'], 2)

        chart_data = response.context['chart_data']
        headcount = dict(zip(chart_data['headcount']['labels'], chart_data['headcount']['data']))
        self.assertEqual(headcount.get(self.eng1.get_role_display()), 2)
        self.assertNotIn(self.qa1.get_role_display(), headcount)  # Carl isn't `working`, excluded from headcount

    def test_role_filter_scopes_employee_count(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse('dashboard'), {'role': self.qa1.role})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['total_employees'], 1)


class HtmxInteractionTests(TestCase):
    def setUp(self):
        self.emp = make_emp()
        self.superuser = User.objects.create_superuser('root2', 'root2@example.com', 'pw')

    def test_emp_home_htmx_returns_partial_only(self):
        self.client.force_login(self.superuser)
        response = self.client.get('/emp/home/', HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.emp.name)
        self.assertNotContains(response, '<nav class="navbar')

    def test_delete_emp_htmx_returns_empty_body_and_deletes(self):
        self.client.force_login(self.superuser)
        response = self.client.delete(f'/emp/delete-emp/{self.emp.id}', HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')
        self.assertFalse(Emp.objects.filter(id=self.emp.id).exists())

    def test_leave_approve_htmx_returns_empty_body(self):
        leave = LeaveRequest.objects.create(
            employee=self.emp,
            start_date=datetime.date(2026, 8, 1),
            end_date=datetime.date(2026, 8, 3),
            reason='Trip',
        )
        self.client.force_login(self.superuser)
        response = self.client.post(f'/emp/leave/{leave.id}/approve/', HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.Status.APPROVED)

    def test_leave_approve_htmx_double_approve_shows_error_row(self):
        leave = LeaveRequest.objects.create(
            employee=self.emp,
            start_date=datetime.date(2026, 8, 1),
            end_date=datetime.date(2026, 8, 3),
            reason='Trip',
            status=LeaveRequest.Status.APPROVED,
        )
        self.client.force_login(self.superuser)
        response = self.client.post(f'/emp/leave/{leave.id}/approve/', HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'text-danger', response.content)

    def test_dashboard_htmx_returns_partial_only(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('dashboard'), HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="role"')
        self.assertContains(response, 'headcountChart')
