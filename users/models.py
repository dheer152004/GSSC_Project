from django.db import models
import logging

logger = logging.getLogger(__name__)
from django.utils import timezone
from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser, BaseUserManager

class AboutContent(models.Model):
    title = models.CharField(max_length=200, default="About GSSC Portal")
    content = models.TextField(help_text="Content for the about section. HTML tags are supported.")
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "About Content"
        verbose_name_plural = "About Content"
        ordering = ['-last_updated']

    def __str__(self):
        return f"About Content (Last updated: {self.last_updated.strftime('%Y-%m-%d %H:%M')})"

    def save(self, *args, **kwargs):
        # Ensure only one active about content exists
        if self.is_active:
            AboutContent.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
        # Clear cache when content is updated
        cache.delete('about_content')

@receiver(post_save, sender=AboutContent)
def clear_about_cache(sender, instance, **kwargs):
    cache.delete('about_content')
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

class School(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Full name of the school")
    code = models.CharField(max_length=20, unique=True, help_text="Short code for the school (e.g., ASET, ALS)")
    description = models.TextField(blank=True, help_text="Optional description of the school")
    address = models.TextField(blank=True, help_text="School address")
    website = models.URLField(blank=True, help_text="School website URL")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text="Uncheck to disable this school")

    def clean(self):
        super().clean()
        # Add any additional validation here if needed
        if self.code:
            self.code = self.code.upper()  # Ensure code is uppercase

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        ordering = ['code']
        verbose_name = 'School'
        verbose_name_plural = 'Schools'
        permissions = [
            ("can_manage_school", "Can manage schools")
        ]

class Department(models.Model):
    name = models.CharField(max_length=100, help_text="Full name of the Department")
    code = models.CharField(max_length=30, help_text="Short code of the Department")
    description = models.TextField(blank=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='departments')
    hod = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='hod_departments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.code:
            self.code = self.code.upper()
            
    class Meta:
        ordering = ['school', 'code']
        unique_together = ['school', 'code']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        permissions = [
            ("can_manage_department", "Can manage departments")
        ]

class Program(models.Model):
    PROGRAM_TYPES = [
        ('UG', 'Undergraduate'),
        ('PG', 'Postgraduate'),
        ('PHD', 'Doctorate'),
        ('DIPLOMA', 'Diploma'),
    ]

    name = models.CharField(max_length=100, help_text="Full name of the Program")
    code = models.CharField(max_length=20, help_text="Program code (e.g., BTech, MCA)")
    type = models.CharField(max_length=10, choices=PROGRAM_TYPES)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='programs')
    duration_years = models.DecimalField(max_digits=3, decimal_places=1, help_text="Program duration in years")
    description = models.TextField(blank=True)
    coordinator = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='coordinated_programs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.department.school.code} - {self.department.code} - {self.code}"

    class Meta:
        ordering = ['department', 'code']
        unique_together = ['department', 'code']
        verbose_name = 'Program'
        verbose_name_plural = 'Programs'
        permissions = [
            ("can_manage_program", "Can manage programs")
        ]

class CustomUserManager(BaseUserManager):
    def create_user(self, employee_id, email, password=None, **extra_fields):
        if not employee_id:
            raise ValueError('The Employee ID must be set')
        if not email:
            raise ValueError('The Email must be set')
        # Normalize inputs to avoid whitespace mismatches
        employee_id = str(employee_id).strip()
        email = self.normalize_email(email).strip()

        user = self.model(
            employee_id=employee_id,
            email=email,
            username=employee_id,  # Set username to employee_id
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, employee_id, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'SUPERADMIN')  # Set role as ADMIN for superuser

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(employee_id, email, password, **extra_fields)



class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('SUPERADMIN', 'Developer'),
        ('HOI', 'Head of Institution'),
        ('ADMIN', 'Department Admin'),
        ('MENTOR', 'Mentor'),
    ]

    # Override groups and user_permissions with custom related_names
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user'
    )

    employee_id = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='MENTOR')
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=False)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'employee_id'
    REQUIRED_FIELDS = ['email']

    def clean(self):
        super().clean()
        if not self.is_superuser:  # Only apply these validations for non-superuser accounts
            # All roles except superuser need a school
            if self.role in ['HOI', 'ADMIN', 'MENTOR'] and not self.school:
                raise ValidationError({'school': 'School is required.'})
            
            # HOI should not have a department
            if self.role == 'HOI' and self.department:
                raise ValidationError({'department': 'Head of Institution (HOI) should not have a department assigned.'})
            
            # ADMIN only needs school, department should be null
            if self.role == 'ADMIN' and self.department:
                raise ValidationError({'department': 'Department should not be assigned for Admin role.'})
            
            # Mentor needs both school and department
            if self.role == 'MENTOR':
                if not self.department:
                    raise ValidationError({'department': 'Department is required for Mentors.'})
                # Ensure department belongs to selected school
                if self.department and self.school and self.department.school != self.school:
                    raise ValidationError({'department': 'Selected department must belong to the selected school.'})

    def save(self, *args, **kwargs):
        # Ensure employee_id and username are normalized
        if self.employee_id:
            self.employee_id = str(self.employee_id).strip()
        if not self.username:
            self.username = self.employee_id
        if not self.is_superuser:  # Skip validations for superuser
            if self.role == 'HOI':
                self.department = None
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_id})"

    def can_manage_users(self, target_user=None):
        # Superadmin can manage all users
        if self.is_superuser:
            return True
        # HOI and ADMIN can manage users in their school (except other HOIs and ADMINs)
        if self.role in ['HOI', 'ADMIN']:
            if target_user:
                return (
                    target_user.school == self.school and 
                    target_user.role == 'MENTOR'
                )
            return True
        return False

    def can_manage_files(self, file=None):
        # Superadmin can manage all files
        if self.is_superuser:
            return True
        # HOI and ADMIN can manage files in their school
        if self.role in ['HOI', 'ADMIN']:
            if file:
                return file.school == self.school
            return True
        # Mentors can only manage their own files
        if self.role == 'MENTOR':
            if file:
                return file.uploaded_by == self
            return True
        return False

    def can_assign_sections(self, section=None):
        # Superadmin can assign any section
        if self.is_superuser:
            return True
        # HOI and ADMIN can assign sections in their school
        if self.role in ['HOI', 'ADMIN']:
            if section:
                return section.department.schools.filter(id=self.school.id).exists()
            return True
        return False

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


