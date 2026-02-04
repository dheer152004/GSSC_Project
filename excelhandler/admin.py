from django.contrib import admin
from .models import ExcelFile, SheetCategory
from users.admin import admin_site

class SheetCategoryInline(admin.TabularInline):
    model = SheetCategory
    extra = 1

class ExcelFileAdmin(admin.ModelAdmin):
    inlines = [SheetCategoryInline]
    list_display = ('file', 'uploaded_by', 'school', 'department', 'uploaded_at', 'is_active')
    list_filter = ('school', 'department', 'is_active')
    search_fields = ('uploaded_by__employee_id', 'school__name', 'department__name')
    order_index = 7  # Place after FileUpload in admin index
    
    class Meta:
        verbose_name = 'Excel File'
        verbose_name_plural = 'Excel Files'

class SheetCategoryAdmin(admin.ModelAdmin):
    list_display = ('sheet_name', 'school', 'department', 'program', 'semester', 'year_range')
    list_filter = ('school', 'department', 'program', 'semester')
    search_fields = ('sheet_name', 'school__name', 'department__name', 'program')
    order_index = 8  # Place after Excel Files in admin index

# Register with our custom admin site
admin_site.register(ExcelFile, ExcelFileAdmin)
admin_site.register(SheetCategory, SheetCategoryAdmin)
