"""
GitHub Service module.
Handles interaction with GitHub REST API:
- Fetching Pull Request unified diffs
- Posting review comments to Pull Requests
"""

import logging
from typing import Optional
import httpx
from github import Github, GithubException, Auth

from app.config import get_settings

logger = logging.getLogger(__name__)


class GitHubService:
    """
    Service client for interacting with GitHub Pull Requests and Comments.
    """

    def __init__(self, token: Optional[str] = None):
        settings = get_settings()
        self.token = token or settings.GITHUB_TOKEN
        auth = Auth.Token(self.token)
        self.client = Github(auth=auth)

    async def fetch_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
        """
        Fetches raw git diff for a specific Pull Request via GitHub REST API with custom Accept header.

        Args:
            repo_full_name: e.g. "octocat/Hello-World"
            pr_number: Pull request integer number

        Returns:
            Unified diff text string.
        """
        url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3.diff",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "DevSentinels-PR-Reviewer"
        }

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(
                    f"Failed to fetch PR diff for {repo_full_name}#{pr_number}: "
                    f"Status {response.status_code} - {response.text}"
                )
                response.raise_for_status()

            return response.text

    async def post_pr_comment(self, repo_full_name: str, pr_number: int, comment_body: str) -> bool:
        """
        Posts a markdown comment onto the Pull Request conversation.

        Args:
            repo_full_name: Repository name with owner (e.g. 'owner/repo')
            pr_number: PR ID number
            comment_body: Markdown content to post

        Returns:
            True if post succeeded, False otherwise.
        """
        try:
            repo = self.client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)
            pr.create_issue_comment(comment_body)
            logger.info(f"Successfully posted DevSentinels review to {repo_full_name}#{pr_number}")
            return True
        except GithubException as g_err:
            logger.error(f"GitHub API error posting comment to {repo_full_name}#{pr_number}: {g_err}")
            return False
        except Exception as err:
            logger.error(f"Unexpected error posting comment to {repo_full_name}#{pr_number}: {err}")
            return False

