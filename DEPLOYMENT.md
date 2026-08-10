# Deployment

This archive contains the project source without local virtual-environment and Python cache files.

Install dependencies with:
    pip install -r requirements.txt

For a Flask application whose Flask object is `app` in `app.py`, use:
    gunicorn app:app
