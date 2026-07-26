from django.contrib import admin
from django.urls import path
from .views import *

urlpatterns = [
    path('',emp_home),
    path('home/',emp_home),
    path('add-emp/',add_emp),
    path('delete-emp/<int:emp_id>',delete_emp),
    path('update-emp/<int:emp_id>',update_emp),
    path('testimonials/',testimonials),
    path('add-testimonials/',testimonials),
    path('feedback/',feedback),
    path('logout/',logout_view),

    path('attendance/mark/', attendance_mark, name='attendance_mark'),
    path('attendance/history/', attendance_history, name='attendance_history'),

    path('leave/request/', leave_request_create, name='leave_request_create'),
    path('leave/my-requests/', leave_my_requests, name='leave_my_requests'),
    path('leave/queue/', leave_queue, name='leave_queue'),
    path('leave/<int:pk>/approve/', leave_approve, name='leave_approve'),
    path('leave/<int:pk>/reject/', leave_reject, name='leave_reject'),

    path('dashboard/', dashboard, name='dashboard'),
]


