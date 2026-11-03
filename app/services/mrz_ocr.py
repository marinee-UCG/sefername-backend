from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, ImageOps

from app.services.mrz import TD3_LINE_LENGTH, MRZError, parse_td3

PDF_RENDER_DPI = 300
MIN_IMAGE_WIDTH = 1500
BOTTOM_CROP_RATIO = 0.35
BINARY_THRESHOLD = 140
MRZ_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
TESSERACT_CONFIG = f"--psm 6 -c tessedit_char_whitelist={MRZ_ALPHABET}"

# Typical OCR confusions, fixed only where the MRZ layout says the position
# must be a letter (names, country codes, sex) or a digit (dates, check digits).
TO_LETTER = str.maketrans({"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B"})
TO_DIGIT = str.maketrans({"O": "0", "D": "0", "Q": "0", "I": "1", "L": "1",
                          "Z": "2", "S": "5", "B": "8", "G": "6"})
LINE2_LETTER_SLICES = [slice(10, 13), slice(20, 21)]                  # nationality, sex
LINE2_DIGIT_SLICES = [slice(9, 10), slice(13, 20), slice(21, 28), slice(43, 44)]


class MRZNotFoundError(MRZError):
    """No readable passport MRZ was found in the document."""


def load_image(path: str) -> Image.Image:
    if Path(path).suffix.lower() == ".pdf":
        with pymupdf.open(path) as doc:
            if doc.page_count == 0:
                raise MRZNotFoundError("PDF has no pages")
            pixmap = doc[0].get_pixmap(dpi=PDF_RENDER_DPI)
            return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    with Image.open(path) as img:
        # Phone photos store rotation in EXIF; apply it so the text is upright.
        return ImageOps.exif_transpose(img).convert("RGB")


def to_gray(img: Image.Image) -> Image.Image:
    gray = ImageOps.grayscale(img)
    if gray.width < MIN_IMAGE_WIDTH:
        scale = MIN_IMAGE_WIDTH / gray.width
        gray = gray.resize((MIN_IMAGE_WIDTH, round(gray.height * scale)), Image.Resampling.LANCZOS)
    return ImageOps.autocontrast(gray)


def preprocess_variants(img: Image.Image):
    gray = to_gray(img)
    yield gray
    yield gray.resize((gray.width * 2, gray.height * 2), Image.Resampling.LANCZOS).point(
        lambda p: 255 if p > BINARY_THRESHOLD else 0
    )


def candidate_regions(img: Image.Image):
    for upright in (img, img.rotate(180)):     # second pass: upside-down scan
        yield upright.crop((0, round(upright.height * (1 - BOTTOM_CROP_RATIO)),
                            upright.width, upright.height))   # passport page: MRZ at bottom
        yield upright                                         # A4 scan: passport anywhere


def fix_positions(line: str, slices: list[slice], table: dict) -> str:
    chars = list(line)
    for s in slices:
        chars[s] = list(line[s].translate(table))
    return "".join(chars)


def find_td3_lines(text: str) -> tuple[str, str] | None:
    lines = [line.replace(" ", "") for line in text.splitlines()]
    lines = [line for line in lines if len(line) >= 30]
    for first, second in zip(lines, lines[1:]):
        if not first.startswith("P"):
            continue
        # Trailing "<" fillers on line 1 are often dropped by OCR; restore them.
        if len(first) < TD3_LINE_LENGTH:
            first = first.ljust(TD3_LINE_LENGTH, "<")
        if len(first) == TD3_LINE_LENGTH and len(second) == TD3_LINE_LENGTH:
            first = first.translate(TO_LETTER)
            second = fix_positions(second, LINE2_LETTER_SLICES, TO_LETTER)
            second = fix_positions(second, LINE2_DIGIT_SLICES, TO_DIGIT)
            return first, second
    return None


def extract_passport_data(path: str) -> dict:
    """Read the passport MRZ from a PDF/JPG/PNG and return parsed fields.

    Returns the first result whose check digits all pass; if none passes,
    returns the first readable result (checks show what is suspicious).
    """
    img = load_image(path)
    fallback = None
    for region in candidate_regions(img):
        for variant in preprocess_variants(region):
            text = pytesseract.image_to_string(variant, config=TESSERACT_CONFIG)
            lines = find_td3_lines(text)
            if lines is None:
                continue
            try:
                result = parse_td3(*lines)
            except MRZError:
                continue
            if result["all_checks_passed"]:
                return result
            fallback = fallback or result
    if fallback is not None:
        return fallback
    raise MRZNotFoundError("Could not find a passport MRZ in the document")
