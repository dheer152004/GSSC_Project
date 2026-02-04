from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_remove_section_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Section name (e.g., A, B, C)', max_length=50)),
                ('is_active', models.BooleanField(default=True, help_text='Uncheck to disable this section')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sections', to='users.department')),
                ('mentor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mentored_sections', to='users.customuser')),
            ],
            options={
                'verbose_name': 'Section',
                'verbose_name_plural': 'Sections',
                'ordering': ['department__school', 'department', 'name'],
                'unique_together': {('name', 'department')},
                'permissions': [('can_manage_section', 'Can manage sections'), ('can_assign_mentor', 'Can assign mentor to section')],
            },
        ),
    ]
