from django.contrib import admin
from .models import Emp,Testimonial,Feedback,Attendance,LeaveRequest

# Register your models here.
class EmpAdmin(admin.ModelAdmin):
    list_display=('name','working','emp_id','phone','role','user')
    list_filter=('role','working')
    search_fields=('name','role')

class FeedbackAdmin(admin.ModelAdmin):
    list_display=('name','email','created_at')
    search_fields=('name','email','feedback')

class AttendanceAdmin(admin.ModelAdmin):
    list_display=('employee','date','status','marked_by')
    list_filter=('status','date')
    search_fields=('employee__name',)

class LeaveRequestAdmin(admin.ModelAdmin):
    list_display=('employee','start_date','end_date','status','reviewed_by','reviewed_at')
    list_filter=('status',)
    search_fields=('employee__name','reason')
    actions=['approve_selected','reject_selected']

    @admin.action(description='Approve selected pending leave requests')
    def approve_selected(self, request, queryset):
        for leave in queryset.filter(status=LeaveRequest.Status.PENDING):
            leave.approve(request.user)

    @admin.action(description='Reject selected pending leave requests')
    def reject_selected(self, request, queryset):
        for leave in queryset.filter(status=LeaveRequest.Status.PENDING):
            leave.reject(request.user)

admin.site.register(Emp,EmpAdmin)
admin.site.register(Testimonial)
admin.site.register(Feedback,FeedbackAdmin)
admin.site.register(Attendance,AttendanceAdmin)
admin.site.register(LeaveRequest,LeaveRequestAdmin)


