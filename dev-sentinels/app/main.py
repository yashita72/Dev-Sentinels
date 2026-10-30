"""
DevSentinels FastAPI Application Entrypoint.
Sets up middlewares, life-cycle, background tasks, and webhook endpoints.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.services.webhook_handler import WebhookHandler
from app.services.github_service import GitHubService
from app.agents.graph import review_graph, PRReviewState

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("dev_sentinels")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown life-cycle handler.
    """
    settings = get_settings()
    logger.info("DevSentinels Sentinel service starting up...")
    logger.info(f"Target LLM Model: {settings.GEMINI_MODEL}")
    yield
    logger.info("DevSentinels Sentinel service shutting down...")


app = FastAPI(
    title="DevSentinels",
    description="Automated AI Multi-Agent GitHub PR Review and Security Auditing System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

webhook_handler = WebhookHandler()
github_service = GitHubService()


async def process_pr_review_task(
    repo_full_name: str,
    pr_number: int,
    pr_title: str,
    pr_author: str,
):
    """
    Background worker task to fetch PR diff, run LangGraph agents, and post review comments.
    """
    logger.info(f"Starting analysis for PR #{pr_number} in '{repo_full_name}'")
    try:
        # Step 1: Fetch PR diff
        diff_text = await github_service.fetch_pr_diff(repo_full_name, pr_number)
        if not diff_text.strip():
            logger.info(f"Diff for PR #{pr_number} is empty. Skipping analysis.")
            return

        # Step 2: Initialize State and Execute LangGraph multi-agent workflow
        initial_state: PRReviewState = {
            "repo_name": repo_full_name,
            "pr_number": pr_number,
            "pr_title": pr_title,
            "pr_author": pr_author,
            "diff_text": diff_text,
            "bug_review": None,
            "security_review": None,
            "refactoring_review": None,
            "final_summary": None,
            "error": None,
        }

        logger.info(f"Invoking LangGraph Multi-Agent workflow for PR #{pr_number}...")
        graph_result = await review_graph.ainvoke(initial_state)

        final_summary = graph_result.get("final_summary")
        if not final_summary:
            logger.error("Workflow completed without generating final summary.")
            return

        # Step 3: Post the generated markdown summary back to the GitHub PR
        logger.info(f"Posting review results to PR #{pr_number}...")
        success = await github_service.post_pr_comment(repo_full_name, pr_number, final_summary)
        if success:
            logger.info(f"Successfully finished processing PR #{pr_number}")
        else:
            logger.warning(f"Could not post review comment on PR #{pr_number}")

    except Exception as exc:
        logger.exception(f"Error processing PR review for {repo_full_name}#{pr_number}: {exc}")


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """
    Root landing endpoint.
    """
    return {
        "service": "DevSentinels",
        "description": "Automated AI Multi-Agent GitHub PR Review and Security Auditing System",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
        "webhook_endpoint": "/api/webhook/github"
    }


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Liveness and readiness health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "DevSentinels",
        "version": "1.0.0"
    }


@app.post("/api/webhook/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None)
):
    """
    Secure GitHub Webhook ingestion endpoint.
    Verifies HMAC SHA-256 signature and delegates Pull Request events to background processing.
    """
    raw_body = await request.body()

    # 1. Verify HMAC SHA-256 Webhook Signature
    is_valid = webhook_handler.verify_signature(raw_body, x_hub_signature_256)
    if not is_valid:
        logger.warning("Rejected webhook request: Invalid HMAC signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Hub-Signature-256 webhook signature"
        )

    # 2. Inspect GitHub Event Header
    if x_github_event == "ping":
        logger.info("Received GitHub ping event. Connection verified successfully.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "pong", "message": "Webhook setup verified successfully"}
        )

    if x_github_event != "pull_request":
        logger.info(f"Ignoring unsupported event type: '{x_github_event}'")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ignored", "message": f"Event '{x_github_event}' not processed"}
        )

    # 3. Parse JSON Body
    try:
        payload = await request.json()
    except Exception as exc:
        logger.error(f"Failed to parse webhook JSON payload: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed JSON payload")

    # 4. Extract PR Information
    pr_info = webhook_handler.parse_pull_request_payload(payload)
    if not pr_info:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "skipped", "message": "Action not targeted for automated review"}
        )

    # 5. Queue asynchronous AI review via FastAPI BackgroundTasks
    background_tasks.add_task(
        process_pr_review_task,
        repo_full_name=pr_info.repo_full_name,
        pr_number=pr_info.pr_number,
        pr_title=pr_info.pr_title,
        pr_author=pr_info.pr_author,
    )

    return {
        "status": "queued",
        "message": f"PR review queued for {pr_info.repo_full_name}#{pr_info.pr_number}",
        "action": pr_info.action
    }

