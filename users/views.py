from django.http import Http404
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.cache import cache
from functools import wraps
from django.core.exceptions import PermissionDenied, ValidationError
from .models import CustomUser, School, Department, FileUpload, Program, AboutContent
from .forms import FileUploadForm
from django.http import JsonResponse

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser or request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return _wrapped_view
    return decorator

@login_required
@role_required(['SUPERADMIN', 'HOI', 'ADMIN'])
def register_view(request):
    # Filter schools and departments based on user's role
    if request.user.is_superuser or request.user.role == 'SUPERADMIN':
        schools = School.objects.all()
        departments = Department.objects.all()
        allowed_roles = ["HOI", "ADMIN", "MENTOR"]
    elif request.user.role == 'HOI':
        schools = School.objects.filter(id=request.user.school.id)
        departments = Department.objects.filter(school=request.user.school)
        allowed_roles = ["ADMIN", "MENTOR"]
    else:  # ADMIN
        schools = School.objects.filter(id=request.user.school.id)
        departments = Department.objects.filter(school=request.user.school)
        allowed_roles = ["MENTOR"]

    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        role = request.POST.get('role')
        school_id = request.POST.get('school')
        department_id = request.POST.get('department')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        if not all([employee_id, email, password1, password2, role]):
            messages.error(request, 'All fields are required!')
            return redirect('users:register')

        if password1 != password2:
            messages.error(request, 'Passwords do not match!')
            return redirect('users:register')

        try:
            if CustomUser.objects.filter(employee_id=employee_id).exists():
                messages.error(request, 'Employee ID already exists!')
                return redirect('users:register')

            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists!')
                return redirect('users:register')

            # Get school and department objects
            try:
                school = School.objects.get(id=school_id) if school_id else None
                department = Department.objects.get(id=department_id) if department_id else None
            except (School.DoesNotExist, Department.DoesNotExist):
                messages.error(request, 'Invalid school or department selected!')
                return redirect('users:register')

            # Create new user
            user = CustomUser.objects.create_user(
                employee_id=employee_id,
                email=email,
                password=password1,  # password will be hashed automatically
                role=role,
                first_name=first_name,
                last_name=last_name,
                school=school,
                department=department
            )

            messages.success(request, f'Registration successful! Please login with your Employee ID: {employee_id}')
            return redirect('users:login')

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('users:register')
    
    return render(request, 'users/register.html', {
        'schools': schools,
        'departments': departments,
        'role_choices': [(role, dict(CustomUser.ROLE_CHOICES)[role]) for role in allowed_roles]
    })

from django.views.decorators.csrf import csrf_protect


@csrf_protect
def login_view(request):
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    
    # Get the active about content from cache or database
    about_content = cache.get('about_content')
    if about_content is None:
        about_content = AboutContent.objects.filter(is_active=True).first()
        if about_content:
            cache.set('about_content', about_content, 3600)  # Cache for 1 hour
        
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        password = request.POST.get('password')

        if not employee_id or not password:
            messages.error(request, 'Both Employee ID and password are required.')
            return render(request, 'users/login.html')

        try:
            # First check if user exists
            user_exists = CustomUser.objects.filter(employee_id=employee_id).exists()
            if not user_exists:
                messages.error(request, 'No account found with this Employee ID.')
                return render(request, 'users/login.html')

            # Try to authenticate
            user = authenticate(request, username=employee_id, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.get_full_name() or user.employee_id}!')
                    next_url = request.GET.get('next')
                    return redirect(next_url if next_url else 'users:dashboard')
                else:
                    messages.error(request, 'Your account is not active. Please contact your administrator.')
            else:
                messages.error(request, 'Invalid password.')
        except Exception as e:
            messages.error(request, 'An error occurred during login. Please try again.')
    
    return render(request, 'users/login.html', {'about_content': about_content})





def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('users:login')

