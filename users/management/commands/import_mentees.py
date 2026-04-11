from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from users.models import CustomUser, StudentDetail
from excelhandler.models import ExcelFile, SheetCategory
import pandas as pd
import os


class Command(BaseCommand):
    help = 'Import mentees for a mentor from the latest ExcelFile for their school/department (up to limit)'

    def add_arguments(self, parser):
        parser.add_argument('--mentor', type=str, help='Mentor employee_id (required)')
        parser.add_argument('--limit', type=int, default=120, help='Maximum students to import')

    def handle(self, *args, **options):
        mentor_id = options.get('mentor')
        limit = options.get('limit') or 120
        if not mentor_id:
            raise CommandError('Please provide --mentor <employee_id>')

        try:
            mentor = CustomUser.objects.get(employee_id=str(mentor_id).strip())
        except CustomUser.DoesNotExist:
            raise CommandError(f'Mentor with employee_id={mentor_id} not found')

        # Find latest SheetCategory that matches mentor context (school, department)
        sc_qs = SheetCategory.objects.filter(is_active=True)
        if mentor.school:
            sc_qs = sc_qs.filter(school=mentor.school)
        if mentor.department:
            sc_qs = sc_qs.filter(department=mentor.department)

        latest_sheet = sc_qs.order_by('-created_at').first()
        if not latest_sheet:
            self.stdout.write(self.style.WARNING('No sheet category found for mentor school/department'))
            return

        latest = latest_sheet.excel_file
        file_path = getattr(latest.file, 'path', None) or getattr(latest.file, 'name', None)
        if not file_path or not os.path.exists(file_path):
            # try to resolve from MEDIA_ROOT relative path
            file_path = latest.file.name
            if not os.path.exists(file_path):
                self.stdout.write(self.style.ERROR(f'Excel file not found on disk: {latest.file}'))
                return

        # Read sheet specified by the SheetCategory
        sheet_name = latest_sheet.sheet_name if latest_sheet and latest_sheet.sheet_name else 0
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to read excel file (sheet={sheet_name}): {e}'))
            return

        if df.empty:
            self.stdout.write(self.style.WARNING('Excel sheet is empty'))
            return

        # Normalize columns
        cols = {c.lower().strip(): c for c in df.columns}

        def find_col(keys):
            for k in keys:
                for c in cols:
                    if k in c:
                        return cols[c]
            return None

        enrollment_col = find_col(['enroll', 'enrollment', 'enrollment no', 'enrollment_no', 'reg', 'registration', 'roll'])
        name_col = find_col(['name', 'student name', 'full name'])
        sgpa_col = find_col(['sgpa', 's gpa'])
        cgpa_col = find_col(['cgpa', 'c gpa', 'cum gpa'])

        if not enrollment_col or not name_col:
            self.stdout.write(self.style.ERROR('Could not detect required columns (enrollment and name) in excel'))
            return

        updated = 0
        skipped = 0
        processed_rows = 0

        for _, row in df.iterrows():
            if processed_rows >= limit:
                break
            processed_rows += 1
            enrollment = str(row.get(enrollment_col, '')).strip()
            name = str(row.get(name_col, '')).strip()
            if not enrollment or not name or enrollment.lower() in ['nan', 'none']:
                continue
            sgpa = ''
            cgpa = ''
            if sgpa_col:
                sgpa = str(row.get(sgpa_col, '')).strip()
            if cgpa_col:
                cgpa = str(row.get(cgpa_col, '')).strip()

            try:
                existing = StudentDetail.objects.filter(mentor=mentor, enrollment_no=enrollment).first()
                if existing:
                    existing.name = name
                    existing.sgpa = sgpa
                    existing.cgpa = cgpa
                    existing.source_file = latest
                    existing.source_sheet = latest_sheet
                    existing.save()
                    updated += 1
                else:
                    skipped += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error updating enrollment {enrollment}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Import completed. Rows read={processed_rows}, updated={updated}, skipped={skipped}'))
