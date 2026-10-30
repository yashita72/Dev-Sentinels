# 🛡️ DevSentinels

**DevSentinels** is a production-ready, stateful multi-agent AI system built with **FastAPI**, **LangGraph**, and **LangChain** for automated GitHub Pull Request code reviews, bug detection, and security auditing.

---

## 🌟 Key Features

- **Asynchronous FastAPI Webhook Ingestion**: Receives GitHub `pull_request` triggers (`opened`, `synchronize`, `reopened`) and delegates long-running LLM analysis to non-blocking background workers.
- **HMAC SHA-256 Webhook Verification**: Strictly validates the `X-Hub-Signature-256` header using constant-time comparison (`hmac.compare_digest`) against timing attacks.
- **Stateful Multi-Agent LangGraph Workflow**:
  1. 🐛 **Bug & Logic Analysis Agent**: Pinpoints edge cases, unhandled exceptions, type bugs, and logic flaws.
  2. 🔒 **Security Audit Agent**: Audits OWASP Top 10 vulnerabilities, hardcoded secrets, exposed keys, and insecure deserialization.
  3. 🚀 **Refactoring Agent**: Identifies code-smell anti-patterns, performance bottlenecks, and clean-code optimizations.
  4. 📋 **Aggregator Node**: Compiles findings into an actionable markdown report.
- **Direct GitHub Feedback**: Automatically posts the consolidated review summary directly to the GitHub PR conversation via GitHub REST API / PyGithub.

---

## 📁 Project Directory Structure

```text
dev-sentinels/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization, CORS middleware, routes inclusion
│   ├── config.py            # Pydantic BaseSettings for env variables
│   ├── services/
│   │   ├── __init__.py
│   │   ├── github_service.py # Fetches diff, posts PR review comments via GitHub API
│   │   └── webhook_handler.py # Validates signature and parses PR payloads
│   └── agents/
│       ├── __init__.py
│       ├── graph.py         # LangGraph state graph definition & orchestration
│       └── prompts.py       # System prompts for Bug, Security, and Refactoring agents
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- Python 3.10+
- An OpenAI API Key (`OPENAI_API_KEY`) or Google Gemini API Key (`GEMINI_API_KEY`)
- A GitHub Personal Access Token (PAT) with `repo` or `pull_requests:write` permissions
- [ngrok](https://ngrok.com/) for exposing the local server to GitHub webhooks

### 2. Clone and Install Dependencies

```bash
cd dev-sentinels

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file and fill in your secrets:

```bash
cp .env.example .env
```

Edit `.env`:
```env
GITHUB_TOKEN=ghp_yourPersonalAccessTokenHere
GITHUB_WEBHOOK_SECRET=your_super_secret_webhook_passphrase
OPENAI_API_KEY=sk-proj-yourOpenAiKeyHere
OPENAI_MODEL=gpt-4o
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False
```

### 4. Start the Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify service health:
```bash
curl http://localhost:8000/health
# {"status":"healthy","service":"DevSentinels","version":"1.0.0"}
```

---

## 🌐 Local Testing with ngrok & GitHub Webhooks

To test incoming Pull Requests locally:

### Step 1: Start an ngrok Tunnel
In a new terminal window, run:
```bash
ngrok http 8000
```
ngrok will provide a public HTTPS forwarding URL, for example:
`https://abc1-23-45-67-89.ngrok-free.app`

### Step 2: Configure the Webhook in GitHub
1. Open your GitHub repository in your browser.
2. Navigate to **Settings** -> **Webhooks** -> **Add webhook**.
3. Set the following fields:
   - **Payload URL**: `https://<your-ngrok-subdomain>.ngrok-free.app/api/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: Enter the exact secret string you set in `GITHUB_WEBHOOK_SECRET` in `.env`.
   - **SSL verification**: Enable SSL verification.
4. Under **Which events would you like to trigger this webhook?**:
   - Choose **Let me select individual events**.
   - Check **Pull requests**.
   - Uncheck everything else.
5. Click **Add webhook**. GitHub will send a test `ping` event, and DevSentinels will acknowledge it with `200 OK`.

---

## 🧪 Testing the Workflow

1. Create a new branch in your repository:
   ```bash
   git checkout -b test-dev-sentinels
   ```
2. Make a change (e.g. create a file with a deliberate logic bug or hardcoded key) and commit it:
   ```python
   # test.py
   API_KEY = "sk-1234567890abcdef1234567890abcdef"
   def calculate_discount(price, discount):
       return price / discount # Potential ZeroDivisionError
   ```
3. Push and open a Pull Request against `main`.
4. DevSentinels will:
   - Verify the webhook signature.
   - Return an HTTP `202 Accepted` to GitHub immediately.
   - Concurrently fetch the unified diff.
   - Run the stateful LangGraph agents (`bug_agent` -> `security_agent` -> `refactoring_agent` -> `aggregator`).
   - Post an automated review comment directly onto your PR.

