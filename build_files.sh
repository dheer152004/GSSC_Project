echo "BUILD START"
python3.10 -m pip install -r requirements-dev.txt
python3.10 -m manage.py collectstatic --noinput --clear
echo "BUILD END"

echo "Creating superuser if it doesn't exist..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'Password123')
    print('Superuser created!')
else:
    print('Superuser already exists.')
"