# In views.py, modify the dashboard_view function
@login_required
def dashboard_view(request):
    """Display the appropriate dashboard based on user role"""
    print(f"User role detected: {request.user.role}")  # Debugging line
    
    context = {
        'user': request.user,
        'role_display': request.user.get_role_display()
    }
    
    if request.user.is_superuser or request.user.role == 'SUPERADMIN':
        print("Routing to superadmin dashboard")  # Debugging line
        # Get all departments with related information
        departments = Department.objects.all()
        department_info = []
        for dept in departments:
            department_info.append({
                'department': dept,
                'school': dept.school,
                'total_mentors': CustomUser.objects.filter(department=dept, role='MENTOR').count(),
                'total_admins': CustomUser.objects.filter(department=dept, role='ADMIN').count(),
                'total_uploads': FileUpload.objects.filter(department=dept).count(),
                'recent_uploads': FileUpload.objects.filter(department=dept).order_by('-uploaded_at')[:3]
            })

        context.update({
            'schools': School.objects.all(),
            'departments': Department.objects.all(),
            'department_info': department_info,
            'total_users': CustomUser.objects.count(),
            'total_uploads': FileUpload.objects.count(),
            'recent_users': CustomUser.objects.order_by('-date_joined')[:5],
            'recent_uploads': FileUpload.objects.order_by('-uploaded_at')[:5]
        })
        template = 'users/dashboard_superadmin.html'
        
    elif request.user.role == 'HOI':
        print("Routing to HOI dashboard")  # Debugging line
        school = request.user.school
        context.update({
            'school': school,
            'mentors': CustomUser.objects.filter(school=school, role='MENTOR'),
            'recent_uploads': FileUpload.objects.filter(
                school=school
            ).order_by('-uploaded_at')[:10],
            'total_mentors': CustomUser.objects.filter(school=school, role='MENTOR').count(),
            'total_uploads': FileUpload.objects.filter(school=school).count(),
            'school_users': CustomUser.objects.filter(school=school)
        })
        template = 'users/dashboard_hoi.html'
        
    elif request.user.role == 'ADMIN':
        print("Routing to ADMIN dashboard")  # Debugging line
        department = request.user.department
        school = request.user.school
        context.update({
            'department': department,
            'school': school,
            # Department specific data
            'department_mentors': CustomUser.objects.filter(department=department, role='MENTOR'),
            'department_uploads': FileUpload.objects.filter(
                department=department
            ).order_by('-uploaded_at')[:10],
            'department_mentors_count': CustomUser.objects.filter(department=department, role='MENTOR').count(),
            'department_uploads_count': FileUpload.objects.filter(department=department).count(),
            # School wide data
            'school_users': CustomUser.objects.filter(
                school=school
            ).filter(role__in=['MENTOR', 'HOI', 'ADMIN']).order_by('role', 'employee_id'),
            'school_uploads': FileUpload.objects.filter(
                school=school
            ).order_by('-uploaded_at')[:10],
            'school_mentors_count': CustomUser.objects.filter(school=school, role='MENTOR').count(),
            'school_uploads_count': FileUpload.objects.filter(school=school).count()
        })
        template = 'users/dashboard_admin.html'
        
    else:  # MENTOR role
        print("Routing to MENTOR dashboard")  # Debugging line
        context.update({
            'my_uploads': FileUpload.objects.filter(uploaded_by=request.user).order_by('-uploaded_at'),
            'department_uploads': FileUpload.objects.filter(
                department=request.user.department
            ).exclude(uploaded_by=request.user).order_by('-uploaded_at')[:10],
            'department': request.user.department,
            'school': request.user.school
        })
        template = 'users/dashboard_mentor.html'

    return render(request, template, context)




@login_required
@role_required(['HOI', 'ADMIN'])
def edit_user_view(request, user_id):
    try:
        # For HOI: get any user in their school
        # For ADMIN: get any mentor in their department
        if request.user.role == 'HOI':
            user_to_edit = CustomUser.objects.get(id=user_id, school=request.user.school)
        else:  # ADMIN
            user_to_edit = CustomUser.objects.get(id=user_id, department=request.user.department, role='MENTOR')
        
        if request.method == 'POST':
            # Update basic fields
            user_to_edit.email = request.POST.get('email')
            user_to_edit.first_name = request.POST.get('first_name')
            user_to_edit.last_name = request.POST.get('last_name')
            user_to_edit.is_active = request.POST.get('is_active') == 'on'
            
            # Handle department assignment (only for HOI)
            if request.user.role == 'HOI':
                department_id = request.POST.get('department')
                if department_id:
                    try:
                        department = Department.objects.get(id=department_id, school=request.user.school)
                        user_to_edit.department = department
                    except Department.DoesNotExist:
                        messages.error(request, 'Invalid department selected')
                        return redirect('users:edit_user', user_id=user_id)
            
            user_to_edit.save()
            messages.success(request, 'User profile updated successfully!')
            return redirect('users:dashboard')

        # Get departments for HOI users
        departments = []
        if request.user.role == 'HOI':
            departments = Department.objects.filter(school=request.user.school)

        return render(request, 'users/edit_user.html', {
            'user_to_edit': user_to_edit,
            'departments': departments
        })

    except CustomUser.DoesNotExist:
        raise Http404("Mentor not found")



@login_required
def file_upload_view(request):
    context = {}
    
    # Get sections based on user's role
    if request.user.role == 'MENTOR':
        sections = request.user.mentored_sections.all()
    elif request.user.role == 'HOI':
        departments = Department.objects.filter(school=request.user.school)
        context['departments'] = departments
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            description = request.POST.get('description')
            if not all([title, request.FILES.get('file')]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'users/file_upload.html', context)
            
            # Create the file upload
            file_upload = FileUpload.objects.create(
                title=title,
                file=request.FILES['file'],
                description=description,
                uploaded_by=request.user,
                department=request.user.department,
                school=request.user.school
            )
            
            messages.success(request, 'File uploaded successfully!')
            return redirect('users:dashboard')
            
        except Exception as e:
            messages.error(request, f'Error uploading file: {str(e)}')
            return render(request, 'users/file_upload.html', context)
    
    return render(request, 'users/file_upload.html', context)

