def gb_to_gib(gb: int) -> int:
    if not gb:
        return 0
    return round(gb * (1e9 / (1 << 30)))


def gib_to_gb(gib: int = 0) -> int:
    gb = gib * 1.073741824
    return round(gb)


def gb_to_bytes(gb: int) -> int:
    if not gb:
        return 0
    return round(gb * 1e9)


def mib_to_bytes(mib: int) -> int:
    if not mib:
        return 0
    return round(mib << 20)


def gib_to_bytes(gib: int) -> int:
    if not gib:
        return 0
    return round(gib << 30)


def tib_to_bytes(tib: int) -> int:
    if not tib:
        return 0
    return round(tib << 40)


def bytes_to_gib(bytes: int) -> int:
    if not bytes:
        return 0
    return round(bytes / (1 << 30))


def bytes_to_gb(bytes: int = 0) -> int:
    gb = round(bytes * 1e-9)
    return gb


def str_gb_to_mb(gb_str: str) -> int:
    """
    Volume size in GB passed as string converted to MB (int)
    eg: 8G -> 8 -> 8 * 1024 = 8096
    """
    return int(gb_str.strip()[:-1]) * 1024
