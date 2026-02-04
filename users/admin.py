from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from .models import School, Department, Program, CustomUser, FileUpload, Section, AboutContent
from .forms import SectionAdminForm

# Override the default admin site to control model ordering
class CustomAdminSite(admin.AdminSite):
    site_header = 'GSSC Administration'
    site_title = 'GSSC Admin Portal'
    index_title = 'Welcome to GSSC Administration'
    
    def get_app_list(self, request):
        """
        Return a sorted list of all the installed apps that have been registered in this site.
        """
        app_dict = self._build_app_dict(request)
        for app in app_dict.values():
            app['models'].sort(
                key=lambda x: (
                    # First sort by order_index if it exists
                    getattr(self._registry.get(x['model'], None), 'order_index', 100),
                    # Then by verbose name
                    x.get('name', '').lower()
                )
            )
        return sorted(app_dict.values(), key=lambda x: x['name'].lower())

    def each_context(self, request):
        context = super().each_context(request)
        context['custom_admin'] = True
        return context

# Create a custom admin site instance
admin_site = CustomAdminSite(name='gssc_admin')

class AboutContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'last_updated')
    readonly_fields = ('last_updated', 'created_at')
    fieldsets = (
        ('Content', {
            'fields': ('title', 'content'),
            'description': '''
                <p>Enter the content for the About section. You can add links using HTML tags.</p>
                <p>Example of how to add links:</p>
                <pre>Welcome to GSSC Portal!

&lt;a href="https://example.com" class="text-primary"&gt;Click here&lt;/a&gt; to visit our website.

You can contact us at &lt;a href="mailto:contact@gssc.edu" class="text-primary"&gt;contact@gssc.edu&lt;/a&gt;

For more information about our programs, please visit our 
&lt;a href="/programs" class="text-primary text-decoration-none"&gt;Programs page&lt;/a&gt;.</pre>

                <p>Available link styles:</p>
                <ul>
                    <li>Add <code>class="text-primary"</code> for blue links</li>
                    <li>Add <code>class="text-decoration-none"</code> to remove underline</li>
                </ul>
            '''
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('last_updated', 'created_at'),
            'classes': ('collapse',)
        })
    )
    order_index = 0  # Will appear at the top of the admin index

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
    
    def has_add_permission(self, request):
        # Only allow adding if no content exists
        return request.user.is_superuser and not AboutContent.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

