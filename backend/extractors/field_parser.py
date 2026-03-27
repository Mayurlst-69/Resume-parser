import re
import os
import json
import asyncio
from api.models import ExtractedFields, ParseConfig
from extractors.heuristic_extractor import extract_name_heuristic, extract_position_heuristic

# ── LiteLLM — unified multi-provider interface ────────────────────────────────
import litellm
litellm.suppress_debug_info = True
litellm.set_verbose = False

# Default model
DEFAULT_MODEL = "groq/llama-3.3-70b-versatile"

# ── Model prefix map — LiteLLM uses "provider/model_id" format ───────────────
# Docs: https://docs.litellm.ai/docs/providers
MODEL_PREFIX_MAP = {
    "groq":      "groq/",
    "openai":    "",           # openai models use no prefix
    "anthropic": "anthropic/",
    "google":    "gemini/",
}

# ── All available models by provider ─────────────────────────────────────────
ALL_MODELS = [
    # Groq — Free tier
    {
        "provider": "groq", "provider_label": "Groq (Free)",
        "id": "llama-3.3-70b-versatile",
        "litellm_id": "groq/llama-3.3-70b-versatile",
        "label": "Llama 3.3 70B",
        "context": "128k", "speed": "fast",
        "desc": "Meta's best open model. Recommended for Thai resume parsing.",
        "free": True,
    },
    {
        "provider": "groq", "provider_label": "Groq (Free)",
        "id": "llama-3.1-8b-instant",
        "litellm_id": "groq/llama-3.1-8b-instant",
        "label": "Llama 3.1 8B",
        "context": "128k", "speed": "fastest",
        "desc": "Lightweight and fast. Separate quota from 70B.",
        "free": True,
    },
    {
        "provider": "groq", "provider_label": "Groq (Free)",
        "id": "gemma2-9b-it",
        "litellm_id": "groq/gemma2-9b-it",
        "label": "Gemma 2 9B",
        "context": "8k", "speed": "fast",
        "desc": "Google's open model hosted on Groq.",
        "free": True,
    },
    {
        "provider": "groq", "provider_label": "Groq (Free)",
        "id": "mixtral-8x7b-32768",
        "litellm_id": "groq/mixtral-8x7b-32768",
        "label": "Mixtral 8x7B",
        "context": "32k", "speed": "fast",
        "desc": "Mistral's MoE model. Great for long resumes.",
        "free": True,
    },
    # OpenAI
    {
        "provider": "openai", "provider_label": "OpenAI",
        "id": "gpt-4o",
        "litellm_id": "gpt-4o",
        "label": "GPT-4o",
        "context": "128k", "speed": "fast",
        "desc": "OpenAI's flagship model. Excellent accuracy.",
        "free": False,
    },
    {
        "provider": "openai", "provider_label": "OpenAI",
        "id": "gpt-4o-mini",
        "litellm_id": "gpt-4o-mini",
        "label": "GPT-4o Mini",
        "context": "128k", "speed": "fastest",
        "desc": "Fast and affordable. Great balance of speed and accuracy.",
        "free": False,
    },
    # Anthropic
    {
        "provider": "anthropic", "provider_label": "Anthropic",
        "id": "claude-sonnet-4-6",
        "litellm_id": "anthropic/claude-sonnet-4-6",
        "label": "Claude Sonnet 4.6",
        "context": "200k", "speed": "fast",
        "desc": "Anthropic's balanced model. Strong multilingual understanding.",
        "free": False,
    },
    {
        "provider": "anthropic", "provider_label": "Anthropic",
        "id": "claude-opus-4-6",
        "litellm_id": "anthropic/claude-opus-4-6",
        "label": "Claude Opus 4.6",
        "context": "200k", "speed": "medium",
        "desc": "Anthropic's most powerful model. Best for complex documents.",
        "free": False,
    },
    # Google
    {
        "provider": "google", "provider_label": "Google",
        "id": "gemini-1.5-pro",
        "litellm_id": "gemini/gemini-1.5-pro",
        "label": "Gemini 1.5 Pro",
        "context": "1M", "speed": "fast",
        "desc": "Google's best model. Massive context window.",
        "free": False,
    },
    {
        "provider": "google", "provider_label": "Google",
        "id": "gemini-1.5-flash",
        "litellm_id": "gemini/gemini-1.5-flash",
        "label": "Gemini 1.5 Flash",
        "context": "1M", "speed": "fastest",
        "desc": "Fast and affordable. Good Thai language support.",
        "free": False,
    },
]

