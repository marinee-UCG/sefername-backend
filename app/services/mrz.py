def char_value(c: str) -> int:
    if c.isdigit():
        return int(c)
    if "A" <= c <= "Z":
        return ord(c) - 55
    if c == "<":
        return 0
    raise ValueError(f"Invalid MRZ character: {c!r}")