class CustomUserAdmin(UserAdmin):
    list_display = ('employee_id', 'email', 'get_full_name', 'get_role_display', 'get_school_name', 'get_department_name', 'is_staff')
    order_index = 1  # To control ordering in admin index

    def get_role_display(self, obj):
        return obj.get_role_display()
    get_role_display.short_description = 'Role'

    def get_school_name(self, obj):
        return obj.school.name if obj.school else '-'
    get_school_name.short_description = 'School'
    
    def get_department_name(self, obj):
        return obj.department.name if obj.department else '-'
    get_department_name.short_description = 'Department'
    
    search_fields = [
        'employee_id', 'email', 'first_name', 'last_name',
        'department__name', 'department__code',
        'school__name', 'school__code'
    ]
    search_help_text = "Search by name, employee ID, email, department, or school"
    list_filter = ('role', 'school', 'department', 'is_staff', 'is_superuser')
    search_fields = ('employee_id', 'email', 'first_name', 'last_name')
    ordering = ('employee_id',)

    fieldsets = (
        (None, {'fields': ('employee_id', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('School & Role', {'fields': ('role', 'school', 'department')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('employee_id', 'email', 'role', 'school', 'department', 'password1', 'password2'),
        }),
    )

class SchoolAdmin(admin.ModelAdmin):
    """Only superuser can manage schools"""
    list_display = ('code', 'name', 'website', 'is_active')
    order_index = 2  # To control ordering in admin index
    list_filter = ('is_active',)
    search_fields = ('code', 'name', 'description')
    ordering = ('code',)
    search_help_text = "Search by school code or name"
    autocomplete_fields = []  # No foreign keys to autocomplete
    
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset, use_distinct

    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description')
        }),
        ('Contact Details', {
            'fields': ('address', 'website')
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )

    def save_model(self, request, obj, form, change):
        try:
            obj.full_clean()  # Validate the model
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving school: {str(e)}")
            raise

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            messages.error(request, "Only superusers can modify schools.")
            return
        super().save_model(request, obj, form, change)



class DepartmentAdmin(admin.ModelAdmin):
    """Only superuser can manage departments"""
    list_display = ('code', 'name', 'school', 'hod', 'is_active')
    order_index = 3  # To control ordering in admin index
    list_filter = ('school', 'is_active')
    search_fields = ('code', 'name', 'description', 'school__name', 'school__code')
    ordering = ('school', 'code')
    autocomplete_fields = ['school', 'hod']
    search_help_text = "Search by department code, name, or school"
    
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset, use_distinct

    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description')
        }),
        ('School & Management', {
            'fields': ('school', 'hod')
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "hod":
            kwargs["queryset"] = CustomUser.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            messages.error(request, "Only superusers can modify departments.")
            return
        super().save_model(request, obj, form, change)

class ProgramAdmin(admin.ModelAdmin):
    """Only superuser can manage programs"""
    list_display = ('code', 'name', 'type', 'department', 'duration_years', 'coordinator', 'is_active')
    order_index = 4  # To control ordering in admin index
    list_filter = ('type', 'department__school', 'department', 'is_active')
    search_fields = ('code', 'name', 'description')
    ordering = ('department__school', 'department', 'code')
    autocomplete_fields = ['department', 'coordinator']

    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description')
        }),
        ('Program Details', {
            'fields': ('type', 'department', 'duration_years', 'coordinator')
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "coordinator":
            kwargs["queryset"] = CustomUser.objects.filter(is_active=True)
        elif db_field.name == "department":
            kwargs["queryset"] = Department.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            messages.error(request, "Only superusers can modify programs.")
            return
        super().save_model(request, obj, form, change)


class SectionAdmin(admin.ModelAdmin):
    form = SectionAdminForm
    order_index = 5  # To control ordering in admin index
    list_display = ('name', 'school', 'department', 'mentor', 'is_active')
    list_filter = ('school', 'department', 'is_active')
    search_fields = ('name', 'department__name', 'school__name')
    list_select_related = ('school', 'department', 'mentor')
    autocomplete_fields = ['school', 'department', 'mentor']
    
    def get_model_perms(self, request):
        # This will affect how the model is displayed in the admin index
        perms = super().get_model_perms(request)
        if perms['view']:
            perms['view_name'] = 'Sections'  # This is what appears in the admin index
        return perms

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "department":
            kwargs["queryset"] = Department.objects.filter(is_active=True).select_related('school')
        elif db_field.name == "mentor":
            kwargs["queryset"] = CustomUser.objects.filter(role='MENTOR', is_active=True).select_related('department')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    class Media:
        js = ('users/js/section_admin.js',)


class FileUploadAdmin(admin.ModelAdmin):
    """Admin interface for managing Excel file uploads"""
    list_display = ('title', 'uploaded_by', 'school', 'department', 'uploaded_at', 'is_active')
    order_index = 6  # To control ordering in admin index
    list_filter = ('is_active', 'uploaded_at', 'school', 'department')
    search_fields = ('title', 'description', 'uploaded_by__employee_id')
    autocomplete_fields = ['uploaded_by', 'school', 'department']
    readonly_fields = ('uploaded_at', 'updated_at')
    search_help_text = "Search by title, description, or uploader's ID"

    def has_add_permission(self, request):
        return True  # Everyone can upload files

    def has_change_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        if request.user.role in ['HOI', 'ADMIN']:
            return obj.school == request.user.school
        return obj.uploaded_by == request.user

# Register all models with the custom admin site
admin_site.register(AboutContent, AboutContentAdmin)
admin_site.register(CustomUser, CustomUserAdmin)
admin_site.register(School, SchoolAdmin)
admin_site.register(Department, DepartmentAdmin)
admin_site.register(Program, ProgramAdmin)
admin_site.register(Section, SectionAdmin)
admin_site.register(FileUpload, FileUploadAdmin)
