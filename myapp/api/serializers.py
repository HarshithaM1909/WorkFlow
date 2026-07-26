from rest_framework import serializers

from emp.models import Attendance, Emp, Feedback, LeaveRequest, Testimonial


class EmpSerializer(serializers.ModelSerializer):
    class Meta:
        model = Emp
        fields = ['id', 'name', 'emp_id', 'phone', 'address', 'working', 'role', 'user']
        read_only_fields = ['user']


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)

    class Meta:
        model = Attendance
        fields = ['id', 'employee', 'employee_name', 'date', 'status', 'marked_by']
        read_only_fields = ['marked_by']


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'employee_name', 'start_date', 'end_date', 'reason',
            'status', 'reviewed_by', 'reviewed_at', 'review_note', 'created_at',
        ]
        read_only_fields = ['employee', 'status', 'reviewed_by', 'reviewed_at', 'review_note', 'created_at']

    def validate(self, data):
        start = data.get('start_date') or getattr(self.instance, 'start_date', None)
        end = data.get('end_date') or getattr(self.instance, 'end_date', None)
        if start and end and end < start:
            raise serializers.ValidationError("End date cannot be before start date.")
        return data


class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = ['id', 'name', 'testimonial', 'picture', 'rating']


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'email', 'name', 'feedback', 'created_at']
        read_only_fields = ['created_at']
