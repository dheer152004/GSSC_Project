from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from users.decorators import role_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from .models import ExcelFile, SheetCategory
from users.models import School, Department, Program
import pandas as pd
import io

@login_required
@role_required(['SUPERADMIN', 'ADMIN'])
def categorize_list(request):
    """View for listing files that need to be categorized"""
    if request.user.is_superuser:
        excel_files = ExcelFile.objects.all()
    else:
        excel_files = ExcelFile.objects.filter(school=request.user.school)

    context = {
        'excel_files': excel_files,
        'title': 'Categorize Excel Files'
    }
    return render(request, 'excelhandler/categorize_list.html', context)

def view_sheet(request, category_id):
    category = get_object_or_404(SheetCategory, id=category_id)

    # Check permissions
    if not (request.user.is_superuser or
            (request.user.role in ['HOI', 'ADMIN'] and request.user.school == category.school) or
            (request.user.role == 'MENTOR' and request.user.school == category.school and
             request.user.department == category.department)):
        messages.error(request, "You don't have permission to view this sheet.")
        return redirect('excelhandler:subject_analyser')

    try:
        # Read the Excel file
        df = pd.read_excel(category.excel_file.file.path, sheet_name=category.sheet_name)

        # Convert DataFrame to HTML table
        html_table = df.head(50).to_html(classes=['table', 'table-striped', 'table-bordered'],
                                       index=False, escape=False)

        context = {
            'category': category,
            'table_html': html_table,
            'total_rows': len(df),
            'displayed_rows': min(50, len(df))
        }

        return render(request, 'excelhandler/view_sheet_placeholder.html', context)

    except Exception as e:
        messages.error(request, f'Error viewing sheet: {str(e)}')
        return redirect('excelhandler:subject_analyser')

@login_required
@role_required(['SUPERADMIN', 'HOI', 'ADMIN', 'MENTOR'])
def subject_analyser(request):
    # Get categories based on user's role
    if request.user.is_superuser:
        categories = SheetCategory.objects.all()
    elif request.user.role in ['HOI', 'ADMIN']:
        categories = SheetCategory.objects.filter(
            school=request.user.school
        )
    else:  # MENTOR
        # Use the actual School and Department objects
        categories = SheetCategory.objects.filter(
            school=request.user.school,
            department=request.user.department
        )

    # SheetCategory now uses relational fields; avoid legacy string-field lookups.
    has_school_relationships = categories.filter(school__isnull=False).exists()
    schools = School.objects.filter(sheet_categories__in=categories).distinct()
    departments = Department.objects.filter(sheet_categories__in=categories).distinct()

    # Get unique programs, semesters, and year ranges (these are text fields)
    programs = categories.values_list('program', flat=True).distinct()
    semesters = categories.values_list('semester', flat=True).distinct()
    year_ranges = categories.values_list('year_range', flat=True).distinct()

    # Prepare categories with proper fields
    if has_school_relationships:
        categories = categories.select_related('school', 'department')

    context = {
        'page_title': 'Subject Analysis',
        'user': request.user,
        'categories': categories,
        'schools': schools,
        'departments': departments,
        'programs': programs,
        'semesters': semesters,
        'year_ranges': year_ranges,
        'using_relationships': has_school_relationships
    }
    return render(request, 'excelhandler/subject_analyser_for_aump.html', context)


@login_required
@role_required(['SUPERADMIN', 'HOI', 'ADMIN', 'MENTOR'])
def student_analyser(request):
    # Get categories based on user's role
    if request.user.is_superuser:
        categories = SheetCategory.objects.all()
        # For superuser, get all schools
        schools = School.objects.all()
        departments = Department.objects.all()
    elif request.user.role in ['HOI', 'ADMIN']:
        categories = SheetCategory.objects.filter(school=request.user.school)
        schools = School.objects.filter(id=request.user.school.id)
        if request.user.role == 'HOI':
            # HOI can see all departments in their school
            departments = Department.objects.filter(school=request.user.school)
        else:
            # ADMIN can only see their department
            departments = Department.objects.filter(id=request.user.department.id)
    else:  # MENTOR
        categories = SheetCategory.objects.filter(
            school=request.user.school,
            department=request.user.department
        )
        schools = School.objects.filter(id=request.user.school.id)
        departments = Department.objects.filter(id=request.user.department.id)

    # Get unique values for dropdowns from filtered categories
    programs = categories.values_list('program', flat=True).distinct()
    semesters = categories.values_list('semester', flat=True).distinct()
    year_ranges = categories.values_list('year_range', flat=True).distinct()

    context = {
        'page_title': 'Student Analysis',
        'user': request.user,
        'categories': categories.select_related('school', 'department'),
        'schools': schools,
        'departments': departments,
        'programs': programs,
        'semesters': semesters,
        'year_ranges': year_ranges,
        'using_relationships': True
    }
    return render(request, 'excelhandler/student_analyser_for_aump.html', context)

