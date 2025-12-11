# Deployment Guide

## Prerequisites

- Python 3.10+
- Firebase Project (if using Firebase mode)
- Google Cloud SDK (optional for deployment)

## Environment Variables

Copy `.env.example` to `.env` and set the following:

- `FLASK_APP`: `app.py`
- `FLASK_ENV`: `production`
- `SECRET_KEY`: Generate a strong random string
- `DB_TYPE`: `firebase` or `sqlite`
- `FIREBASE_CONFIG_PATH`: Path to your service account JSON

## Deployment Options

### Heroku

1. Create a `Procfile`:
   ```
   web: gunicorn app:app
   ```
2. Set environment variables in Heroku dashboard.
3. Push code to Heroku.

### Google Cloud Run

1. Build container:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT-ID/tradesim
   ```
2. Deploy:
   ```bash
   gcloud run deploy tradesim --image gcr.io/PROJECT-ID/tradesim
   ```

## Post-Deployment

1. Create an admin user by registering and manually changing the role in the database.
2. Ensure Background Scheduler is running (in Heroku, this might need a separate worker or just run in the web dyno if using APScheduler BackgroundScheduler, but note that multiple dynos will duplicate jobs. For production, consider using a separate clock process or Redis-based queue).
