import io
from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side
)
from openpyxl.utils import get_column_letter
from api.models import ParseJob, JobStatus

# Colors
HEADER_FILL = PatternFill("solid", fgColor="1D9E75")
WARN_FILL = PatternFill("solid", fgColor="FAC775")   # low confidence row
ALT_FILL = PatternFill("solid", fgColor="F5FAF8")    # alternating row
NULL_FONT = Font(italic=True, color="999999")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)

thin = Side(style="thin", color="E0E0E0")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

COLUMNS = [
    ("Name", "name"),
    ("Position", "position"),
    ("Phone", "phone"),
    ("Email", "email"),
    ("Confidence", "confidence"),
    ("Source File", "filename"),
    ("Parse Method", "parse_method"),
    ("Status", "status"),
]

COL_WIDTHS = [25, 28, 20, 32, 12, 40, 16, 14]


def build_excel(jobs: list[ParseJob], config=None) -> bytes:
    """
    Build Excel workbook from completed parse jobs.
    Returns raw bytes for streaming download.
    - Low confidence rows highlighted amber
    - Null/empty values shown in italic gray
    - Source filename in last tracking column
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Parsed Resumes"

    # ── Header row ──
    for col_idx, (label, _) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER
    ws.row_dimensions[1].height = 22

    # ── Data rows ──
    for row_idx, job in enumerate(jobs, start=2):
        is_low_conf = job.status == JobStatus.low_confidence
        is_alt = row_idx % 2 == 0

        result = job.result

        values = {
            "name": result.name if result else None,
            "position": result.position if result else None,
            "phone": result.phone if result else None,
            "email": result.email if result else None,
            "confidence": f"{int(result.confidence * 100)}%" if result else "—",
            "filename": job.filename,
            "parse_method": job.parse_method or "—",
            "status": job.status.value,
        }

        for col_idx, (_, key) in enumerate(COLUMNS, start=1):
            val = values.get(key)
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=False)

            is_null = val is None or val == "null" or val == ""
            if is_null:
                cell.value = "null"
                cell.font = NULL_FONT
            else:
                cell.value = val

            # Row fill
            if is_low_conf:
                cell.fill = WARN_FILL
            elif is_alt:
                cell.fill = ALT_FILL

        ws.row_dimensions[row_idx].height = 18

    # ── Column widths ──
    for col_idx, width in enumerate(COL_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # ── Freeze header ──
    ws.freeze_panes = "A2"

    # ── Auto-filter ──
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}1"

    # ── Summary sheet ──
    ws2 = wb.create_sheet(title="Summary")
    total = len(jobs)
    done = sum(1 for j in jobs if j.status == JobStatus.done)
    flagged = sum(1 for j in jobs if j.status == JobStatus.low_confidence)
    failed = sum(1 for j in jobs if j.status == JobStatus.failed)

    summary_data = [
        ("Total files", total),
        ("Parsed OK", done),
        ("Low confidence (flagged)", flagged),
        ("Failed", failed),
    ]
    for r, (label, val) in enumerate(summary_data, start=1):
        ws2.cell(row=r, column=1, value=label).font = Font(bold=True)
        ws2.cell(row=r, column=2, value=val)

    ws2.column_dimensions["A"].width = 30
    ws2.column_dimensions["B"].width = 12

    # ── Export to bytes ──
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
