from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, ImageOps

from app.services.mrz import TD3_LINE_LENGTH, MRZError, parse_td3

PDF_RENDER_DPI = 300
PDF_MAX_WIDTH = 3000   # pixels; some PDFs have huge pages, cap them to keep OCR fast
MIN_IMAGE_WIDTH = 1500
BOTTOM_CROP_RATIO = 0.35
BINARY_THRESHOLD = 140
MAX_LONG_EDGE = 2400   # pixels; phone photos are too large for Tesseract to read well
MRZ_MARGIN = 15        # pixels kept around the MRZ so edge characters are not cut

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
            page = doc[0]
            zoom = min(PDF_RENDER_DPI / 72, PDF_MAX_WIDTH / page.rect.width)
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
            return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    with Image.open(path) as img:
        # Phone photos store rotation in EXIF; apply it so the text is upright.
        return ImageOps.exif_transpose(img).convert("RGB")
def shrink(gray:Image.Image) -> Image.Image:
    scale=MAX_LONG_EDGE /max(gray.size)
    if scale >= 1:
        return gray
    new_size= (round(gray.width*scale),round(gray.height*scale))
    return gray.resize(new_size,Image.Resampling.LANCZOS)


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

def mrz_region(img: Image.Image) -> Image.Image | None:
    """Find the MRZ with a free page read and cut it out; None when no MRZ-like text is seen."""
    small = shrink(img)
    data = pytesseract.image_to_data(small, output_type=pytesseract.Output.DICT)
    words = [i for i, word in enumerate(data["text"]) if "<<" in word]
    if not words:
        return None
    return small.crop((
        max(0, min(data["left"][i] for i in words) - MRZ_MARGIN),
        max(0, min(data["top"][i] for i in words) - MRZ_MARGIN),
        max(data["left"][i] + data["width"][i] for i in words) + MRZ_MARGIN,
        max(data["top"][i] + data["height"][i] for i in words) + MRZ_MARGIN,
    ))

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
        first = first[:TD3_LINE_LENGTH]   # OCR sometimes adds extra fillers at the end
        if len(first) < TD3_LINE_LENGTH:
            first = first.ljust(TD3_LINE_LENGTH, "<")
        if len(first) == TD3_LINE_LENGTH and len(second) == TD3_LINE_LENGTH:
            first = first.translate(TO_LETTER)
            second = fix_positions(second, LINE2_LETTER_SLICES, TO_LETTER)
            second = fix_positions(second, LINE2_DIGIT_SLICES, TO_DIGIT)
            return first, second
    return None

def reading_candidates(img: Image.Image):
    region = mrz_region(img)
    if region is not None:
        yield region
    for region in candidate_regions(img):
        yield from preprocess_variants(region)


def extract_passport_data(path: str) -> dict:
    """Read the passport MRZ from a PDF/JPG/PNG and return parsed fields.

    Returns the first result whose check digits all pass; if none passes,
    returns the first readable result (checks show what is suspicious).
    """
    img = load_image(path)
    fallback = None
    for candidate in reading_candidates(img):
        text = pytesseract.image_to_string(candidate, config=TESSERACT_CONFIG)
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