# ── Helper: resolve litellm model id + api key ────────────────────────────────

def _resolve_model(config: ParseConfig) -> tuple[str, str]:
    """
    Returns (litellm_model_id, api_key)
    Looks up the litellm_id from ALL_MODELS, falls back to prefixing.
    API key: UI config → env fallback
    """
    model_id = config.model or DEFAULT_MODEL
    ui_keys  = config.api_keys or {}

    # Find in ALL_MODELS to get litellm_id + provider
    model_info = next((m for m in ALL_MODELS if m["id"] == model_id), None)

    if model_info:
        litellm_id = model_info["litellm_id"]
        provider   = model_info["provider"]
    else:
        # Custom model — user typed their own id
        # Try to detect provider from prefix (e.g. "groq/...", "anthropic/...")
        if "/" in model_id:
            provider   = model_id.split("/")[0]
            litellm_id = model_id
        else:
            # Default to groq if no prefix
            provider   = "groq"
            litellm_id = f"groq/{model_id}"

    # Resolve API key: UI → env
    env_map = {
        "groq":      "GROQ_API_KEY",
        "openai":    "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google":    "GOOGLE_API_KEY",
    }
    api_key = ui_keys.get(provider) or os.getenv(env_map.get(provider, ""), "")

    return litellm_id, api_key


# ── Clean TEXT ────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\b([A-Z])(?: ([A-Z]))+\b', lambda m: m.group(0).replace(' ', ''), text)
    return text.strip()


def extract_contact_section(text: str) -> str:
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    SECTION_BREAKS = re.compile(
        r'^(ประสบการณ์|ประสบการณ์การทำงาน|การศึกษา|ประวัติการศึกษา|'
        r'experience|work experience|work history|education|'
        r'academic|qualification|ทักษะ|ความสามารถ|skills|abilities|'
        r'references|เอกสารอ้างอิง|โครงการ|project|portfolio|'
        r'รางวัล|award|achievement|กิจกรรม|activity|activities)'
        r'\s*[:\-]?\s*$',
        re.IGNORECASE
    )
    contact_lines = []
    for line in lines:
        if SECTION_BREAKS.match(line) and len(contact_lines) >= 5:
            break
        contact_lines.append(line)
    if len(contact_lines) == len(lines):
        contact_lines = lines[:40]
    return '\n'.join(contact_lines)


def extract_general_section(text: str) -> str:
    return clean_text(text)[:4000]


# ── Certainty parser ──────────────────────────────────────────────────────────

def parse_llm_value(raw) -> tuple[str | None, str]:
    if raw is None:
        return None, "absent"
    if str(raw).strip().lower() in ("none", "null", ""):
        return None, "unsure"
    return str(raw).strip(), "confident"


# ── Regex patterns ────────────────────────────────────────────────────────────

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r'(?<!\d)(?:\+66[\s\-.]?[6-9]\d[\s\-.]?\d{3,4}[\s\-.]?\d{4}|0[689]\d[\s\-.]?\d{3,4}[\s\-.]?\d{4}|02[\s\-.]?\d{3,4}[\s\-.]?\d{4}|0[3-7]\d[\s\-.]?\d{3}[\s\-.]?\d{4})(?!\d)'
)
THAI_ADDRESS_RE = re.compile(
    r'(?:ที่อยู่|address|บ้านเลขที่|เลขที่|อาคาร)\s*[:\-]?\s*(.{10,120})'
    r'|(\d+[/\d]*\s+.{5,80}(?:จังหวัด|จ\.|กรุงเทพ|กทม\.|อำเภอ|อ\.|เขต|ตำบล|ต\.|แขวง|ถนน|ถ\.|หมู่|ม\.|ซอย|ซ\.)[^\n]{0,50}(?:\d{5})?)',
    re.IGNORECASE
)


def extract_email(text: str) -> tuple[str | None, float]:
    match = EMAIL_RE.search(text)
    return (match.group(0).strip(), 0.97) if match else (None, 0.0)


def clean_email(email: str) -> str | None:
    if not email:
        return None
    cleaned = re.sub(r'\s+', '', email)
    return cleaned if EMAIL_RE.fullmatch(cleaned) else None


