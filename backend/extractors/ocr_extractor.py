import os
import tempfile
from PIL import Image
import pytesseract 
from pdf2image import convert_from_path
import uuid

# Tesseract path from env (Windows)
tesseract_path = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = tesseract_path

# EasyOCR — lazy init (first load downloads models ~500MB, cached after)
_readers: dict[str, object] = {}

def _get_reader(languages: list[str]):
    lang_map = {"eng": "en", "tha": "th"}
    easy_langs = sorted({lang_map.get(l, "en") for l in languages})
    cache_key = ",".join(easy_langs)

    if cache_key not in _readers:
        try:
            import easyocr
            _readers[cache_key] = easyocr.Reader(easy_langs, gpu=False, verbose=False)
        except Exception:
            _readers[cache_key] = None

    return _readers[cache_key]


def ocr_image_file(file_path: str, languages: list[str] = ["eng", "tha"]) -> tuple[str, float]:
    """
    OCR a single image file (jpg, png).
    Returns (text, confidence 0-1).
    Tries EasyOCR first, falls back to Tesseract.
    """
    return _ocr_with_fallback(file_path, languages)


def ocr_scanned_pdf(file_path: str, languages: list[str] = ["eng", "tha"]) -> tuple[str, float]:
    """
    Convert scanned PDF pages to images then OCR each.
    Returns (combined_text, avg_confidence).
    """
    try:
        images = convert_from_path(file_path, dpi=200)
    except Exception:
        return "", 0.0

    all_texts = []
    all_confs = []

    job_id = uuid.uuid4().hex

    for i, img in enumerate(images):
        tmp_path = os.path.join(tempfile.gettempdir(), f"_ocr_{job_id}_page_{i}.png")
        img.save(tmp_path, "PNG")
        try:
            text, conf = _ocr_with_fallback(tmp_path, languages)
            all_texts.append(text)
            all_confs.append(conf)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    combined = "\n".join(all_texts).strip()
    avg_conf = sum(all_confs) / len(all_confs) if all_confs else 0.0
    return combined, round(avg_conf, 3)


def _ocr_with_fallback(image_path: str, languages: list[str]) -> tuple[str, float]:
    """
    EasyOCR → Tesseract fallback.
    """
    # --- EasyOCR ---
    reader = _get_reader(languages)
    if reader:
        try:
            results = reader.readtext(image_path, detail=1, paragraph=False)
            lines = []
            confs = []
            for (_, text, conf) in results:
                if text.strip():
                    lines.append(text.strip())
                    confs.append(float(conf))
            if lines:
                return "\n".join(lines), round(sum(confs) / len(confs), 3)
        except Exception:
            pass

    # --- Tesseract fallback ---
    try:
        lang_str = "+".join(languages)  # "eng+tha"
        img = Image.open(image_path)
        data = pytesseract.image_to_data(
            img, lang=lang_str, output_type=pytesseract.Output.DICT
        )
        words = [
            w for w, c in zip(data["text"], data["conf"])
            if w.strip() and int(c) > 0
        ]
        confs = [int(c) for c in data["conf"] if int(c) > 0]
        text = " ".join(words)
        conf = round(sum(confs) / len(confs) / 100.0, 3) if confs else 0.0
        return text, conf
    except Exception:
        return "", 0.0
