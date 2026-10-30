"""
LangGraph Multi-Agent Workflow for PR Review and Security Auditing.
Orchestrates Bug Analysis, Security Audit, Refactoring Analysis, and Final Aggregation.
"""

import os
from typing import TypedDict, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

from app.config import get_settings
from app.agents.prompts import (
    BUG_LOGIC_PROMPT,
    SECURITY_PROMPT,
    REFACTORING_PROMPT,
)


class PRReviewState(TypedDict):
    """
    State tracking schema throughout the LangGraph workflow execution.
    """
    repo_name: str
    pr_number: int
    pr_title: str
    pr_author: str
    diff_text: str
    bug_review: Optional[str]
    security_review: Optional[str]
    refactoring_review: Optional[str]
    final_summary: Optional[str]
    error: Optional[str]


def _get_llm() -> ChatGoogleGenerativeAI:
    """
    Helper to instantiate Gemini LLM client with configured settings.
    """
    settings = get_settings()
    api_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    model = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.2,
    )


async def bug_logic_agent_node(state: PRReviewState) -> dict:
    """
    Agent Node 1: Detects syntax, logic bugs, unhandled exceptions, and edge conditions.
    """
    llm = _get_llm()
    user_prompt = (
        f"Repository: {state['repo_name']}\n"
        f"PR #{state['pr_number']}: {state['pr_title']}\n"
        f"Author: {state['pr_author']}\n\n"
        f"### Code Diff to Analyze:\n```diff\n{state['diff_text']}\n```"
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=BUG_LOGIC_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        return {"bug_review": response.content}
    except Exception as exc:
        return {"bug_review": f"⚠️ Bug analysis failed: {str(exc)}"}


async def security_agent_node(state: PRReviewState) -> dict:
    """
    Agent Node 2: Audits security vulnerabilities, hardcoded secrets, and OWASP flaws.
    """
    llm = _get_llm()
    user_prompt = (
        f"Repository: {state['repo_name']}\n"
        f"PR #{state['pr_number']}: {state['pr_title']}\n"
        f"Author: {state['pr_author']}\n\n"
        f"### Code Diff to Analyze:\n```diff\n{state['diff_text']}\n```"
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=SECURITY_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        return {"security_review": response.content}
    except Exception as exc:
        return {"security_review": f"⚠️ Security audit failed: {str(exc)}"}


async def refactoring_agent_node(state: PRReviewState) -> dict:
    """
    Agent Node 3: Evaluates clean code standards, optimization, and maintainability.
    """
    llm = _get_llm()
    user_prompt = (
        f"Repository: {state['repo_name']}\n"
        f"PR #{state['pr_number']}: {state['pr_title']}\n"
        f"Author: {state['pr_author']}\n\n"
        f"### Code Diff to Analyze:\n```diff\n{state['diff_text']}\n```"
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=REFACTORING_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        return {"refactoring_review": response.content}
    except Exception as exc:
        return {"refactoring_review": f"⚠️ Refactoring assessment failed: {str(exc)}"}


async def aggregator_node(state: PRReviewState) -> dict:
    """
    Combines agent reviews into a comprehensive, beautifully structured GitHub Markdown comment.
    """
    repo = state["repo_name"]
    pr_num = state["pr_number"]
    title = state["pr_title"]
    author = state["pr_author"]

    bug_section = state.get("bug_review") or "No bug findings reported."
    sec_section = state.get("security_review") or "No security findings reported."
    refactor_section = state.get("refactoring_review") or "No refactoring suggestions reported."

    markdown_summary = f"""## 🛡️ DevSentinels Automated PR Review

> **PR #{pr_num}**: {title}  
> **Author**: @{author} | **Repository**: `{repo}`  
> **Engine**: LangGraph Multi-Agent Sentinel Workflow

---

### 1. 🐛 Bug & Logic Analysis
{bug_section}

---

### 2. 🔒 Security & Secrets Audit
{sec_section}

---

### 3. 🚀 Refactoring & Performance Optimizations
{refactor_section}

---
*Generated with care by **DevSentinels** • Automated Pull Request Sentinel*
"""
    return {"final_summary": markdown_summary}


def build_review_graph():
    """
    Constructs and compiles the LangGraph state graph.
    Execution flow:
      START -> Bug Agent -> Security Agent -> Refactoring Agent -> Aggregator -> END
    """
    workflow = StateGraph(PRReviewState)

    # Register nodes
    workflow.add_node("bug_agent", bug_logic_agent_node)
    workflow.add_node("security_agent", security_agent_node)
    workflow.add_node("refactoring_agent", refactoring_agent_node)
    workflow.add_node("aggregator", aggregator_node)

    # Define execution edges
    workflow.set_entry_point("bug_agent")
    workflow.add_edge("bug_agent", "security_agent")
    workflow.add_edge("security_agent", "refactoring_agent")
    workflow.add_edge("refactoring_agent", "aggregator")
    workflow.add_edge("aggregator", END)

    return workflow.compile()


# Pre-compiled instance ready for execution
review_graph = build_review_graph()

