"""
tests/structure/test_frontend.py — frontend rules that keep both themes and the icon set clean.

1. No emoji or symbol characters used as icons. Icons come from lucide-react.
2. No hard-coded colours in components. Colours are tokens in frontend/src/index.css,
   used as Tailwind classes or read with usePalette(); that is what makes light and dark
   mode both work everywhere.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"

# Pictographs, dingbats (incl. check marks and warning signs), geometric shapes used as
# bullets, arrows, misc technical symbols (refresh), emoji modifiers and variation selectors.
_SYMBOLS = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿⬀-⯿←-⇿⌀-⏿"
    "■-◿⤀-⥿︎️‍]"
)
_HEX = re.compile(r"(?<!&)#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")   # not HTML entities (&#39;)
_RGBA = re.compile(r"\brgba?\(")


def _sources(*suffixes):
    return sorted(p for p in SRC.rglob("*") if p.suffix in suffixes)


def test_no_emoji_or_symbol_icons():
    found = []
    for path in _sources(".ts", ".tsx"):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            chars = sorted(set(_SYMBOLS.findall(line)))
            if chars:
                found.append(f"{path.relative_to(ROOT).as_posix()}:{n} uses {' '.join(chars)}")
    assert not found, (
        "Emoji or symbol characters found. Use an icon from lucide-react instead "
        "(e.g. TriangleAlert, CircleCheck, ChevronRight, ArrowRight); in comments write '->'.\n" + "\n".join(found)
    )


def test_no_hard_coded_colours_in_components():
    found = []
    for path in _sources(".ts", ".tsx"):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _HEX.search(line) or _RGBA.search(line):
                found.append(f"{path.relative_to(ROOT).as_posix()}:{n}: {line.strip()[:100]}")
    assert not found, (
        "Hard-coded colours found. Add or reuse a token in frontend/src/index.css (dark value in "
        "@theme static, light value under :root[data-theme='light']) and use it as a class "
        "(text-accent, bg-surface, border-ok/30) or via usePalette().\n" + "\n".join(found)
    )


def test_every_dark_token_has_a_light_value():
    css = (SRC / "index.css").read_text(encoding="utf-8")
    dark_block = css[css.index("@theme static"):]
    dark_block = dark_block[:dark_block.index("}")]
    light_block = css[css.index(":root[data-theme='light'] {"):]
    light_block = light_block[:light_block.index("}")]
    token = re.compile(r"--color-([a-z0-9-]+)\s*:")
    dark = set(token.findall(dark_block))
    light = set(token.findall(light_block))
    missing = sorted(dark - light - {"on-accent"})            # on-accent is white in both themes
    assert not missing, f"Tokens without a light-theme value in index.css: {missing}"


def test_palette_reads_every_token():
    css = (SRC / "index.css").read_text(encoding="utf-8")
    dark_block = css[css.index("@theme static"):]
    dark = set(re.findall(r"--color-([a-z0-9-]+)\s*:", dark_block[:dark_block.index("}")]))
    palette = (SRC / "theme" / "palette.ts").read_text(encoding="utf-8")
    listed = set(re.findall(r"'([a-z0-9-]+)'", palette[palette.index("TOKENS"):palette.index("] as const")]))
    assert dark == listed, f"palette.ts TOKENS and index.css tokens differ: {sorted(dark ^ listed)}"
