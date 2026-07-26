import datetime
from io import BytesIO

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from emp.models import Attendance, Emp, LeaveRequest, Testimonial


def make_emp(**kwargs):
    defaults = {
        'name': 'Jane Doe',
        'emp_id': 'E200',
        'phone': '9999999999',
        'address': 'Somewhere',
        'working': True,
    }
    defaults.update(kwargs)
    return Emp.objects.create(**defaults)


def make_test_image():
    buf = BytesIO()
    Image.new('RGB', (10, 10), color='red').save(buf, format='JPEG')
    buf.seek(0)
    return SimpleUploadedFile('test.jpg', buf.read(), content_type='image/jpeg')


class EmpApiTests(TestCase):
    def setUp(self):
        self.emp = make_emp()
        self.viewer = User.objects.create_user('viewer', password='pw')
        self.adder = User.objects.create_user('adder', password='pw')
        self.adder.user_permissions.add(Permission.objects.get(codename='add_emp'))

    def test_anonymous_cannot_list(self):
        response = self.client.get('/api/v1/employees/')
        self.assertIn(response.status_code, (401, 403))

    def test_authenticated_user_can_list(self):
        self.client.force_login(self.viewer)
        response = self.client.get('/api/v1/employees/')
        self.assertEqual(response.status_code, 200)

    def test_create_requires_add_emp_permission(self):
        self.client.force_login(self.viewer)
        response = self.client.post('/api/v1/employees/', {
            'name': 'New', 'emp_id': 'E300', 'phone': '1234567890',
            'address': 'X', 'working': True, 'role': Emp.Role.QA_ENGINEER,
        })
        self.assertEqual(response.status_code, 403)

    def test_create_succeeds_with_permission(self):
        self.client.force_login(self.adder)
        response = self.client.post('/api/v1/employees/', {
            'name': 'New', 'emp_id': 'E300', 'phone': '1234567890',
            'address': 'X', 'working': True, 'role': Emp.Role.QA_ENGINEER,
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Emp.objects.filter(emp_id='E300').exists())

    def test_filter_by_role(self):
        make_emp(name='Other', emp_id='E400', role=Emp.Role.QA_ENGINEER)
        self.emp.role = Emp.Role.SOFTWARE_ENGINEER
        self.emp.save()
        self.client.force_login(self.viewer)
        response = self.client.get('/api/v1/employees/', {'role': Emp.Role.SOFTWARE_ENGINEER})
        self.assertEqual(response.status_code, 200)
        names = [row['name'] for row in response.json()]
        self.assertIn('Jane Doe', names)
        self.assertNotIn('Other', names)


class AttendanceApiTests(TestCase):
    def setUp(self):
        self.emp = make_emp()
        self.other_emp = make_emp(name='Other', emp_id='E500')
        self.employee_user = User.objects.create_user('employee', password='pw')
        self.emp.user = self.employee_user
        self.emp.save()

        self.manager = User.objects.create_user('manager', password='pw')
        self.manager.user_permissions.add(Permission.objects.get(codename='view_attendance'))
        self.manager.user_permissions.add(Permission.objects.get(codename='add_attendance'))

        Attendance.objects.create(employee=self.emp, date=datetime.date(2026, 1, 1), status='PRESENT')
        Attendance.objects.create(employee=self.other_emp, date=datetime.date(2026, 1, 1), status='ABSENT')

    def test_employee_only_sees_own_attendance(self):
        self.client.force_login(self.employee_user)
        response = self.client.get('/api/v1/attendance/')
        self.assertEqual(response.status_code, 200)
        rows = response.json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['employee'], self.emp.id)

    def test_manager_sees_all_attendance(self):
        self.client.force_login(self.manager)
        response = self.client.get('/api/v1/attendance/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_create_sets_marked_by(self):
        self.client.force_login(self.manager)
        response = self.client.post('/api/v1/attendance/', {
            'employee': self.emp.id, 'date': '2026-02-01', 'status': 'PRESENT',
        })
        self.assertEqual(response.status_code, 201)
        record = Attendance.objects.get(employee=self.emp, date=datetime.date(2026, 2, 1))
        self.assertEqual(record.marked_by, self.manager)


class LeaveRequestApiTests(TestCase):
    def setUp(self):
        self.emp = make_emp()
        self.employee_user = User.objects.create_user('employee', password='pw')
        self.emp.user = self.employee_user
        self.emp.save()

        self.manager = User.objects.create_user('manager', password='pw')
        self.manager.user_permissions.add(Permission.objects.get(codename='approve_leaverequest'))

        self.lone_user = User.objects.create_user('lone', password='pw')

    def test_create_requires_employee_profile(self):
        self.client.force_login(self.lone_user)
        response = self.client.post('/api/v1/leave-requests/', {
            'start_date': '2026-08-01', 'end_date': '2026-08-03', 'reason': 'Trip',
        })
        self.assertEqual(response.status_code, 400)

    def test_employee_can_create_own_leave_request(self):
        self.client.force_login(self.employee_user)
        response = self.client.post('/api/v1/leave-requests/', {
            'start_date': '2026-08-01', 'end_date': '2026-08-03', 'reason': 'Trip',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(LeaveRequest.objects.get().employee, self.emp)

    def test_end_before_start_rejected(self):
        self.client.force_login(self.employee_user)
        response = self.client.post('/api/v1/leave-requests/', {
            'start_date': '2026-08-10', 'end_date': '2026-08-01', 'reason': 'Trip',
        })
        self.assertEqual(response.status_code, 400)

    def test_non_manager_cannot_approve(self):
        leave = LeaveRequest.objects.create(
            employee=self.emp, start_date=datetime.date(2026, 8, 1),
            end_date=datetime.date(2026, 8, 3), reason='Trip',
        )
        self.client.force_login(self.employee_user)
        response = self.client.post(f'/api/v1/leave-requests/{leave.id}/approve/')
        self.assertEqual(response.status_code, 403)

    def test_manager_can_approve(self):
        leave = LeaveRequest.objects.create(
            employee=self.emp, start_date=datetime.date(2026, 8, 1),
            end_date=datetime.date(2026, 8, 3), reason='Trip',
        )
        self.client.force_login(self.manager)
        response = self.client.post(f'/api/v1/leave-requests/{leave.id}/approve/')
        self.assertEqual(response.status_code, 200)
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.Status.APPROVED)

    def test_double_approve_returns_400(self):
        leave = LeaveRequest.objects.create(
            employee=self.emp, start_date=datetime.date(2026, 8, 1),
            end_date=datetime.date(2026, 8, 3), reason='Trip',
            status=LeaveRequest.Status.APPROVED,
        )
        self.client.force_login(self.manager)
        response = self.client.post(f'/api/v1/leave-requests/{leave.id}/approve/')
        self.assertEqual(response.status_code, 400)

    def test_employee_cannot_see_others_requests(self):
        other_emp = make_emp(name='Other', emp_id='E600')
        LeaveRequest.objects.create(
            employee=other_emp, start_date=datetime.date(2026, 8, 1),
            end_date=datetime.date(2026, 8, 3), reason='Trip',
        )
        self.client.force_login(self.employee_user)
        response = self.client.get('/api/v1/leave-requests/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)


class TestimonialApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('someone', password='pw')

    def test_anonymous_cannot_list(self):
        response = self.client.get('/api/v1/testimonials/')
        self.assertIn(response.status_code, (401, 403))

    def test_authenticated_user_can_create_and_list(self):
        self.client.force_login(self.user)
        response = self.client.post('/api/v1/testimonials/', {
            'name': 'A', 'testimonial': 'Great service!', 'rating': 5, 'picture': make_test_image(),
        })
        self.assertEqual(response.status_code, 201)
        response = self.client.get('/api/v1/testimonials/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_update_requires_change_permission(self):
        testimonial = Testimonial.objects.create(name='A', testimonial='Great!', rating=5, picture='testimonials/x.jpg')
        self.client.force_login(self.user)
        response = self.client.patch(
            f'/api/v1/testimonials/{testimonial.id}/',
            {'rating': 1},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)


class FeedbackApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('someone', password='pw')

    def test_anonymous_cannot_create(self):
        response = self.client.post('/api/v1/feedback/', {
            'email': 'a@example.com', 'name': 'A', 'feedback': 'Nice app!',
        })
        self.assertIn(response.status_code, (401, 403))

    def test_authenticated_user_can_create(self):
        self.client.force_login(self.user)
        response = self.client.post('/api/v1/feedback/', {
            'email': 'a@example.com', 'name': 'A', 'feedback': 'Nice app!',
        })
        self.assertEqual(response.status_code, 201)

    def test_list_not_exposed(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/v1/feedback/')
        self.assertEqual(response.status_code, 405)
