"""Locate bundled assets and validate embedded fonts."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
BUNDLE = (Path(sys._MEIPASS) / "bookstudio") if getattr(sys, "frozen", False) else ROOT

FONT_FAMILIES = {
    "Vazirmatn": {
        100: "Vazirmatn-Thin.ttf",
        200: "Vazirmatn-ExtraLight.ttf",
        300: "Vazirmatn-Light.ttf",
        400: "Vazirmatn-Regular.ttf",
        500: "Vazirmatn-Medium.ttf",
        600: "Vazirmatn-SemiBold.ttf",
        700: "Vazirmatn-Bold.ttf",
        800: "Vazirmatn-ExtraBold.ttf",
        900: "Vazirmatn-Black.ttf",
    },
    "IRNazanin": {
        400: "IRNazanin.ttf",
        700: "IRNazaninBold.ttf",
        "italic": "IRNazaninIranic.ttf",
    },
}

WEIGHT_LABELS = {
    100: "Thin",
    200: "ExtraLight",
    300: "Light",
    400: "Regular",
    500: "Medium",
    600: "SemiBold",
    700: "Bold",
    800: "ExtraBold",
    900: "Black",
}

EMBEDDED_FONT_FILES = {fname for family in FONT_FAMILIES.values() for fname in family.values()}


def resource_path(relative: str | Path) -> Path:
    return BUNDLE / relative


def _font_file(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"فونت {path.name} موجود نیست؛ آن را در پوشه fonts قرار دهید.")
    if path.open("rb").read(4) not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
        raise ValueError(f"فایل {path.name} یک فونت معتبر TTF/OTF نیست.")
    return path


def available_weights(family: str) -> list[int]:
    family_map = FONT_FAMILIES.get(family) or FONT_FAMILIES["Vazirmatn"]
    return sorted(k for k in family_map.keys() if isinstance(k, int))


def normalize_weight(family: str, weight: int | str | bool = 400, italic: bool = False) -> int | str:
    if isinstance(weight, bool):
        weight = 700 if weight else 400
    try:
        weight = int(weight)
    except Exception:
        weight = 400
    weights = available_weights(family)
    if italic and "italic" in FONT_FAMILIES.get(family, {}):
        return "italic"
    if weight in weights:
        return weight
    # nearest available weight
    return min(weights, key=lambda w: abs(w - weight))


def font_path(weight: int | str | bool = 400, family: str = "Vazirmatn", italic: bool = False) -> Path:
    family = family if family in FONT_FAMILIES else "Vazirmatn"
    key = normalize_weight(family, weight, italic=italic)
    fname = FONT_FAMILIES[family][key]
    return _font_file(resource_path("fonts") / fname)


def fonts_available() -> bool:
    try:
        for family in FONT_FAMILIES:
            # validate only core usable files
            _ = font_path(400, family=family)
        return True
    except (ValueError, FileNotFoundError):
        return False
