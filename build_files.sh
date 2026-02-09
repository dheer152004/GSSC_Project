echo "BUILD START"
python3.10 -m pip install -r requirements-dev.txt
python3.10 -m manage.py collectstatic --noinput --clear
echo "BUILD END"