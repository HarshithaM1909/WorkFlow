import logging

from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from .models import Emp,Testimonial,Feedback,Attendance,LeaveRequest
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from .form import EmpForm, FeedbackForm, TestimonialForm, LeaveRequestForm
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from django.utils.html import format_html
import datetime

logger = logging.getLogger(__name__)


# Create your views here.
@login_required(login_url='/login')
def emp_home(request):
    query = request.GET.get('search')
    if query:
        emps = Emp.objects.filter(Q(name__icontains=query) | Q(emp_id__icontains=query)).order_by('id')
    else:
        emps = Emp.objects.all().order_by('id')

    paginator = Paginator(emps, 15)
    emps = paginator.get_page(request.GET.get('page'))

    if request.htmx:
        return render(request, 'emp/partials/emp_table.html', {'emps': emps})
    return render(request,'emp/home.html', {
        'emps': emps
    })

@login_required(login_url='/login')
@permission_required('emp.add_emp',login_url="/login", raise_exception=True)
def add_emp(request):
    if request.method=='POST':
        form = EmpForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/emp/home/')
    else:
        form = EmpForm()
    return render(request,'emp/add_emp.html',{'form': form})

@login_required(login_url='/login')
@permission_required('emp.delete_emp', login_url="/login", raise_exception=True)
def delete_emp(request,emp_id):
    emp=get_object_or_404(Emp, id=emp_id)
    if request.method in ('POST', 'DELETE'):
        emp.delete()
        if request.htmx:
            return HttpResponse('')
        return redirect('/emp/home/')
    return render(request, 'emp/delete_emp_confirm.html', {'emp': emp})

@login_required(login_url='/login')
@permission_required('emp.change_emp', login_url="/login", raise_exception=True)
def update_emp(request, emp_id):
    emp = get_object_or_404(Emp, pk=emp_id)

    if request.method == "POST":
        form = EmpForm(request.POST, instance=emp)
        if form.is_valid():
            form.save()
            return redirect('/emp/home/')
    else:
        form = EmpForm(instance=emp)

    return render(request, 'emp/update_emp.html', {
        'emp': emp,
        'form': form,
    })
@login_required(login_url='/login')
def testimonials(request):
    if request.method == 'POST':
        form = TestimonialForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                t = Testimonial()
                t.name = form.cleaned_data['name']
                t.testimonial = form.cleaned_data['testimonial']
                t.rating = form.cleaned_data['rating']
                if form.cleaned_data.get('picture'):
                    t.picture = form.cleaned_data.get('picture')
                t.save()
                return redirect(request.path_info)
            except Exception:
                logger.exception("Failed to save testimonial")
                messages.error(request, "Something went wrong saving your testimonial. Please try again.")
        else:
            logger.info("Testimonial form validation failed: %s", form.errors)
    else:
        form = TestimonialForm()
    
    testi = Testimonial.objects.all()
    return render(request, 'emp/testimonials.html', {
        'testi': testi,
        'form': form,
    })



