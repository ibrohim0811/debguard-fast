run:
	uvicorn main:app --reload
celery:
	celery -A celery_app worker --loglevel=info