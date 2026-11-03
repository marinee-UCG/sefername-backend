

def char_value(c:str) -> int:
    if len(c) != 1:
        raise ValueError(f"Expected a single character,got {c!r}")
    if c.isdigit():
        return int(c)
    if "A"<=c<="Z":
        return ord(c)-55
    if c== "<":
        return 0
    raise ValueError(f"Invalid MRZ character: {c!r}")


def compute_check_digit(c:str) -> int:
    weights=[7,3,1]
    total = 0
    for i,c in enumerate(c):
        total +=char_value(c)*weights[i%3]
    return total % 10 
  