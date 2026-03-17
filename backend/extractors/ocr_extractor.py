import os
import sys
from pathlib import Path
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

# Set tesseract path from env (Windows path)
tesseract_path = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = tesseract_path

# PaddleOCR — lazy init to avoid slow startup on every import
_paddle_ocr = None

def _get_paddle():
    global _paddle_ocr
    if _paddle_ocr is None:
        try:
            from paddleocr import PaddleOCR
            # lang='en' handles both English layout; Thai via post-process
            # For full Thai support use lang='chinese_cht' or multilang build
            _paddle_ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        except Exception:
            _paddle_ocr = None
    return _paddle_ocr


def ocr_image_file(file_path: str, languages: list[str] = ["eng", "tha"]) -> tuple[str, float]:
    """
    OCR a single image file (jpg, png).
    Returns (text, confidence_score 0-1).
    Tries PaddleOCR first, falls back to Tesseract.
    """
    return _ocr_with_fallback(file_path, languages)


def ocr_scanned_pdf(file_path: str, languages: list[str] = ["eng", "tha"]) -> tuple[str, float]:
    """
    Convert scanned PDF pages to images, then OCR each page.
    Returns (combined_text, avg_confidence).
    """
    try:
        # poppler must be on PATH or provide poppler_path
        images = convert_from_path(file_path, dpi=200)
    except Exception as e:
        return "", 0.0

    all_texts = []
    all_confs = []

    for i, img in enumerate(images):
        # Save temp image
        tmp_path = f"_ocr_tmp_page_{i}.png"
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
    return combined, avg_conf


def _ocr_with_fallback(image_path: str, languages: list[str]) -> tuple[str, float]:
    """
    Try PaddleOCR → fallback to Tesseract.
    """
    # --- PaddleOCR attempt ---
    paddle = _get_paddle()
    if paddle:
        try:
            result = paddle.ocr(image_path, cls=True)
            lines = []
            confs = []
            if result and result[0]:
                for line in result[0]:
                    text_info = line[1]
                    lines.append(text_info[0])
                    confs.append(float(text_info[1]))
            if lines:
                text = "\n".join(lines)
                conf = sum(confs) / len(confs) if confs else 0.0
                return text, conf
        except Exception:
            pass

    # --- Tesseract fallback ---
    try:
        lang_str = "+".join(languages)  # e.g. "eng+tha"
        img = Image.open(image_path)
        data = pytesseract.image_to_data(img, lang=lang_str, output_type=pytesseract.Output.DICT)
        words = [w for w, c in zip(data["text"], data["conf"]) if w.strip() and int(c) > 0]
        confs = [int(c) for c in data["conf"] if int(c) > 0]
        text = " ".join(words)
        conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
        return text, conf
    except Exception as e:
        return "", 0.0
