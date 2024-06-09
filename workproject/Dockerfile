FROM python:3.11-slim


COPY . /app/
WORKDIR /app

RUN pip install -r requirements.txt

CMD python manage.py makemigrations \
    && python manage.py migrate\
    && python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='root').exists() or User.objects.create_superuser('root', 'root@example.com', 'root')" \
    && python manage.py collectstatic --noinput\
    && gunicorn workproject.wsgi:application --bind 0.0.0.0:8000 --log-level info