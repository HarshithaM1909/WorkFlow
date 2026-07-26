from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from emp.models import Attendance, Emp, Feedback, LeaveRequest, Testimonial

from .serializers import (
    AttendanceSerializer,
    EmpSerializer,
    FeedbackSerializer,
    LeaveRequestSerializer,
    TestimonialSerializer,
)


class EmpViewSet(viewsets.ModelViewSet):
    """Mirrors the web app's Emp CRUD: any logged-in user can view,
    add/change/delete require the matching Django model permission
    (same `emp.add_emp` / `emp.change_emp` / `emp.delete_emp` used by the views)."""
    queryset = Emp.objects.all().order_by('id')
    serializer_class = EmpSerializer
    filterset_fields = ['role', 'working']
    search_fields = ['name', 'emp_id']


class AttendanceViewSet(viewsets.ModelViewSet):
    """GET is open to any logged-in user but scoped to their own record
    unless they hold `emp.view_attendance` or are a superuser - mirrors
    attendance_history's scoping, since DjangoModelPermissions alone has
    no row-level concept."""
    serializer_class = AttendanceSerializer
    filterset_fields = ['employee', 'date', 'status']

    def get_queryset(self):
        qs = Attendance.objects.select_related('employee').all()
        user = self.request.user
        if user.has_perm('emp.view_attendance') or user.is_superuser:
            return qs
        employee = getattr(user, 'employee_profile', None)
        return qs.filter(employee=employee) if employee else qs.none()

    def perform_create(self, serializer):
        serializer.save(marked_by=self.request.user)


class LeaveRequestViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """No generic update/destroy - the only state transitions are the
    approve/reject actions below, which reuse LeaveRequest.approve()/reject()
    so the API and the leave_approve/leave_reject web views share one
    source of truth for the guard against double-processing."""
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'employee']

    def get_queryset(self):
        qs = LeaveRequest.objects.select_related('employee').all()
        user = self.request.user
        if user.has_perm('emp.approve_leaverequest') or user.is_superuser:
            return qs
        employee = getattr(user, 'employee_profile', None)
        return qs.filter(employee=employee) if employee else qs.none()

    def perform_create(self, serializer):
        employee = getattr(self.request.user, 'employee_profile', None)
        if employee is None:
            raise ValidationError("Your account isn't linked to an employee profile.")
        serializer.save(employee=employee)

    def _check_reviewer(self, request):
        return request.user.has_perm('emp.approve_leaverequest') or request.user.is_superuser

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        if not self._check_reviewer(request):
            return Response({'detail': 'Not permitted.'}, status=status.HTTP_403_FORBIDDEN)
        leave = self.get_object()
        try:
            leave.approve(request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LeaveRequestSerializer(leave).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        if not self._check_reviewer(request):
            return Response({'detail': 'Not permitted.'}, status=status.HTTP_403_FORBIDDEN)
        leave = self.get_object()
        try:
            leave.reject(request.user, note=request.data.get('note', ''))
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LeaveRequestSerializer(leave).data)


class TestimonialViewSet(viewsets.ModelViewSet):
    """list/retrieve/create only require login (matches the `testimonials`
    view's plain @login_required); update/destroy have no web equivalent,
    so they fall back to DjangoModelPermissions as an admin-moderation
    control rather than being open to any logged-in user."""
    queryset = Testimonial.objects.all().order_by('-id')
    serializer_class = TestimonialSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'create'):
            return [permissions.IsAuthenticated()]
        return [permissions.DjangoModelPermissions()]


class FeedbackViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Create-only, matching the web `feedback` view. No list/retrieve:
    Feedback carries an email address, and there's no admin-list-only
    equivalent surfaced anywhere but Django admin."""
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
