web: uvicorn your_project.asgi:application --host 0.0.0.0 --port $PORT --workers 2
# Alternative with gunicorn and uvicorn worker:
# web: gunicorn your_project.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT