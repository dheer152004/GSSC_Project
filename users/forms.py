from django import forms
from .models import Section, School, Department, CustomUser,FileUpload

class SectionAdminForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['school', 'department', 'mentor', 'name', 'is_active']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mentor'].required = False  # Make mentor optional

    def clean(self):
        cleaned_data = super().clean()
        school = cleaned_data.get('school')
        department = cleaned_data.get('department')
        mentor = cleaned_data.get('mentor')

        if department and school and department.school != school:
            raise forms.ValidationError({
                'department': 'Selected department does not belong to the selected school.'
            })

        if mentor and department and mentor.department != department:
            raise forms.ValidationError({
                'mentor': 'Selected mentor does not belong to the selected department.'
            })

        return cleaned_data
            
            # if 'department' in kwargs['initial']:
            #     department = kwargs['initial']['department']
            #     if department:
            #         self.fields['mentor'].queryset = CustomUser.objects.filter(
            #             department=department,
            #             role='MENTOR',
            #             is_active=True
            #         )


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = FileUpload
        fields = ['title', 'file']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'class': 'form-control'})
        self.fields['file'].widget.attrs.update({'class': 'form-control'})


