pip install gunicorn
gunicorn --bind 0.0.0.0:8000 app:app