@login_required
@role_required(['HOI', 'ADMIN'])
def delete_user_view(request, user_id):
    try:
        # For HOI: can delete any user in their school
        # For ADMIN: can only delete mentors in their department
        if request.user.role == 'HOI':
            user_to_delete = CustomUser.objects.get(id=user_id, school=request.user.school)
        else:  # ADMIN
            user_to_delete = CustomUser.objects.get(id=user_id, department=request.user.department, role='MENTOR')
        
        user_name = user_to_delete.get_full_name()
        user_to_delete.delete()
        messages.success(request, f'User {user_name} has been deleted successfully.')
        return redirect('users:dashboard')

    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('users:dashboard')

@login_required
def welcome_view(request):
    """
    A welcome view shown after successful login, displays user info and next steps
    """
    context = {
        'user': request.user,
        'role': request.user.get_role_display(),
        'school': request.user.school.name if request.user.school else None,
        'department': request.user.department.name if request.user.department else None
    }
    return render(request, 'users/welcome.html', context)

@login_required
def delete_file_view(request, file_id):
    """
    Allow users to delete their uploaded files
    """
    try:
        # Get the file upload object
        file_upload = FileUpload.objects.get(id=file_id)
        
        # Check if the user has permission to delete this file
        if request.user == file_upload.uploaded_by or request.user.is_superuser or \
           (request.user.role == 'ADMIN' and request.user.department == file_upload.department) or \
           (request.user.role == 'HOI' and request.user.school == file_upload.school):
            
            # Delete the file
            file_upload.delete()
            messages.success(request, 'File deleted successfully!')
        else:
            messages.error(request, 'You do not have permission to delete this file.')
            
    except FileUpload.DoesNotExist:
        messages.error(request, 'File not found.')
    
    # Redirect back to the dashboard
    return redirect('users:dashboard')



@login_required
def get_schools(request):
    schools = list(School.objects.filter(is_active=True).values('id', 'name'))
    return JsonResponse({'schools': schools})

@login_required
@role_required(['SUPERADMIN', 'HOI', 'ADMIN'])
def get_departments(request):
    school_id = request.GET.get('school_id')
    departments = []
    if school_id:
        try:
            school = School.objects.get(id=school_id, is_active=True)
            departments = list(Department.objects.filter(
                school=school,
                is_active=True
            ).order_by('name').values('id', 'name', 'code'))
        except School.DoesNotExist:
            pass
    return JsonResponse({'departments': departments})

@login_required
@role_required(['SUPERADMIN', 'HOI', 'ADMIN'])
def get_mentors(request):
    department_id = request.GET.get('department_id')
    mentors = []
    if department_id:
        mentors = list(CustomUser.objects.filter(
            department_id=department_id,
            role='MENTOR',
            is_active=True
        ).order_by('first_name', 'last_name').values(
            'id', 'first_name', 'last_name', 'employee_id'
        ))
    return JsonResponse({'mentors': mentors})

def change_password_view(request):
    """
    Allow users to change their password
    """
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        if not all([old_password, new_password1, new_password2]):
            messages.error(request, 'All password fields are required')
            return redirect('users:change_password')

        if new_password1 != new_password2:
            messages.error(request, 'New passwords do not match')
            return redirect('users:change_password')

        if len(new_password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return redirect('users:change_password')

        # Check if old password is correct
        user = request.user
        if not user.check_password(old_password):
            messages.error(request, 'Current password is incorrect')
            return redirect('users:change_password')

        # Set the new password
        user.set_password(new_password1)
        user.save()

        # Update the session
        login(request, user)
        
        messages.success(request, 'Your password was successfully changed!')
        return redirect('users:dashboard')

    return render(request, 'users/change_password.html')




def role_required(allowed_roles):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser or request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return _wrapped_view
    return decorator

@login_required
@role_required(['SUPERADMIN', 'HOI', 'ADMIN'])
def get_departments(request):
    school_id = request.GET.get('school_id')
    departments = []
    if school_id:
        try:
            school = School.objects.get(id=school_id, is_active=True)
            departments = list(Department.objects.filter(
                school=school,
                is_active=True
            ).order_by('name').values('id', 'name', 'code'))
        except School.DoesNotExist:
            pass
    return JsonResponse({'departments': departments})

@login_required
@role_required(['SUPERADMIN', 'HOI', 'ADMIN'])
def get_mentors(request):
    department_id = request.GET.get('department_id')
    mentors = []
    if department_id:
        mentors = list(CustomUser.objects.filter(
            department_id=department_id,
            role='MENTOR',
            is_active=True
        ).order_by('first_name', 'last_name').values(
            'id', 'first_name', 'last_name', 'employee_id'
        ))
    return JsonResponse({'mentors': mentors})
