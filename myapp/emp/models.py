from django.conf import settings
from django.db import models
from django.utils import timezone


# Create your models here.
class Emp(models.Model):
    class Role(models.TextChoices):
        SOFTWARE_ENGINEER = "SOFTWARE_ENGINEER", "Software Engineer"
        SENIOR_SOFTWARE_ENGINEER = "SENIOR_SOFTWARE_ENGINEER", "Senior Software Engineer"
        QA_ENGINEER = "QA_ENGINEER", "QA Engineer"
        DEVOPS_ENGINEER = "DEVOPS_ENGINEER", "DevOps Engineer"
        TEAM_LEAD = "TEAM_LEAD", "Team Lead"
        PROJECT_MANAGER = "PROJECT_MANAGER", "Project Manager"
        HR = "HR", "HR"
        SYSTEM_ADMINISTRATOR = "SYSTEM_ADMINISTRATOR", "System Administrator"

    name=models.CharField(max_length=200)
    emp_id=models.CharField(max_length=200, unique=True)
    phone=models.CharField(max_length=10)
    address=models.CharField(max_length=150)
    working=models.BooleanField(default=True)
    role=models.CharField(max_length=30, choices=Role.choices, blank=True, default='')
    user=models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='employee_profile',
    )

    class Meta:
        permissions = [
            ("view_dashboard", "Can view analytics dashboard"),
        ]

    def __str__(self):
        return self.name


class Testimonial(models.Model):
    name=models.CharField(max_length=200)
    testimonial=models.TextField()
    picture=models.ImageField(upload_to="testimonials/")
    rating=models.IntegerField()

    def __str__(self):
        return self.testimonial 

class Feedback(models.Model):
    email = models.EmailField()
    name = models.CharField(max_length=200)
    feedback = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.name}"


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        HALF_DAY = "HALF_DAY", "Half Day"
        ON_LEAVE = "ON_LEAVE", "On Leave"

    employee = models.ForeignKey(Emp, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attendance_marked",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["employee", "date"], name="unique_attendance_per_day"),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee.name} - {self.date} - {self.get_status_display()}"


class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    employee = models.ForeignKey(Emp, on_delete=models.CASCADE, related_name="leave_requests")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leave_requests_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("approve_leaverequest", "Can approve or reject leave requests"),
        ]

    def __str__(self):
        return f"{self.employee.name}: {self.start_date} to {self.end_date} ({self.status})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")

    def approve(self, reviewer):
        if self.status != self.Status.PENDING:
            raise ValueError(f"Cannot approve a leave request that is already {self.status}.")
        self.status = self.Status.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()

    def reject(self, reviewer, note=""):
        if self.status != self.Status.PENDING:
            raise ValueError(f"Cannot reject a leave request that is already {self.status}.")
        self.status = self.Status.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_note = note
        self.save()