@login_required(login_url='/login')
def feedback(request):
    if request.method=="POST":
        form=FeedbackForm(request.POST)
        if form.is_valid():
            Feedback.objects.create(
                email=form.cleaned_data['email'],
                name=form.cleaned_data['name'],
                feedback=form.cleaned_data['feedback']
            )
            messages.success(request, "Thank you for your feedback!")
            return redirect('/emp/feedback/')
    else:
        form=FeedbackForm()
    return render(request,'emp/feedback.html', {'form':form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    return redirect('home')


@login_required(login_url='/login')
@permission_required('emp.add_attendance', login_url="/login", raise_exception=True)
def attendance_mark(request):
    date_str = request.GET.get('date') or request.POST.get('date')
    try:
        selected_date = datetime.date.fromisoformat(date_str) if date_str else timezone.localdate()
    except ValueError:
        selected_date = timezone.localdate()

    if request.method == 'POST':
        emps = Emp.objects.filter(working=True)
        for emp in emps:
            status = request.POST.get(f'status_{emp.id}')
            if status in Attendance.Status.values:
                Attendance.objects.update_or_create(
                    employee=emp,
                    date=selected_date,
                    defaults={'status': status, 'marked_by': request.user},
                )
        messages.success(request, f"Attendance saved for {selected_date}.")
        return redirect(f"/emp/attendance/mark/?date={selected_date}")

    emps = Emp.objects.filter(working=True).order_by('name')
    existing = {
        a.employee_id: a.status
        for a in Attendance.objects.filter(date=selected_date, employee__in=emps)
    }
    rows = [
        {'emp': emp, 'status': existing.get(emp.id, Attendance.Status.PRESENT)}
        for emp in emps
    ]
    return render(request, 'emp/attendance_mark.html', {
        'rows': rows,
        'selected_date': selected_date,
        'statuses': Attendance.Status.choices,
    })


@login_required(login_url='/login')
def attendance_history(request):
    emp_id = request.GET.get('emp_id')
    if emp_id and (request.user.has_perm('emp.view_attendance') or request.user.is_superuser):
        employee = Emp.objects.filter(id=emp_id).first()
    else:
        employee = getattr(request.user, 'employee_profile', None)

    records = Attendance.objects.filter(employee=employee) if employee else Attendance.objects.none()
    return render(request, 'emp/attendance_history.html', {
        'employee': employee,
        'records': records,
    })


@login_required(login_url='/login')
def leave_request_create(request):
    employee = getattr(request.user, 'employee_profile', None)
    if employee is None:
        messages.error(request, "Your account isn't linked to an employee profile. Ask an admin to link it before requesting leave.")
        return redirect('/emp/home/')

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = employee
            leave.full_clean()
            leave.save()
            messages.success(request, "Leave request submitted.")
            return redirect('/emp/leave/my-requests/')
    else:
        form = LeaveRequestForm()

    return render(request, 'emp/leave_request_form.html', {'form': form})


@login_required(login_url='/login')
def leave_my_requests(request):
    employee = getattr(request.user, 'employee_profile', None)
    requests_qs = employee.leave_requests.all() if employee else LeaveRequest.objects.none()
    return render(request, 'emp/leave_my_requests.html', {'leave_requests': requests_qs})


@login_required(login_url='/login')
@permission_required('emp.approve_leaverequest', login_url="/login", raise_exception=True)
def leave_queue(request):
    pending = LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING).select_related('employee')
    return render(request, 'emp/leave_queue.html', {'leave_requests': pending})


@login_required(login_url='/login')
@permission_required('emp.approve_leaverequest', login_url="/login", raise_exception=True)
def leave_approve(request, pk):
    if request.method == 'POST':
        leave = LeaveRequest.objects.get(pk=pk)
        try:
            leave.approve(request.user)
            if request.htmx:
                return HttpResponse('')
            messages.success(request, f"Approved leave for {leave.employee.name}.")
        except ValueError as e:
            if request.htmx:
                return HttpResponse(
                    format_html('<tr><td colspan="5" class="text-danger">{}</td></tr>', str(e))
                )
            messages.error(request, str(e))
    return redirect('/emp/leave/queue/')


@login_required(login_url='/login')
@permission_required('emp.approve_leaverequest', login_url="/login", raise_exception=True)
def leave_reject(request, pk):
    if request.method == 'POST':
        leave = LeaveRequest.objects.get(pk=pk)
        try:
            leave.reject(request.user, note=request.POST.get('note', ''))
            if request.htmx:
                return HttpResponse('')
            messages.success(request, f"Rejected leave for {leave.employee.name}.")
        except ValueError as e:
            if request.htmx:
                return HttpResponse(
                    format_html('<tr><td colspan="5" class="text-danger">{}</td></tr>', str(e))
                )
            messages.error(request, str(e))
    return redirect('/emp/leave/queue/')


@login_required(login_url='/login')
@permission_required('emp.view_dashboard', login_url="/login", raise_exception=True)
def dashboard(request):
    selected_role = request.GET.get('role') or ''
    try:
        days = int(request.GET.get('days', 30))
    except ValueError:
        days = 30
    days = max(1, min(days, 180))

    emps = Emp.objects.all()
    if selected_role:
        emps = emps.filter(role=selected_role)

    role_labels = dict(Emp.Role.choices)

    headcount_qs = (
        Emp.objects.filter(working=True)
        .values('role')
        .annotate(count=Count('id'))
        .order_by('role')
    )
    headcount_labels = [role_labels.get(row['role'], 'Unassigned') for row in headcount_qs]
    headcount_counts = [row['count'] for row in headcount_qs]

    cutoff = timezone.localdate() - datetime.timedelta(days=days - 1)
    attendance_qs = Attendance.objects.filter(date__gte=cutoff)
    if selected_role:
        attendance_qs = attendance_qs.filter(employee__role=selected_role)
    trend = (
        attendance_qs.values('date')
        .annotate(
            present=Count('id', filter=Q(status=Attendance.Status.PRESENT)),
            absent=Count('id', filter=Q(status=Attendance.Status.ABSENT)),
        )
        .order_by('date')
    )
    trend_labels = [row['date'].isoformat() for row in trend]
    trend_present = [row['present'] for row in trend]
    trend_absent = [row['absent'] for row in trend]

    rating_stats = Testimonial.objects.aggregate(avg_rating=Avg('rating'), count=Count('id'))

    stats = {
        'total_employees': emps.count(),
        'working_employees': emps.filter(working=True).count(),
        'pending_leaves': LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING).count(),
        'avg_rating': round(rating_stats['avg_rating'], 2) if rating_stats['avg_rating'] is not None else None,
        'testimonial_count': rating_stats['count'],
    }

    chart_data = {
        'headcount': {'labels': headcount_labels, 'data': headcount_counts},
        'attendance_trend': {'labels': trend_labels, 'present': trend_present, 'absent': trend_absent},
    }

    context = {
        'stats': stats,
        'chart_data': chart_data,
        'roles': Emp.Role.choices,
        'selected_role': selected_role,
        'days': days,
    }
    if request.htmx:
        return render(request, 'emp/partials/dashboard_content.html', context)
    return render(request, 'emp/dashboard.html', context)