def upload_excel(request):
    if request.method == 'POST':
        if 'excel_file' not in request.FILES:
            messages.error(request, 'Please select a file to upload.')
            return redirect('upload_excel')

        excel_file = request.FILES['excel_file']
        if not excel_file.name.endswith('.xlsx'):
            messages.error(request, 'Please upload a valid Excel file (.xlsx)')
            return redirect('upload_excel')

        try:
            # Read Excel file to get sheet names
            xls = pd.ExcelFile(excel_file)
            sheet_names = xls.sheet_names

            # Save the Excel file with user info
            excel_obj = ExcelFile.objects.create(
                file=excel_file,
                uploaded_by=request.user,
                school=request.user.school if not request.user.is_superuser else None
            )

            # Get schools, departments, and programs based on user's role
            if request.user.is_superuser:
                schools = School.objects.all()
                departments = Department.objects.all()
                programs = Program.objects.all()
            elif request.user.role in ['HOI', 'ADMIN']:
                schools = School.objects.filter(id=request.user.school.id)
                departments = Department.objects.filter(school=request.user.school)
                programs = Program.objects.filter(department__school=request.user.school)
            else:  # MENTOR
                schools = School.objects.filter(id=request.user.school.id)
                departments = Department.objects.filter(id=request.user.department.id)
                programs = Program.objects.filter(department=request.user.department)

            context = {
                'excel_id': excel_obj.id,
                'sheet_names': sheet_names,
                'schools': schools,
                'departments': departments,
                'programs': programs,
                'user': request.user
            }
            return render(request, 'excelhandler/categorize_sheets.html', context)

        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
            return redirect('upload_excel')

    return render(request, 'excelhandler/upload.html')

def categorize_sheets(request, excel_id):
    excel_obj = ExcelFile.objects.get(id=excel_id)

    if request.method == 'POST':
        try:
            # Debug info for POST data
            print("POST data:", request.POST)

            for sheet_name in pd.ExcelFile(excel_obj.file.path).sheet_names:
                if f'program_{sheet_name}' in request.POST:
                    print(f"Processing sheet: {sheet_name}")
                    print(f"School ID: {request.POST[f'school_{sheet_name}']}")
                    print(f"Department ID: {request.POST[f'department_{sheet_name}']}")
                    print(f"Program ID: {request.POST[f'program_{sheet_name}']}")

                    # Get the School and Department objects
                    school = School.objects.get(id=request.POST[f'school_{sheet_name}'])
                    department = Department.objects.get(id=request.POST[f'department_{sheet_name}'])
                    program = request.POST[f'program_{sheet_name}']

                    SheetCategory.objects.create(
                        excel_file=excel_obj,
                        sheet_name=sheet_name,
                        school=school,
                        department=department,
                        program=program.strip(),  # Remove any extra whitespace
                        semester=request.POST[f'semester_{sheet_name}'],
                        year_range=request.POST[f'year_range_{sheet_name}']
                    )
            messages.success(request, 'Sheets categorized successfully!')
            return redirect('excelhandler:upload_excel')
        except (School.DoesNotExist, Department.DoesNotExist) as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('excelhandler:categorize_sheets', excel_id=excel_id)

    # Get sheet names from Excel file
    sheet_names = pd.ExcelFile(excel_obj.file.path).sheet_names

    # Get schools, departments, and programs based on user's role
    if request.user.is_superuser:
        schools = School.objects.all()
        departments = Department.objects.all()
    elif request.user.role in ['HOI', 'ADMIN']:
        schools = School.objects.filter(id=request.user.school.id)
        departments = Department.objects.filter(school=request.user.school)
    else:  # MENTOR
        schools = School.objects.filter(id=request.user.school.id)
        departments = Department.objects.filter(id=request.user.department.id)

    # Get existing programs as suggestions
    existing_programs = SheetCategory.objects.values_list('program', flat=True).distinct()

    # Debug info
    print("Available Schools:", [f"{school.id}: {school.code} - {school.name}" for school in schools])
    print("Available Departments:", [f"{dept.id}: {dept.code} - {dept.name}" for dept in departments])
    print("Existing Programs:", list(existing_programs))

    context = {
        'excel_id': excel_id,
        'sheet_names': sheet_names,
        'schools': schools,
        'departments': departments,
        'existing_programs': existing_programs,
        'user': request.user
    }
    return render(request, 'excelhandler/categorize_sheets.html', context)

