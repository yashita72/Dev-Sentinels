"""
Webhook Handler Service.
Handles HMAC SHA-256 signature verification and parsing of GitHub webhook events.
"""

import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.config import get_settings

logger = logging.getLogger(__name__)


class PullRequestEventInfo(BaseModel):
    """
    Normalized data extracted from GitHub pull_
    request payload.
    """
    action: str = Field(..., description="Action name e.g. opened, synchronize")
    pr_number: int = Field(..., description="PR number")
    pr_title: str = Field(..., description="PR title")
    pr_author: str = Field(..., description="Username of author who created PR")
    repo_full_name: str = Field(..., description="Full repository name 'owner/repo'")
    clone_url: str = Field(default="", description="Repository clone URL")
    diff_url: str = Field(default="", description="Direct link to unified diff")


class WebhookHandler:
    """
    Service responsible for validating GitHub webhook payloads.
    """

    def __init__(self, secret: Optional[str] = None):
        settings = get_settings()
        self.secret = secret or settings.GITHUB_WEBHOOK_SECRET

    def verify_signature(self, raw_body: bytes, signature_header: Optional[str]) -> bool:
        """
        Verifies GitHub X-Hub-Signature-256 header using HMAC-SHA256.

        Args:
            raw_body: Raw bytes from the incoming HTTP request.
            signature_header: Header string starting with 'sha256='

        Returns:
            True if signature matches, False otherwise.
        """
        if not signature_header:
            logger.warning("Missing X-Hub-Signature-256 header in webhook request.")
            return False

        if not signature_header.startswith("sha256="):
            logger.warning("Invalid signature prefix in X-Hub-Signature-256 header.")
            return False

        provided_signature = signature_header[len("sha256="):]
        computed_signature = hmac.new(
            key=self.secret.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(provided_signature, computed_signature)

    def parse_pull_request_payload(self, payload: Dict[str, Any]) -> Optional[PullRequestEventInfo]:
        """
        Extracts relevant information from a verified GitHub pull_request webhook payload.

        Args:
            payload: Deserialized JSON payload dictionary.

        Returns:
            PullRequestEventInfo instance or None if not applicable.
        """
        action = payload.get("action")
        pr_data = payload.get("pull_request")
        repo_data = payload.get("repository")

        if not pr_data or not repo_data:
            logger.warning("Payload does not contain expected pull_request or repository structures.")
            return None

        # Filter supported PR actions
        if action not in ["opened", "synchronize", "reopened"]:
            logger.info(f"Ignored pull_request event action: '{action}'")
            return None

        return PullRequestEventInfo(
            action=action,
            pr_number=pr_data.get("number"),
            pr_title=pr_data.get("title", ""),
            pr_author=pr_data.get("user", {}).get("login", "unknown"),
            repo_full_name=repo_data.get("full_name", ""),
            clone_url=repo_data.get("clone_url", ""),
            diff_url=pr_data.get("diff_url", "")
        )

