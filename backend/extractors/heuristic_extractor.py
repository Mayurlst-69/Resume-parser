import re

# ── Thai/English name patterns ────────────────────────────────────────────────

# Thai name prefixes
THAI_PREFIX = re.compile(
    r'^(นาย|นาง|นางสาว|ด\.ร\.|ดร\.|Mr\.|Mrs\.|Ms\.|Miss)\s*', re.IGNORECASE
)

# Lines that are NOT names (skip these)
NOT_NAME_PATTERNS = [
    re.compile(r'@'),                          # email
    re.compile(r'\d{5,}'),                     # long numbers (phone/zip)
    re.compile(r'(resume|cv|curriculum)', re.I),
    re.compile(r'(address|ที่อยู่|อีเมล|email|tel|โทร)', re.I),
    re.compile(r'(บริษัท|company|university|มหาวิทยาลัย)', re.I),
    re.compile(r'^[\d\W]+$'),                  # pure numbers/symbols
    re.compile(r'(จังหวัด|ถนน|ตำบล|อำเภอ)'), # address words
]

# Thai position keywords
POSITION_KEYWORDS = re.compile(
    r'(ตำแหน่ง|สมัครตำแหน่ง|position|applied for|job title|'
    r'ประสบการณ์การทำงาน|current position|desired position)',
    re.IGNORECASE
)

# Common job title words (Thai + English)
JOB_TITLE_WORDS = re.compile(
    r'(manager|executive|officer|director|supervisor|engineer|analyst|'
    r'consultant|coordinator|specialist|assistant|senior|junior|head|'
    r'ผู้จัดการ|เจ้าหน้าที่|ผู้อำนวยการ|วิศวกร|นักวิเคราะห์|ที่ปรึกษา|'
    r'ผู้ช่วย|หัวหน้า|พนักงาน|นักการตลาด|ฝ่าย)',
    re.IGNORECASE
)


def is_likely_name(line: str) -> bool:
    """Check if a line looks like a person's name."""
    line = line.strip()
    if not line or len(line) < 2 or len(line) > 80:
        return False
    for pattern in NOT_NAME_PATTERNS:
        if pattern.search(line):
            return False
    # Must contain at least one letter
    if not re.search(r'[a-zA-Zก-๙]', line):
        return False
    # Reject lines that are ALL numbers or symbols
    if re.match(r'^[\d\s\-\(\)\+\.]+$', line):
        return False
    return True


def extract_name_heuristic(text: str) -> tuple[str | None, float]:
    """
    Try to extract candidate name from text using rules.
    Returns (name, confidence).
    confidence 0.70 = heuristic guess, 0.80 = found with Thai prefix
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Pass 1: look for Thai prefix (นาย/นาง/นางสาว) in first 10 lines
    for line in lines[:10]:
        if THAI_PREFIX.match(line):
            name = line.strip()
            if len(name) > 3 and is_likely_name(name):
                return name, 0.80

    # Pass 2: first non-junk line in first 5 lines
    for line in lines[:5]:
        if is_likely_name(line):
            # Extra check: not a job title word
            if not JOB_TITLE_WORDS.search(line):
                return line.strip(), 0.65

    return None, 0.0


def extract_position_heuristic(text: str) -> tuple[str | None, float]:
    """
    Try to extract position from text using keyword scanning.
    Returns (position, confidence).
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Pass 1: look for label like "ตำแหน่ง: xxx" or "Position: xxx"
    for line in lines[:30]:
        match = re.match(
            r'(?:ตำแหน่ง|สมัครตำแหน่ง|position|สมัครงานตำแหน่ง|ตำแหน่งงาน|job title|applied for)\s*[:\-]?\s*(.+)',
            line, re.IGNORECASE
        )
        if match:
            pos = match.group(1).strip()
            if 3 < len(pos) < 80:
                return pos, 0.78

    # Pass 2: find line that contains job title keywords
    for line in lines[:20]:
        if JOB_TITLE_WORDS.search(line):
            # Make sure it's not a company name line
            if not re.search(r'(บริษัท|co\.,?ltd|company|corp)', line, re.I):
                if len(line) < 80:
                    return line.strip(), 0.60

    return None, 0.0