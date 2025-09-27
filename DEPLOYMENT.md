# Deployment Guide

This guide provides instructions for deploying the Gamified Trading Platform to a production environment.

## 1. Production Checklist
Before deploying, ensure you have completed the following:
- [ ] Set `FLASK_ENV` to `production` in your environment variables.
- [ ] Generated a strong, unique `SECRET_KEY`.
- [ ] Configured a production Firebase project (separate from your development project).
- [ ] Deployed and tested your Firestore security rules.
- [ ] Set up a production-ready WSGI server like Gunicorn.
- [ ] Configured HTTPS to secure all traffic.

## 2. Firebase Production Setup
1.  **Create a Production Firebase Project**: It is highly recommended to use a separate Firebase project for production to isolate data.
2.  **Production Firestore Database**: Create a new Firestore database in your production project.
3.  **Deploy Security Rules**:
    *   Copy the security rules from the project's `firestore.rules` file (if you have one) or from the documentation.
    *   In your Firebase Console, go to **Firestore Database > Rules**.
    *   Paste the rules and click **Publish**. Ensure your rules are not overly permissive.
4.  **Production Service Account**: Generate a new service account key (`firebase_config.json`) for your production project and replace the development key on your server.
5.  **Web App Config**: Update your production environment variables with the web app configuration (`firebaseConfig`) from the production Firebase project.

## 3. Flask Deployment Options
This application can be deployed to any platform that supports Python and WSGI. Below are instructions for a few common providers.

### Option A: Heroku (Recommended for simplicity)
1.  **Install Heroku CLI**: Follow the [official instructions](https://devcenter.heroku.com/articles/heroku-cli) to install the Heroku CLI.
2.  **Create `Procfile`**: Create a file named `Procfile` in the root directory with the following content:
    ```
    web: gunicorn app:app
    ```
3.  **Login and Create App**:
    ```bash
    heroku login
    heroku create your-app-name
    ```
4.  **Set Environment Variables**:
    ```bash
    heroku config:set FLASK_ENV=production
    heroku config:set SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex())')
    heroku config:set FIREBASE_API_KEY=your_production_key
    # ... set all other required .env variables
    ```
5.  **Deploy**:
    ```bash
    git push heroku main
    ```

### Option B: Google Cloud Run (Recommended for Firebase integration)
Google Cloud Run is a serverless platform that works seamlessly with Firebase.

1.  **Enable APIs**: In your Google Cloud project, enable the Cloud Run and Cloud Build APIs.
2.  **Create `Dockerfile`**: Create a `Dockerfile` in your project root:
    ```Dockerfile
    FROM python:3.11-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    COPY . .
    CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
    ```
3.  **Build and Deploy**:
    ```bash
    # Replace [PROJECT-ID] and [IMAGE-NAME]
    gcloud builds submit --tag gcr.io/[PROJECT-ID]/[IMAGE-NAME]
    gcloud run deploy --image gcr.io/[PROJECT-ID]/[IMAGE-NAME] --platform managed
    ```
4.  **Set Environment Variables**: Configure secrets and environment variables in the Cloud Run service settings.

## 4. Environment Variables in Production
**Never hardcode secrets**. Use your hosting provider's system for managing environment variables (e.g., Heroku Config Vars, Google Secret Manager).

-   `FLASK_ENV`: `production`
-   `SECRET_KEY`: A long, random, and unique string.
-   All `FIREBASE_*` variables for your **production** project.

## 5. Security Hardening
### HTTPS Enforcement (Flask-Talisman)
This project includes `Flask-Talisman` to handle HTTPS and security headers. It is configured in `app.py`. By default, it will force all connections to `https` in a production environment.

### Security Headers
`Flask-Talisman` also sets important security headers like:
-   `Content-Security-Policy` (CSP)
-   `Strict-Transport-Security` (HSTS)
-   `X-Content-Type-Options`
-   `X-Frame-Options`

Review the CSP in `app.py` to ensure it fits your needs, especially if you add external scripts or resources.

### Rate Limiting
The application uses `Flask-Limiter` to prevent brute-force attacks. The limits are defined in `app.py` and can be adjusted for production traffic.

### CORS Configuration
`Flask-CORS` is included to manage cross-origin requests. The default configuration is restrictive. Adjust it in `app.py` if your frontend is hosted on a different domain than your backend.

## 6. Background Tasks (APScheduler)
Running APScheduler in a production environment with a WSGI server like Gunicorn requires care, as Gunicorn can spawn multiple worker processes.

**Problem**: Each Gunicorn worker will initialize its own scheduler, leading to duplicate job executions.

**Solution**: Use a centralized, persistent job store for APScheduler, such as Redis or a database. This ensures that only one instance of a job runs at a time.

**Example with Redis Job Store**:
1.  Add `redis` to `requirements.txt`.
2.  Configure APScheduler in `tasks/scheduler.py`:
    ```python
    from apscheduler.jobstores.redis import RedisJobStore

    jobstores = {
        'default': RedisJobStore(host='your-redis-host', port=6379, db=0)
    }
    scheduler = BackgroundScheduler(jobstores=jobstores, timezone='UTC')
    ```
3.  Ensure your hosting environment has a Redis instance available.

## 7. Monitoring & Logging
### Flask Logging
In `config.py`, you can configure production-level logging to write logs to a file or a logging service.

```python
# config.py
import logging
from logging.handlers import RotatingFileHandler

# ...
if os.environ.get('FLASK_ENV') == 'production':
    # Example: Log to a file
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
```

### Firebase Monitoring
Use the Firebase console to monitor Firestore usage, function performance, and authentication activity. Set up alerts for unusual activity.

## 8. Backup & Recovery
Firestore provides automated backups and point-in-time recovery features.
-   **Enable Backups**: In the Google Cloud Console, navigate to **Firestore > Backups** and set up a daily backup schedule.
-   **Test Recovery**: Periodically test restoring from a backup to ensure your recovery plan works.

## 9. Scaling Considerations
-   **Firebase**: Firestore and Firebase Auth are designed to scale automatically. Monitor your usage to stay within budget.
-   **Flask Application**: If your application traffic grows, you can scale horizontally by increasing the number of Gunicorn workers or running instances of your app behind a load balancer.

## 10. Cost Estimation
-   **Firebase**: The "Spark" free tier is generous and may be sufficient for small-scale research studies. Key costs are typically related to document reads/writes and data storage. Use the [Firebase Pricing Calculator](https://firebase.google.com/pricing) to estimate costs.
-   **Hosting**:
    -   **Heroku**: The "Eco" or "Basic" dynos are a good starting point.
    -   **Google Cloud Run**: You pay for what you use based on CPU and memory consumption. It can be very cost-effective for low-traffic applications.
    -   Other providers (DigitalOcean, PythonAnywhere) have similar tiered pricing.