from django.core.management.base import BaseCommand
from users.models import School, Department, Program
import json
import os

class Command(BaseCommand):
    help = 'Setup academic structure (schools, departments, programs) from JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to JSON file containing academic structure data')

    def handle(self, *args, **kwargs):
        json_file = kwargs['json_file']
        
        if not os.path.exists(json_file):
            self.stdout.write(self.style.ERROR(f'File not found: {json_file}'))
            return

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            # Create Schools
            for school_data in data['schools']:
                school, created = School.objects.get_or_create(
                    code=school_data['code'],
                    defaults={
                        'name': school_data['name'],
                        'description': school_data.get('description', ''),
                        'address': school_data.get('address', ''),
                        'website': school_data.get('website', ''),
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created school: {school.code}'))
                else:
                    self.stdout.write(self.style.WARNING(f'School already exists: {school.code}'))

                # Create Departments for this school
                for dept_data in school_data.get('departments', []):
                    dept, created = Department.objects.get_or_create(
                        code=dept_data['code'],
                        school=school,
                        defaults={
                            'name': dept_data['name'],
                            'description': dept_data.get('description', ''),
                        }
                    )

                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Created department: {dept.code} in {school.code}'))
                    else:
                        self.stdout.write(self.style.WARNING(f'Department already exists: {dept.code} in {school.code}'))

                    # Create Programs for this department
                    for prog_data in dept_data.get('programs', []):
                        prog, created = Program.objects.get_or_create(
                            code=prog_data['code'],
                            department=dept,
                            defaults={
                                'name': prog_data['name'],
                                'type': prog_data['type'],
                                'duration_years': prog_data['duration_years'],
                                'description': prog_data.get('description', ''),
                            }
                        )

                        if created:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Created program: {prog.code} in {dept.code}, {school.code}'
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Program already exists: {prog.code} in {dept.code}, {school.code}'
                                )
                            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
