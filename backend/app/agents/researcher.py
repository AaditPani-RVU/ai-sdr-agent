"""
Researcher Agent — Week 1 core.

Flow: prospect input → Tavily web search → website scrape → DeepSeek R1 analysis → ResearchResult
"""
import os
import json
import httpx
from app.schemas import ProspectCreate, ResearchResult
from app.services.groq_client import chat

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_URL = "https://api.tavily.com/search"

RESEARCH_SYSTEM_PROMPT = """You are an expert B2B sales researcher. Given information about a company and prospect, your job is to:
1. Understand what the company does and their business model
2. Identify their likely pain points and challenges
3. Find specific personalization hooks (recent news, funding, hiring, product launches, etc.)
4. Recommend the best outreach angle for a cold email

IMPORTANT: If web search results are empty or unhelpful, use your own knowledge of the company. Most well-known companies are in your training data — draw on that. Never output generic "no information available" answers. Always produce specific, useful research based on what you know about the company and the prospect's role.

You MUST respond with valid JSON only (no markdown, no extra text) in this exact structure:
{
  "company_summary": "2-3 sentence description of what the company does and their stage",
  "pain_points": ["pain point 1", "pain point 2", "pain point 3"],
  "personalization_hooks": ["specific hook 1", "specific hook 2"],
  "recommended_angle": "The single best angle for cold outreach to this specific prospect",
  "confidence_score": 0.0
}

confidence_score is 0.0-1.0 based on how much concrete information you found."""

RESEARCH_USER_TEMPLATE = """Research this prospect and their company for a cold outreach campaign:

Prospect: {first_name} {last_name}, {role} at {company}
Company website: {website_url}
LinkedIn: {linkedin_url}

Web research findings:
{search_results}

Website content (if available):
{website_content}

Analyze this information deeply. If search results are sparse, draw on your own knowledge of {company} to fill the gaps — do not admit ignorance, produce useful research.

Think about:
- What specific challenges does a {role} at this type of company face?
- What recent events (hiring sprees, funding, product launches, layoffs) create urgency?
- What would make this person open a cold email?
- What outcome can we promise that maps to their KPIs?

Return only valid JSON."""


async def _tavily_search(query: str) -> list[dict]:
    if not TAVILY_API_KEY:
        return []
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                TAVILY_URL,
                json={"api_key": TAVILY_API_KEY, "query": query, "max_results": 5, "search_depth": "basic"},
            )
            resp.raise_for_status()
            return resp.json().get("results", [])
        except Exception:
            return []


async def _scrape_website(url: str) -> str:
    if not url:
        return ""
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            # strip tags crudely — good enough for context feeding
            import re
            text = re.sub(r"<[^>]+>", " ", resp.text)
            text = re.sub(r"\s+", " ", text)
            return text[:3000]
        except Exception:
            return ""


def _format_search_results(results: list[dict]) -> str:
    if not results:
        return "No search results found."
    lines = []
    for r in results:
        lines.append(f"- {r.get('title', '')}: {r.get('content', '')[:300]}")
    return "\n".join(lines)


async def research_prospect(prospect: ProspectCreate, prospect_id: int) -> ResearchResult:
    company = prospect.company
    name = f"{prospect.first_name} {prospect.last_name}"

    # Parallel searches
    import asyncio
    results_company, results_news, results_person = await asyncio.gather(
        _tavily_search(f"{company} company overview business model"),
        _tavily_search(f"{company} recent news funding hiring 2024 2025"),
        _tavily_search(f"{name} {company} {prospect.role}"),
    )

    all_results = results_company + results_news + results_person
    search_text = _format_search_results(all_results)
    website_content = await _scrape_website(prospect.website_url or "")

    messages = [
        {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": RESEARCH_USER_TEMPLATE.format(
                first_name=prospect.first_name,
                last_name=prospect.last_name,
                role=prospect.role,
                company=prospect.company,
                website_url=prospect.website_url or "not provided",
                linkedin_url=prospect.linkedin_url or "not provided",
                search_results=search_text,
                website_content=website_content or "not available",
            ),
        },
    ]

    clean_response, thinking_trace = await chat(messages, model="llama-3.3-70b-versatile", temperature=0.5)

    try:
        data = json.loads(clean_response)
    except json.JSONDecodeError:
        # fallback: extract JSON block if model wrapped it
        import re
        match = re.search(r"\{.*\}", clean_response, re.DOTALL)
        data = json.loads(match.group()) if match else {}

    return ResearchResult(
        prospect_id=prospect_id,
        company_summary=data.get("company_summary", ""),
        pain_points=data.get("pain_points", []),
        personalization_hooks=data.get("personalization_hooks", []),
        recommended_angle=data.get("recommended_angle", ""),
        thinking_trace=thinking_trace,
        confidence_score=float(data.get("confidence_score", 0.5)),
    )