# Signal to log password changes for users (helpful to trace unexpected password resets)
from django.db.models.signals import pre_save

@receiver(pre_save, sender=CustomUser)
def log_password_change(sender, instance, **kwargs):
    try:
        if instance.pk:
            old = sender.objects.get(pk=instance.pk)
            if old.password != instance.password:
                logger.debug("Password changed for %s: old_prefix=%s, new_prefix=%s",
                             getattr(instance, 'employee_id', instance.pk),
                             (old.password or '')[:12], (instance.password or '')[:12])
    except Exception:
        # Ignore errors here to avoid breaking save flow
        pass



class Section(models.Model):
    name = models.CharField(max_length=50, help_text="Section name (e.g., A, B, C)")
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='school_sections',default=1)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='sections')
    mentor = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='mentored_sections')
    is_active = models.BooleanField(default=True, help_text="Uncheck to disable this section")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if not (self.department and self.department.school):
            return f"Section {self.name}"
        return f"{self.department.school.code} - {self.department.code} - Section {self.name}"

    def clean(self):
        super().clean()
        # Validate that department belongs to the selected school
        if self.department and self.school and self.department.school != self.school:
            raise ValidationError({'department': 'Department must belong to the selected school.'})
            
        # Validate that mentor belongs to the same department
        if self.mentor and self.mentor.department != self.department:
            raise ValidationError({'mentor': 'Mentor must belong to the same department as the section.'})
            
        # Validate that mentor is actually a mentor
        if self.mentor and self.mentor.role != 'MENTOR':
            raise ValidationError({'mentor': 'Selected user must have the role of MENTOR.'})

    def get_school(self):
        return self.department.school

    def get_full_name(self):
        return f"{self.department.school.name} - {self.department.name} - Section {self.name}"

    class Meta:
        unique_together = ['name', 'department']
        ordering = ['department__school', 'department', 'name']
        verbose_name = 'Section'
        verbose_name_plural = 'Sections'
        default_permissions = ('add', 'change', 'delete', 'view')
        permissions = [
            ("can_manage_section", "Can manage sections"),
            ("can_assign_mentor", "Can assign mentor to section")
        ]

    def get_str_for_admin(self):
        return f"{self.department.school.code} - {self.department.code} - Section {self.name}"

    def can_edit(self, user):
        # Superadmin can edit everything
        if user.is_superuser:
            return True
        # HOI and ADMIN can edit files from their school
        if user.role in ['HOI', 'ADMIN'] and user.school == self.school:
            return True
        # Mentor can only edit their own files
        if user.role == 'MENTOR' and user == self.uploaded_by:
            return True
        return False

    def can_view(self, user):
        # Superadmin can view everything
        if user.is_superuser:
            return True
        # HOI and ADMIN can view files from their school
        if user.role in ['HOI', 'ADMIN'] and user.school == self.school:
            return True
        # Mentor can view files from their department and section
        if user.role == 'MENTOR':
            if user.department == self.department:
                # Can view all files in their department
                return True
            if hasattr(user, 'mentored_sections') and self.section in user.mentored_sections.all():
                # Can view files from sections they mentor
                return True
        return False

    class Meta:
        ordering = ['-created_at']

class FileUpload(models.Model):
    title = models.CharField(max_length=255, help_text='Title of the document')
    file = models.FileField(upload_to='uploads/', help_text='Upload files')
    description = models.TextField(blank=True, help_text='Optional description of the file')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='uploads')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='files')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='files')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Excel File'
        verbose_name_plural = 'Excel Files Of Sections'


class StudentDetail(models.Model):
    """Stores mentee/student details linked to a mentor.

    Up to 120 entries per mentor are expected; enforcement is left to
    application logic when importing from Excel.
    """
    mentor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mentees')
    name = models.CharField(max_length=200)
    enrollment_no = models.CharField(max_length=64)
    sgpa = models.CharField(max_length=32, blank=True)
    cgpa = models.CharField(max_length=32, blank=True)
    source_file = models.ForeignKey('excelhandler.ExcelFile', null=True, blank=True, on_delete=models.SET_NULL)
    source_sheet = models.ForeignKey('excelhandler.SheetCategory', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('mentor', 'enrollment_no')
        ordering = ['mentor', 'enrollment_no']
        verbose_name = 'Student Detail'
        verbose_name_plural = 'Student Details'

    def __str__(self):
        return f"{self.name} ({self.enrollment_no}) — Mentor: {self.mentor.employee_id}"

    def save(self, *args, **kwargs):
        if self.enrollment_no:
            self.enrollment_no = str(self.enrollment_no).strip()
        super().save(*args, **kwargs)