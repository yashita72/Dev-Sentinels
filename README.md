# Dev-Sentinels

Dev-Sentinels is an automated, multi-agent AI code review service for GitHub pull requests. It receives signed GitHub webhooks, analyzes pull request diffs with specialized LangGraph agents, and posts a consolidated review back to the pull request.

## Features

- FastAPI webhook service with asynchronous background processing
- HMAC-SHA256 verification for GitHub webhook requests
- LangGraph workflow for bug and logic analysis, security auditing, and refactoring suggestions
- Automatic Markdown review comments on GitHub pull requests
- Health and service information endpoints
- Render deployment configuration included

## Architecture

```text
GitHub pull_request webhook -> FastAPI -> LangGraph review workflow
                                      -> Bug, Security, and Refactoring agents
                                      -> Aggregated Markdown GitHub comment
```

The application source lives in [`dev-sentinels/`](./dev-sentinels).

## Requirements

- Python 3.10 or newer
- A GitHub token that can read pull requests and write pull request comments
- A GitHub webhook secret
- A Google Gemini API key
- A publicly reachable HTTPS endpoint for GitHub webhooks when running outside a hosted environment

## Local setup

```bash
git clone https://github.com/yashita72/Dev-Sentinels.git
cd Dev-Sentinels/dev-sentinels

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

Set the required environment variables:

```bash
export GITHUB_TOKEN="your-github-token"
export GITHUB_WEBHOOK_SECRET="your-webhook-secret"
export GEMINI_API_KEY="your-gemini-api-key"
export GEMINI_MODEL="gemini-1.5-flash"
```

Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
curl http://localhost:8000/health
```

## GitHub webhook configuration

Create a webhook in the repository you want to review with:

- **Payload URL:** `https://your-domain.example/api/webhook/github`
- **Content type:** `application/json`
- **Secret:** the value of `GITHUB_WEBHOOK_SECRET`
- **Events:** Pull requests

Dev-Sentinels processes the `opened`, `synchronize`, and `reopened` pull request actions. Use [ngrok](https://ngrok.com/) or a hosted deployment to expose a local service to GitHub.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Service information and links |
| `GET` | `/health` | Health check |
| `POST` | `/api/webhook/github` | Signed GitHub webhook ingestion |

Interactive API documentation is available at `/docs` when the service is running.

## Deployment

The repository includes [`render.yaml`](./dev-sentinels/render.yaml) and a `Procfile` for Render-compatible deployments. Configure `GITHUB_TOKEN`, `GITHUB_WEBHOOK_SECRET`, and `GEMINI_API_KEY` as platform secrets.

## Security notes

- Keep tokens, API keys, and webhook secrets out of source control.
- Configure GitHub webhook signature verification with a strong, private secret.
- Grant the GitHub token only the permissions required to read pull requests and post comments.

## License

This project is licensed under the [MIT License](./LICENSE).
