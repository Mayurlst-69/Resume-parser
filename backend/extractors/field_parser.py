import re
import os
import json
import httpx
import asyncio
from api.models import ExtractedFields, ParseConfig
from extractors.heuristic_extractor import extract_name_heuristic, extract_position_heuristic

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
#GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MODEL = "llama-3.1-8b-instant"

# ── Clean TEXT ────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Remove null bytes, fix broken spacing from bad PDF font encoding."""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\b([A-Z])(?: ([A-Z]))+\b', lambda m: m.group(0).replace(' ', ''), text)
    return text.strip()

# ── Header section extractor ─────────────────────────────────────────────────

def extract_contact_section(text: str) -> str:
    """
    Smart section extractor 

    Vision: Token optimization must NOT affect accuracy.
    - Send only AI contact section that is relevant (name/position/email/phone)
    - Stop when section break such as EXPERIENCE, EDUCATION
    - If not found section break → Use 40 lines (added more 25 for accuracy)
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Section breaks — When found these text, Assume that contact section have done
    SECTION_BREAKS = re.compile(
        r'^(ประสบการณ์|ประสบการณ์การทำงาน|การศึกษา|ประวัติการศึกษา|'
        r'experience|work experience|work history|education|'
        r'academic|qualification|'
        r'ทักษะ|ความสามารถ|skills|abilities|'
        r'references|เอกสารอ้างอิง|'
        r'โครงการ|project|portfolio|'
        r'รางวัล|award|achievement|'
        r'กิจกรรม|activity|activities)'
        r'\s*[:\-]?\s*$',
        re.IGNORECASE
    )

    contact_lines = []
    for line in lines:
        # Stop when section break (have atleast 5 paragraph)
        if SECTION_BREAKS.match(line) and len(contact_lines) >= 5:
            break
        contact_lines.append(line)

    # If not found any section break  → Use 40 lines
    # 40 > 25 for accuracy, Not token saving
    if len(contact_lines) == len(lines):
        contact_lines = lines[:40]

    return '\n'.join(contact_lines)

# ── General extract section ───────────────────────────────────────────────────

def extract_general_section(text: str) -> str:  
    """
    General Extract mode — Send Full text (safe, no data loss)
    Use when resume has weird format or name not in normally position by default
    """
    return clean_text(text)[:4000]

# ── Certainty parser ──────────────────────────────────────────────────────────

def parse_llm_value(raw: str | None) -> tuple[str | None, str]:
    """
    Parse LLM field value into (value, certainty).
        (value, "confident") — found and sure
        (None,  "unsure")    — found but not sure → "none" from LLM
        (None,  "absent")    — not in resume at all → null from LLM
    """
    if raw is None:
        return None, "absent"
    if str(raw).strip().lower() in ("none", "null", ""):
        return None, "unsure"
    return str(raw).strip(), "confident"


# ── Regex patterns ────────────────────────────────────────────────────────────

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

PHONE_RE = re.compile(
    r'(?<!\d)(?:\+66[\s\-.]?[6-9]\d[\s\-.]?\d{3,4}[\s\-.]?\d{4}|0[689]\d[\s\-.]?\d{3,4}[\s\-.]?\d{4}|02[\s\-.]?\d{3,4}[\s\-.]?\d{4}|0[3-7]\d[\s\-.]?\d{3}[\s\-.]?\d{4})(?!\d)'
)


def extract_email(text: str) -> tuple[str | None, float]:
    match = EMAIL_RE.search(text)
    if match:
        return match.group(0).strip(), 0.97
    return None, 0.0

def clean_email(email: str) -> str | None:
    if not email:
        return None
    cleaned = re.sub(r'\s+', '', email)
    if EMAIL_RE.fullmatch(cleaned):
        return cleaned
    return None

def extract_phone(text: str) -> tuple[str | None, float]:
    match = PHONE_RE.search(text)
    if match:
        raw = match.group(0).strip()
        phone = re.sub(r"[\s]", " ", raw).strip()
        return phone, 0.93
    return None, 0.0

def format_phone(phone: str | None) -> str | None:
    """
    Normalize Thai phone to xxx-xxx-xxxx format.
    Works with: 0812345678, 081 234 5678, 081-234-5678, +66812345678
    """
    if not phone:
        return phone

    # Strip everything except digits
    digits = re.sub(r'\D', '', phone)

    # +66xxxxxxxxx → 0xxxxxxxxx
    if digits.startswith('66') and len(digits) == 11:
        digits = '0' + digits[2:]

    # Format 10-digit Thai mobile: 081-234-5678
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"

    # Format 9-digit landline: 02-123-4567
    if len(digits) == 9:
        return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"

    # Unknown format — return cleaned digits
    return digits


# ── Groq LLM extraction ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a resume parser. Extract fields from resume text and return JSON only.

Output ONLY this JSON object, no other text:
{"name": null, "position": null, "email": null, "phone": null}

Rules:
- name: candidate full name (Thai or English), usually first line.
- position: job title or applied position.
- email: full email address.
- phone: Thai phone number (10 digits).

For each field use exactly one of these values:
1. The actual value — if you found it and are confident
2. "none" — if you see something that might be the field but are not sure
3. JSON null — if the field is clearly not present in the resume at all

- Use JSON null not string "null"
- NO explanations, NO examples, NO other text — JSON only."""