def extract_phone(text: str) -> tuple[str | None, float]:
    match = PHONE_RE.search(text)
    if match:
        return re.sub(r"[\s]", " ", match.group(0).strip()), 0.93
    return None, 0.0


def format_phone(phone: str | None) -> str | None:
    if not phone:
        return phone
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('66') and len(digits) == 11:
        digits = '0' + digits[2:]
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    if len(digits) == 9:
        return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
    return digits


def extract_address(text: str) -> tuple[str | None, float]:
    match = THAI_ADDRESS_RE.search(text)
    if match:
        addr = (match.group(1) or match.group(2) or "").strip()
        if addr and len(addr) > 10:
            return addr[:150], 0.72
    return None, 0.0


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a resume parser. Extract fields from resume text and return JSON only.

Output ONLY this JSON object, no other text:
{"name": null, "position": null, "email": null, "phone": null, "education": null, "experience": null}

Rules:
- name: candidate full name (Thai or English), usually first line.
- position: job title or applied position.
- email: full email address.
- phone: Thai phone number (10 digits).
- education: highest education level and institution. Summarize in 1-2 lines max.
- experience: most recent job title + company + duration. Summarize in 1-2 lines max.

For each field use exactly one of these values:
1. The actual value — if you found it and are confident
2. "none" — if you see something but are not sure
3. JSON null — if the field is clearly not present

