# Report Reviewer App

A small Flask web app that lets you upload a report and uses the OpenAI ChatGPT API to review it for clarity, structure, risks, missing evidence, and actionable improvements. It is designed to deploy easily to Google Cloud Run.

## Features

- Simple upload UI
- Supports `.pdf`, `.docx`, `.txt`, and `.md`
- Extracts text server-side before sending it to OpenAI
- Uses the OpenAI Responses API
- Runs locally or on Google Cloud Run
- No uploaded files are stored permanently

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your API key to `.env`:

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Run the app:

```bash
flask --app app run --debug
```

Open http://127.0.0.1:5000

## Deploy to Google Cloud Run

From the `report-reviewer-app` folder:

```bash
gcloud run deploy report-reviewer-app \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_MODEL=gpt-4.1-mini \
  --set-secrets OPENAI_API_KEY=openai-api-key:latest
```

Create the secret first:

```bash
printf "YOUR_OPENAI_API_KEY" | gcloud secrets create openai-api-key --data-file=-
```

Grant Cloud Run access to the secret if prompted by Google Cloud.

## Notes

- Keep `MAX_CONTENT_LENGTH` conservative for early testing. Large documents can exceed model context limits.
- For confidential reports, review your data-handling requirements before deployment.
- This app extracts text from files and sends only the extracted text plus the review prompt to OpenAI.

## Repository layout

```text
report-reviewer-app/
├── app.py
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .env.example
├── templates/
│   ├── index.html
│   └── result.html
└── static/
    └── styles.css
```
