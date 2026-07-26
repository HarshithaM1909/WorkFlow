from rest_framework.routers import DefaultRouter

from .views import (
    AttendanceViewSet,
    EmpViewSet,
    FeedbackViewSet,
    LeaveRequestViewSet,
    TestimonialViewSet,
)

router = DefaultRouter()
router.register('employees', EmpViewSet, basename='employee')
router.register('attendance', AttendanceViewSet, basename='attendance')
router.register('leave-requests', LeaveRequestViewSet, basename='leaverequest')
router.register('testimonials', TestimonialViewSet, basename='testimonial')
router.register('feedback', FeedbackViewSet, basename='feedback')

urlpatterns = router.urls
