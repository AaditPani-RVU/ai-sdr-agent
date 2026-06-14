"""Contact Finder Agent — discovers key contacts at a company using web search."""
import json
import logging
import os
import re

import httpx

from app.schemas import ContactCandidate, ContactFinderRequest
from app.services.groq_client import chat

logger = logging.getLogger(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_URL = "https://api.tavily.com/search"

FINDER_SYSTEM_PROMPT = """You are a B2B sales researcher. Given web search results about a company,
extract real people who work there and match the requested roles.

Return ONLY valid JSON — an array of objects with this exact structure:
[
  {
    "first_name": "Jane",
    "last_name": "Doe",
    "role": "VP of Marketing",
    "email": "jane.doe@company.com",
    "linkedin_url": "https://linkedin.com/in/janedoe",
    "confidence": 0.85,
    "source": "url where you found this person"
  }
]

Rules:
- Only include real named individuals — no "Contact Us" or generic roles.
- For email: if you found it explicitly, use it. If not, infer from the company domain
  using the most common pattern (first.last@domain.com). Mark inferred emails with
  confidence < 0.7.
- If a person's role doesn't match the requested roles, still include them if they are
  a senior decision-maker (C-suite, VP, Director, Head of).
- If no contacts found, return an empty array [].
- Do NOT fabricate people. Only include people you found evidence of in the search results."""

FINDER_USER_TEMPLATE = """Find key contacts at {company} for a B2B outreach campaign.

Target roles: {roles}
Company website: {website_url}
Company domain: {domain}

Web search results:
{search_results}

Extract real people from these results. For emails not found explicitly, infer using the company
domain ({domain}) with the most likely format based on any emails you see in the results.

Return JSON array only."""


async def _tavily_search(query: str) -> list[dict]:
    if not TAVILY_API_KEY:
        return []
    async with httpx.AsyncClient(timeout=12.0) as client:
        try:
            resp = await client.post(
                TAVILY_URL,
                json={"api_key": TAVILY_API_KEY, "query": query, "max_results": 6, "search_depth": "basic"},
            )
            resp.raise_for_status()
            return resp.json().get("results", [])
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}")
            return []


def _extract_domain(website_url: str | None) -> str:
    if not website_url:
        return ""
    match = re.search(r"https?://(?:www\.)?([^/]+)", website_url)
    return match.group(1) if match else ""


def _format_results(results: list[dict]) -> str:
    if not results:
        return "No results found."
    return "\n\n".join(
        f"[{r.get('title', '')}]\nURL: {r.get('url', '')}\n{r.get('content', '')[:400]}"
        for r in results
    )


async def find_contacts(request: ContactFinderRequest) -> list[ContactCandidate]:
    import asyncio

    company = request.company
    roles_str = ", ".join(request.roles)
    domain = _extract_domain(request.website_url)

    results_team, results_linkedin, results_leadership = await asyncio.gather(
        _tavily_search(f"{company} team leadership about site:{domain}" if domain else f"{company} team leadership about"),
        _tavily_search(f"site:linkedin.com/in {company} {roles_str}"),
        _tavily_search(f"{company} {roles_str} email contact"),
    )

    all_results = results_team + results_linkedin + results_leadership
    search_text = _format_results(all_results)

    messages = [
        {"role": "system", "content": FINDER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": FINDER_USER_TEMPLATE.format(
                company=company,
                roles=roles_str,
                website_url=request.website_url or "not provided",
                domain=domain or "unknown",
                search_results=search_text,
            ),
        },
    ]

    raw, _ = await chat(messages, model="llama-3.3-70b-versatile", temperature=0.2)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        data = json.loads(match.group()) if match else []

    if not isinstance(data, list):
        return []

    contacts = []
    for item in data:
        try:
            contacts.append(
                ContactCandidate(
                    first_name=item.get("first_name", ""),
                    last_name=item.get("last_name", ""),
                    role=item.get("role", ""),
                    company=company,
                    email=item.get("email"),
                    linkedin_url=item.get("linkedin_url"),
                    website_url=request.website_url,
                    confidence=float(item.get("confidence", 0.5)),
                    source=item.get("source"),
                )
            )
        except Exception:
            continue

    return contacts
