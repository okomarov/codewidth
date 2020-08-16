def remove_prefix(s, prefix):
    return s[len(prefix):] if s.startswith(prefix) else s


def divide_or_zero(num, den):
    return num/den if den else 0