async def extract_fields_groq(
    text: str,
    config: ParseConfig,
) -> tuple[str | None, str, str | None, str, float, str | None, str | None]:
    """
    Returns (name, name_cert, position, position_cert, conf, email_llm, phone_llm)
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return None, "absent", None, "absent", 0.0, None, None

    # ── Mode switch ──
    # concise: smart section break — less noise, better accuracy, fewer tokens
    # general: full text [:4000]   — safe fallback for unusual resume formats
    if config.extract_mode == "concise":
        context = extract_contact_section(clean_text(text))
        mode_hint = "The text below is the contact/header section of the resume."
    else:
        context = extract_general_section(text)
        mode_hint = "The text below is the full resume content."

    user_msg = (
        "Extract name, position, email, and phone from this resume.\n"
        f"{mode_hint}\n\n"
        f"Resume text:\n{context}"
    )

    max_retries = 4
    for attempt in range(max_retries):
        await asyncio.sleep(1.5)
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

                if resp.status_code == 429:
                    wait = 3 * (attempt + 1)
                    await asyncio.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                content = re.sub(r"```json|```", "", content).strip()
                print(f"[GROQ RAW] {content}") # --> for debugging
                parsed = json.loads(content)

                name,     name_cert     = parse_llm_value(parsed.get("name"))
                position, position_cert = parse_llm_value(parsed.get("position"))
                email_llm, _            = parse_llm_value(
                    parsed.get("email") or
                    next((v for k, v in parsed.items() if "mail" in k.lower()), None)
                )
                phone_llm, _ = parse_llm_value(parsed.get("phone"))

                # Clean email spaces
                if email_llm:
                    email_llm = clean_email(email_llm)

                found_conf = sum(1 for c in [name_cert, position_cert] if c == "confident")
                found_any  = sum(1 for c in [name_cert, position_cert] if c != "absent")
                conf = 0.90 if found_conf == 2 else (0.75 if found_conf == 1 else (0.40 if found_any > 0 else 0.0))

                return name, name_cert, position, position_cert, conf, email_llm, phone_llm

        except Exception as e:
            print(f"[GROQ ERROR] attempt={attempt} error={e}") # --> for debugging
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            continue

    return None, "absent", None, "absent", 0.0, None, None


# ── Heuristic validation: sanity-check AI output ─────────────────────────────

def sanity_check_name(name: str | None, text: str) -> tuple[str | None, str]:
    """
    Cross-check AI name result against heuristic.
    If AI confident but heuristic disagrees strongly → downgrade to unsure.
    """
    if name is None:
        return name, "absent"

    # Hallucination signals
    hallucination_patterns = [
        r'^\d+$',                          # pure numbers
        r'(company|บริษัท|ltd|co\.,)',      # company name
        r'(university|มหาวิทยาลัย|วิทยาลัย|การศึกษา|College|University)',        # university
        r'.{81,}',                          # too long (>80 chars)
        r'^(resume|cv|curriculum vitae)',   # document title
    ]
    for pat in hallucination_patterns:
        if re.search(pat, name, re.IGNORECASE):
            print(f"[HEURISTIC] name hallucination detected: {name!r}")
            return None, "unsure"

    return name, "confident"


def sanity_check_position(position: str | None) -> tuple[str | None, str]:
    """Basic sanity check for position field."""
    if position is None:
        return None, "absent"
    if len(position) > 100 or re.match(r'^\d+$', position):
        print(f"[HEURISTIC] position suspicious: {position!r}")
        return None, "unsure"
    return position, "confident"

# ── Main entry point ──────────────────────────────────────────────────────────

async def parse_fields(text: str, config: ParseConfig) -> ExtractedFields:
    """
    3-layer extraction:
        Layer 1: Regex (email, phone) — deterministic
        Layer 2: LLM (name, position, fallback email/phone)
        Layer 3: Heuristic fallback when AI fails or is unsure
    """
    text = clean_text(text)
    empty = None if config.empty_value == "null" else ""


    # ── Layer 1:Regex ──
    email_regex, email_conf = extract_email(text) if config.extract_email else (empty, 0)
    phone_regex, phone_conf = extract_phone(text) if config.extract_phone else (empty, 0)

    # ── Layer 2:LLM ──
    name, name_cert, position, position_cert, llm_conf, email_llm, phone_llm = \
        await extract_fields_groq(text, config)
    
    # ── Sanity check AI output (catch hallucinations) ──
    name,     name_cert     = sanity_check_name(name, text)
    position, position_cert = sanity_check_position(position)

    # ── Layer 3: Heuristic fallback ──
    # Only kick in when AI failed (absent) or unsure
    if config.extract_name and name_cert in ("absent", "unsure"):
        h_name, h_conf = extract_name_heuristic(text)
        if h_name:
            print(f"[HEURISTIC] name fallback: {h_name!r} conf={h_conf}")
            name      = h_name
            name_cert = "confident" if h_conf >= 0.75 else "unsure"
            # Blend confidence — heuristic is less reliable than Groq
            llm_conf  = max(llm_conf, h_conf * 0.85)

    if config.extract_position and position_cert in ("absent", "unsure"):
        h_pos, h_conf = extract_position_heuristic(text)
        if h_pos:
            print(f"[HEURISTIC] position fallback: {h_pos!r} conf={h_conf}")
            position      = h_pos
            position_cert = "confident" if h_conf >= 0.75 else "unsure"
            llm_conf      = max(llm_conf, h_conf * 0.85)

    # ── Resolve final values ──
    def resolve(value, cert):
        """absent → empty (follow toggle), unsure → None (UI shows ?), confident → value"""
        if value is not None:
            return value
        if cert == "unsure":
            return None   # UI bypasses toggle, shows "?"
        return empty      # absent → follow toggle

    # Regex wins if found, Groq fills in as fallback
    final_email = email_regex or email_llm or empty
    final_phone = format_phone(phone_regex or phone_llm) or empty

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
        name=resolve(name, name_cert),
        name_cert=name_cert,
        position=resolve(position, position_cert),
        position_cert=position_cert,
        phone=final_phone,
        email=final_email,
        confidence=confidence,
    )