- Use JSON null not string "null"
- NO explanations, NO other text, NO examples — JSON only."""


# ── LLM extraction via LiteLLM ────────────────────────────────────────────────

async def extract_fields_llm(
    text: str,
    config: ParseConfig,
) -> tuple[str | None, str, str | None, str, float, str | None, str | None, str | None, str | None]:
    """
    Multi-provider LLM extraction using LiteLLM.
    Returns (name, name_cert, position, position_cert, conf,
             email_llm, phone_llm, education_llm, experience_llm)
    """
    litellm_id, api_key = _resolve_model(config)

    if not api_key:
        print(f"[LLM] No API key for model: {litellm_id}")
        return None, "absent", None, "absent", 0.0, None, None, None, None

    # ── Context selection ──
    need_full_text = config.extract_education or config.extract_experience
    if need_full_text or config.extract_mode == "general":
        context   = extract_general_section(text)
        mode_hint = "The text below is the full resume content."
    else:
        context   = extract_contact_section(clean_text(text))
        mode_hint = "The text below is the contact/header section of the resume."

    requested = ["name", "position", "email", "phone"]
    if config.extract_education:  requested.append("education")
    if config.extract_experience: requested.append("experience")

    user_msg = (
        f"Extract these fields: {', '.join(requested)}.\n"
        f"{mode_hint}\n\n"
        f"Resume text:\n{context}"
    )

    max_retries = 4
    for attempt in range(max_retries):
        await asyncio.sleep(1.5)
        try:
            # ── LiteLLM call — one line handles all providers ──
            response = await litellm.acompletion(
                model=litellm_id,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                api_key=api_key,
                temperature=0.0,
                max_tokens=400,
                timeout=30,
            )

            content = response.choices[0].message.content.strip()
            content = re.sub(r"```json|```", "", content).strip()
            print(f"[LLM RAW] {litellm_id}: {content}")
            parsed = json.loads(content)

            name,     name_cert     = parse_llm_value(parsed.get("name"))
            position, position_cert = parse_llm_value(parsed.get("position"))
            email_llm, _ = parse_llm_value(
                parsed.get("email") or
                next((v for k, v in parsed.items() if "mail" in k.lower()), None)
            )
            phone_llm, _     = parse_llm_value(parsed.get("phone"))
            education_llm, _ = parse_llm_value(parsed.get("education"))
            experience_llm, _= parse_llm_value(parsed.get("experience"))

            if email_llm:
                email_llm = clean_email(email_llm)

            found_conf = sum(1 for c in [name_cert, position_cert] if c == "confident")
            found_any  = sum(1 for c in [name_cert, position_cert] if c != "absent")
            conf = 0.90 if found_conf == 2 else (0.75 if found_conf == 1 else (0.40 if found_any > 0 else 0.0))

            return name, name_cert, position, position_cert, conf, email_llm, phone_llm, education_llm, experience_llm

        except litellm.RateLimitError:
            wait = 3 * (attempt + 1)
            print(f"[LLM] Rate limit hit, waiting {wait}s...")
            await asyncio.sleep(wait)
            continue
        except litellm.AuthenticationError:
            print(f"[LLM] Invalid API key for {litellm_id}")
            break
        except Exception as e:
            print(f"[LLM ERROR] attempt={attempt} model={litellm_id} error={e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            continue

    return None, "absent", None, "absent", 0.0, None, None, None, None


# ── Sanity checks ─────────────────────────────────────────────────────────────

def sanity_check_name(name: str | None, text: str) -> tuple[str | None, str]:
    if name is None:
        return name, "absent"
    patterns = [
        r'^\d+$',
        r'(company|บริษัท|ltd|co\.,)',
        r'(university|มหาวิทยาลัย|วิทยาลัย|การศึกษา|College|University)',
        r'.{81,}',
        r'^(resume|cv|curriculum vitae)',
    ]
    for pat in patterns:
        if re.search(pat, name, re.IGNORECASE):
            print(f"[HEURISTIC] name hallucination: {name!r}")
            return None, "unsure"
    return name, "confident"


def sanity_check_position(position: str | None) -> tuple[str | None, str]:
    if position is None:
        return None, "absent"
    if len(position) > 100 or re.match(r'^\d+$', position):
        return None, "unsure"
    return position, "confident"


# ── Main entry point ──────────────────────────────────────────────────────────

async def parse_fields(text: str, config: ParseConfig) -> ExtractedFields:
    text  = clean_text(text)
    empty = None if config.empty_value == "null" else ""

    # Layer 1: Regex
    email_regex,   email_conf = extract_email(text)   if config.extract_email   else (empty, 0)
    phone_regex,   phone_conf = extract_phone(text)   if config.extract_phone   else (empty, 0)
    address_regex, _          = extract_address(text) if config.extract_address else (empty, 0)

    # Layer 2: LLM (via LiteLLM)
    name, name_cert, position, position_cert, llm_conf, email_llm, phone_llm, education_llm, experience_llm = \
        await extract_fields_llm(text, config)

    # Layer 3: Sanity check
    name,     name_cert     = sanity_check_name(name, text)
    position, position_cert = sanity_check_position(position)

    # Layer 4: Heuristic fallback
    if config.extract_name and name_cert in ("absent", "unsure"):
        h_name, h_conf = extract_name_heuristic(text)
        if h_name:
            print(f"[HEURISTIC] name fallback: {h_name!r} conf={h_conf}")
            name      = h_name
            name_cert = "confident" if h_conf >= 0.75 else "unsure"
            llm_conf  = max(llm_conf, h_conf * 0.85)

    if config.extract_position and position_cert in ("absent", "unsure"):
        h_pos, h_conf = extract_position_heuristic(text)
        if h_pos:
            print(f"[HEURISTIC] position fallback: {h_pos!r} conf={h_conf}")
            position      = h_pos
            position_cert = "confident" if h_conf >= 0.75 else "unsure"
            llm_conf      = max(llm_conf, h_conf * 0.85)

    # Merge
    def resolve(value, cert):
        if value is not None: return value
        if cert == "unsure":  return None
        return empty

    final_email   = email_regex or email_llm or empty
    final_phone   = format_phone(phone_regex or phone_llm) or empty
    final_address = address_regex or empty
    final_edu     = education_llm or empty if config.extract_education else empty
    final_exp     = experience_llm or empty if config.extract_experience else empty

    email_final_conf = email_conf if email_regex else (0.75 if email_llm else 0.0)
    phone_final_conf = phone_conf if phone_regex else (0.75 if phone_llm else 0.0)

    scores = []
    if config.extract_email:   scores.append(email_final_conf if final_email else 0.0)
    if config.extract_phone:   scores.append(phone_final_conf if final_phone else 0.0)
    if config.extract_name or config.extract_position: scores.append(llm_conf)

    confidence = round(sum(scores) / len(scores), 2) if scores else 0.0

    return ExtractedFields(
        name=resolve(name, name_cert),
        name_cert=name_cert,
        position=resolve(position, position_cert),
        position_cert=position_cert,
        phone=final_phone,
        email=final_email,
        address=final_address,
        education=final_edu,
        experience=final_exp,
        confidence=confidence,
    )
