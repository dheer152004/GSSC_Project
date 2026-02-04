from django.urls import path
from . import views

app_name = 'excelhandler'

urlpatterns = [
    path('dashboard/', views.upload_excel, name='dashboard'),  # Main excel handler dashboard
    path('upload/', views.upload_excel, name='upload_excel'),  # Upload excel file
    path('categorize/', views.categorize_list, name='categorize_list'),  # List files to categorize
    path('categorize/<int:excel_id>/', views.categorize_sheets, name='categorize_sheets'),  # Categorize specific file
    path('categories/', views.view_categorized_sheets, name='view_categories'),  # View categorized sheets
    path('download/<int:category_id>/', views.download_sheet, name='download_sheet'),  # Download sheets
    path('delete/<int:category_id>/', views.delete_sheet_category, name='delete_sheet_category'),
    path('view/<int:category_id>/', views.view_sheet_category, name='view_sheet_category'),  # Redirect to view_sheet
    path('sheet/<int:category_id>/', views.view_sheet, name='view_sheet'),  # View sheet details and preview
    path('update-comments/<int:category_id>/', views.update_comments, name='update_comments'),  # Update sheet comments
    path('analyze/subject/', views.subject_analyser, name='subject_analyser'),  # Subject-wise analysis
    path('analyze/student/', views.student_analyser, name='student_analyser'),  # Student-wise analysis
]
