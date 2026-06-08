import os
import re
from groq import AsyncGroq

_client: AsyncGroq | None = None


def get_groq_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


async def chat(
    messages: list[dict],
    model: str = "deepseek-r1-distill-llama-70b",
    temperature: float = 0.6,
    max_tokens: int = 4096,
) -> tuple[str, str | None]:
    """Returns (clean_response, thinking_trace). thinking_trace is None for non-R1 models."""
    client = get_groq_client()
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content or ""
    thinking, clean = _extract_thinking(content)
    return clean.strip(), thinking


def _extract_thinking(content: str) -> tuple[str | None, str]:
    match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
    if match:
        thinking = match.group(1).strip()
        clean = content[match.end():].strip()
        return thinking, clean
    return None, content
