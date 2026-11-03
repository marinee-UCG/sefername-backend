from datetime import date

TD3_LINE_LENGTH = 44


class MRZError(Exception):
    """MRZ text is structurally unusable (wrong length, wrong type, bad characters)."""


def char_value(c: str) -> int:
    if len(c) != 1:
        raise ValueError(f"Expected a single character, got {c!r}")
    if c.isdigit():
        return int(c)
    if "A" <= c <= "Z":
        return ord(c) - 55
    if c == "<":
        return 0
    raise ValueError(f"Invalid MRZ character: {c!r}")


def compute_check_digit(data: str) -> int:
    weights = [7, 3, 1]
    total = 0
    for i, c in enumerate(data):
        total += char_value(c) * weights[i % 3]
    return total % 10


def is_check_digit_valid(data: str, check_char: str) -> bool:
    if not check_char.isdigit():
        # An empty optional field may use "<" as its check digit (counts as 0).
        return check_char == "<" and compute_check_digit(data) == 0
    return compute_check_digit(data) == int(check_char)


def clean_field(value: str) -> str | None:
    cleaned = value.replace("<", " ").strip()
    return cleaned or None


def parse_mrz_date(yymmdd: str, is_expiry: bool, today: date) -> date | None:
    if not yymmdd.isdigit():
        return None  # unknown date ("<<") or OCR noise
    yy, mm, dd = int(yymmdd[0:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
    if is_expiry:
        year = 2000 + yy
    else:
        year = 2000 + yy if 2000 + yy <= today.year else 1900 + yy
    try:
        return date(year, mm, dd)
    except ValueError:
        return None  # e.g. month 13 from a misread


def parse_names(name_field: str) -> tuple[str | None, str | None]:
    surname, _, given_names = name_field.partition("<<")
    # Given names end at the next "<<"; everything after it is filler
    # (and OCR often misreads long "<<<<" runs as "KKKK").
    given_names, _, _ = given_names.partition("<<")
    return clean_field(surname), clean_field(given_names)


def parse_td3(line1: str, line2: str, today: date | None = None) -> dict:
    today = today or date.today()
    line1, line2 = line1.strip(), line2.strip()

    for name, line in (("line 1", line1), ("line 2", line2)):
        if len(line) != TD3_LINE_LENGTH:
            raise MRZError(f"MRZ {name} must be {TD3_LINE_LENGTH} characters, got {len(line)}")
        try:
            for c in line:
                char_value(c)
        except ValueError as e:
            raise MRZError(f"MRZ {name}: {e}") from e

    if line1[0] != "P":
        raise MRZError("Not a passport MRZ: line 1 must start with 'P'")

    number, number_check = line2[0:9], line2[9]
    birth, birth_check = line2[13:19], line2[19]
    expiry, expiry_check = line2[21:27], line2[27]
    personal, personal_check = line2[28:42], line2[42]
    composite_data = line2[0:10] + line2[13:20] + line2[21:43]
    composite_check = line2[43]

    checks = {
        "document_number": is_check_digit_valid(number, number_check),
        "birth_date": is_check_digit_valid(birth, birth_check),
        "expiry_date": is_check_digit_valid(expiry, expiry_check),
        "personal_number": is_check_digit_valid(personal, personal_check),
        "composite": is_check_digit_valid(composite_data, composite_check),
    }

    surname, given_names = parse_names(line1[5:44])
    birth_date = parse_mrz_date(birth, is_expiry=False, today=today)
    expiry_date = parse_mrz_date(expiry, is_expiry=True, today=today)

    return {
        "document_type": clean_field(line1[0:2]),
        "issuing_country": clean_field(line1[2:5]),
        "surname": surname,
        "given_names": given_names,
        "document_number": clean_field(number),
        "nationality": clean_field(line2[10:13]),
        "birth_date": birth_date.isoformat() if birth_date else None,
        "sex": clean_field(line2[20]),
        "expiry_date": expiry_date.isoformat() if expiry_date else None,
        "personal_number": clean_field(personal),
        "checks": checks,
        "all_checks_passed": all(checks.values()),
    }
