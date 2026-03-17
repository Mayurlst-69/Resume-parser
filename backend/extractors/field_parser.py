import re
import os
import json
import httpx
from api.models import ExtractedFields, ParseConfig

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Regex patterns ─────────────────────────────────────────────────────────────

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

PHONE_RE = re.compile(
    r"""
    (?:
        (?:\+66|0066|66)?          # Thailand country code optional
        [\s\-.]?
        [689]\d{1}                 # Thai mobile prefix (08x, 09x, 06x)
        [\s\-.]?
        \d{3,4}
        [\s\-.]?
        \d{3,4}
    |
        \+?[\d\s\-().]{7,18}       # International generic fallback
    )
    """,
    re.VERBOSE,
)


def extract_email(text: str) -> tuple[str | None, float]:
    match = EMAIL_RE.search(text)
    if match:
        return match.group(0).strip(), 0.97
    return None, 0.0


def extract_phone(text: str) -> tuple[str | None, float]:
    match = PHONE_RE.search(text)
    if match:
        raw = match.group(0).strip()
        # Clean up spacing
        phone = re.sub(r"[\s]", " ", raw).strip()
        return phone, 0.93
    return None, 0.0


# ── Groq LLM extraction ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a resume parser. Given raw resume text (may be Thai or English),
extract the requested fields. Respond ONLY with a valid JSON object — no markdown, no explanation.
If a field cannot be found, return null for that field.

Format:
{
  "name": "Full Name or null",
  "position": "Job Title / Position or null"
}"""


async def extract_fields_groq(
    text: str,
    config: ParseConfig,
) -> tuple[str | None, str | None, float]:
    """
    Call Groq API to extract name and position from resume text.
    Returns (name, position, confidence).
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return None, None, 0.0

    # Truncate to avoid token limits — first 3000 chars has all header info
    snippet = text[:3000]

    fields_requested = []
    if config.extract_name:
        fields_requested.append("name")
    if config.extract_position:
        fields_requested.append("position")

    user_msg = f"Extract these fields: {', '.join(fields_requested)}\n\nResume text:\n{snippet}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 200,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Strip possible markdown fences
            content = re.sub(r"```json|```", "", content).strip()
            parsed = json.loads(content)

            name = parsed.get("name") or None
            position = parsed.get("position") or None

            # Confidence: both found = 0.90, one found = 0.75, none = 0.0
            found = sum(1 for v in [name, position] if v)
            conf = 0.90 if found == 2 else (0.75 if found == 1 else 0.0)

            return name, position, conf

    except Exception as e:
        return None, None, 0.0


# ── Main entry point ───────────────────────────────────────────────────────────

async def parse_fields(text: str, config: ParseConfig) -> ExtractedFields:
    """
    Hybrid extraction:
      - email, phone → regex (deterministic)
      - name, position → Groq LLM
    Returns ExtractedFields with confidence score.
    """
    empty = None if config.empty_value == "null" else ""

    email, email_conf = extract_email(text) if config.extract_email else (empty, 0)
    phone, phone_conf = extract_phone(text) if config.extract_phone else (empty, 0)

    name, position, llm_conf = await extract_fields_groq(text, config)

    # Final confidence = weighted average of found fields
    scores = []
    if config.extract_email:
        scores.append(email_conf if email else 0.0)
    if config.extract_phone:
        scores.append(phone_conf if phone else 0.0)
    if config.extract_name or config.extract_position:
        scores.append(llm_conf)

    confidence = round(sum(scores) / len(scores), 2) if scores else 0.0

    return ExtractedFields(
        name=name or empty,
        position=position or empty,
        phone=phone or empty,
        email=email or empty,
        confidence=confidence,
    )
