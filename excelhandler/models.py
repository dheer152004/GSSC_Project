from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from users.models import School, Department, Program, CustomUser

class ExcelFile(models.Model):
    file = models.FileField(upload_to='excel_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='excel_files', null=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='excel_files', null=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='excel_files', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        school_code = self.school.code if self.school else 'No School'
        employee_id = self.uploaded_by.employee_id if self.uploaded_by else 'Unknown'
        return f"{school_code} - Excel file uploaded by {employee_id} at {self.uploaded_at}"

    def clean(self):
        super().clean()
        # Validate that department belongs to the school if department is provided
        if self.department and self.school and self.department.school != self.school:
            raise ValidationError({'department': 'Department must belong to the selected school.'})

class SheetCategory(models.Model):
    excel_file = models.ForeignKey(ExcelFile, on_delete=models.CASCADE, related_name='sheet_categories')
    sheet_name = models.CharField(max_length=100)
    # Keep old fields for data migration
    # school_name = models.CharField(max_length=100, null=True)    # Temporary field
    # department_name = models.CharField(max_length=100, null=True) # Temporary field
    # program_name = models.CharField(max_length=100, null=True)    # Temporary field
    # New fields
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='sheet_categories', null=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='sheet_categories', null=True)
    program = models.CharField(max_length=100)    # e.g., B.Tech[CSE], BA[History]
    semester = models.CharField(max_length=50)    # e.g., SEM1, SEM3
    year_range = models.CharField(max_length=50)  # e.g., 2023-2027
    comments = models.TextField(blank=True, null=True, help_text="Additional information about the sheet")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        school = self.school.name if self.school else 'No School'
        department = self.department.name if self.department else 'No Department'
        program = self.program if self.program else 'No Program'
        semester = self.semester or 'No Semester'
        year_range = self.year_range or 'No Year'
        return f"{school} - {department} - {program} - {semester} ({year_range})"

    class Meta:
        verbose_name = 'Sheet Category'
        verbose_name_plural = 'Sheet Categories'
        ordering = ['-created_at']
