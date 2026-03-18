import re
import os
import json
import httpx
from api.models import ExtractedFields, ParseConfig
import asyncio  

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
#GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MODEL = "llama-3.1-8b-instant"

# ── Clean TEXT ─────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Remove null bytes, fix broken spacing from bad PDF font encoding."""
    # Remove null bytes and other control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Collapse multiple spaces into one
    text = re.sub(r' {2,}', ' ', text)
    # Fix spaced-out English
    text = re.sub(r'\b([A-Z])(?: ([A-Z]))+\b', lambda m: m.group(0).replace(' ', ''), text)
    return text.strip()

# ── Regex patterns ─────────────────────────────────────────────────────────────

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

PHONE_RE = re.compile(r'(?<!\d)(?:\+66[\s\-.]?[6-9]\d[\s\-.]?\d{3,4}[\s\-.]?\d{4}|0[689]\d[\s\-.]?\d{3,4}[\s\-.]?\d{4}|02[\s\-.]?\d{3,4}[\s\-.]?\d{4}|0[3-7]\d[\s\-.]?\d{3}[\s\-.]?\d{4})(?!\d)')


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

SYSTEM_PROMPT = """You are a resume parser. Extract fields from resume text and return JSON only.

Output ONLY this JSON object, no other text:
{"name": null, "position": null, "email": null, "phone": null}

Rules:
- name: candidate full name (Thai or English), usually first line. null if not found.
- position: job title or applied position. null if not found.
- email: full email address. null if not found or incomplete.
- phone: Thai phone number (10 digits). null if not found.
- Use JSON null not string "null"
- NO explanations, NO examples, NO other text — JSON only."""

async def extract_fields_groq(
    text: str,
    config: ParseConfig,
    ) -> tuple[str | None, str | None, float, str | None, str | None]:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return None, None, 0.0, None, None

    snippet = clean_text(text)[:4000]

    user_msg = (
        "Extract name, position, email, and phone from this resume.\n\n"
        f"Resume text:\n{snippet}"
    )

    # Retry up to 4 times with backoff for rate limit 429
    max_retries = 4
    for attempt in range(max_retries):
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
                        "temperature": 0.0,
                        "max_tokens": 200,
                    },
                )

                # Rate limit hit — wait and retry
                if resp.status_code == 429:
                    wait = 3 * (attempt + 1)  # 3s, 6s, 9s, 12s
                    await asyncio.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                content = re.sub(r"```json|```", "", content).strip()
                print(f"[GROQ RAW] {content}") 
                parsed = json.loads(content)

                name = parsed.get("name") or None
                position = parsed.get("position") or None
                email_llm = (
                    parsed.get("email") or
                    next((v for k, v in parsed.items() if "mail" in k.lower()), None)
                ) or None
                phone_llm = parsed.get("phone") or None

                if name == "null": name = None
                if position == "null": position = None
                if email_llm == "null": email_llm = None
                if phone_llm == "null": phone_llm = None
                
                found = sum(1 for v in [name, position] if v)
                conf = 0.90 if found == 2 else (0.75 if found == 1 else 0.0)
                return name, position, conf, email_llm, phone_llm

        except Exception as e:
            print(f"[GROQ ERROR] attempt={attempt} error={e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            continue

    return None, None, 0.0, None, None


# ── Main entry point ───────────────────────────────────────────────────────────

async def parse_fields(text: str, config: ParseConfig) -> ExtractedFields:
    """
    Hybrid extraction:
        - email, phone → regex (deterministic)
        - name, position → Groq LLM
    Returns ExtractedFields with confidence score.
    """
    text = clean_text(text)
    empty = None if config.empty_value == "null" else ""

    email_regex, email_conf = extract_email(text) if config.extract_email else (empty, 0)
    phone_regex, phone_conf = extract_phone(text) if config.extract_phone else (empty, 0)

    name, position, llm_conf, email_llm, phone_llm = await extract_fields_groq(text, config)

    # Regex wins if found, Groq fills in as fallback
    final_email = email_regex or email_llm or empty
    final_phone = phone_regex or phone_llm or empty
    
    # Recalculate email/phone confidence
    email_final_conf = email_conf if email_regex else (0.75 if email_llm else 0.0)
    phone_final_conf = phone_conf if phone_regex else (0.75 if phone_llm else 0.0)

    scores = []
    if config.extract_email:
        scores.append(email_final_conf if final_email else 0.0)
    if config.extract_phone:
        scores.append(phone_final_conf if final_phone else 0.0)
    if config.extract_name or config.extract_position:
        scores.append(llm_conf)

    confidence = round(sum(scores) / len(scores), 2) if scores else 0.0

    return ExtractedFields(
        name=name or empty,
        position=position or empty,
        phone=final_phone,
        email=final_email,
        confidence=confidence,
    )