def view_categorized_sheets(request):
    # Get all unique categories for filtering
    schools = SheetCategory.objects.values_list('school', flat=True).distinct()
    departments = SheetCategory.objects.values_list('department', flat=True).distinct()
    programs = SheetCategory.objects.values_list('program', flat=True).distinct()
    semesters = SheetCategory.objects.values_list('semester', flat=True).distinct()
    year_ranges = SheetCategory.objects.values_list('year_range', flat=True).distinct()

    # Filter based on query parameters
    categories = SheetCategory.objects.all()

    if request.GET.get('school'):
        categories = categories.filter(school=request.GET.get('school'))
    if request.GET.get('department'):
        categories = categories.filter(department=request.GET.get('department'))
    if request.GET.get('program'):
        categories = categories.filter(program=request.GET.get('program'))
    if request.GET.get('semester'):
        categories = categories.filter(semester=request.GET.get('semester'))
    if request.GET.get('year_range'):
        categories = categories.filter(year_range=request.GET.get('year_range'))

    context = {
        'categories': categories,
        'schools': schools,
        'departments': departments,
        'programs': programs,
        'semesters': semesters,
        'year_ranges': year_ranges,
        'selected_school': request.GET.get('school', ''),
        'selected_department': request.GET.get('department', ''),
        'selected_program': request.GET.get('program', ''),
        'selected_semester': request.GET.get('semester', ''),
        'selected_year_range': request.GET.get('year_range', '')
    }

    return render(request, 'excelhandler/view_categories.html', context)

@login_required
@role_required(['SUPERADMIN', 'HOI', 'ADMIN', 'MENTOR'])
def download_sheet(request, category_id):
    category = get_object_or_404(SheetCategory, id=category_id)

    # Check if user has permission to access this file
    if not (request.user.is_superuser or
            (request.user.role == 'HOI' and category.school == request.user.school) or
            (request.user.role == 'ADMIN' and category.school == request.user.school) or
            (request.user.role == 'MENTOR' and category.school == request.user.school and
             category.department == request.user.department)):
        messages.error(request, "You don't have permission to access this file.")
        return redirect('excelhandler:subject_analyser')

    excel_file = category.excel_file
    sheet_name = category.sheet_name

    try:
        # Read the specific sheet from the Excel file
        df = pd.read_excel(excel_file.file.path, sheet_name=sheet_name)

        # Create a new Excel file in memory with just this sheet
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

        # Prepare the response
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        # Set filename for download
        filename = f"{category.school}_{category.program}_{category.semester}_{category.year_range}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response
    except Exception as e:
        messages.error(request, f'Error downloading sheet: {str(e)}')
        return redirect('excelhandler:view_categories')

def delete_sheet_category(request, category_id):
    category = get_object_or_404(SheetCategory, id=category_id)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Sheet category deleted successfully!')
        return redirect('excelhandler:view_categories')
    return render(request, 'excelhandler/view_categories.html')

def view_sheet_category(request, category_id):
    return redirect('excelhandler:view_sheet', category_id=category_id)

def update_comments(request, category_id):
    if request.method == 'POST':
        category = get_object_or_404(SheetCategory, id=category_id)
        comments = request.POST.get('comments', '')
        category.comments = comments
        category.save()
        messages.success(request, 'Comments updated successfully!')
    return redirect('excelhandler:view_categories')
