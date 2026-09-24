"""Deterministic A0-to-rendered-text locators for anchors and host passages.

The normalization spec frozen at L2 for resolving instrument text in A1-A4:

* ``fold`` compares text case-insensitively after folding typographic quotes,
  dashes, and ellipses; collapsing hyphen runs; and deleting whitespace plus the
  inline-markup characters ``*``, `````, ``_``, and ``\\``. Deleting whitespace
  is required because A3 inserts a separator at every inline element boundary
  (``<code>x</code>.`` extracts as ``x .``). Every folded character maps back to
  original coordinates.
* ``project_mdx`` removes MDX syntax that never renders as text (frontmatter,
  imports, JSX comments and tags, link targets, heading/list/quote/table markup,
  code-fence lines), renders Starlight aside markers as their titles, and
  renders headings with Starlight's ``Section titled "..."`` anchor label
  (verified in the pinned Starlight 0.41.0 source and English translations).
* A host passage is located in an artifact by its **start locator** and **end
  locator**: the shortest folded prefix of its first prose block and suffix of
  its last prose block (at least ``MIN_LOCATOR`` characters) that occur exactly
  once in the projected A0 page of that arm. Blocks end at code fences and at
  lines containing capitalized MDX components, where rendering can insert text
  (code-frame titles, tab labels, badges) that A0 does not contain. Resolution requires exactly one match; there is no fuzzy
  or semantic fallback.
"""

from __future__ import annotations

import html
import re

MIN_LOCATOR = 12
DROPPED = frozenset("*`_\\")
FOLDS = {
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "–": "-",
    "—": "-",
    "−": "-",
    " ": " ",
}
ASIDE_TITLES = {"note": "Note", "tip": "Tip", "caution": "Caution", "danger": "Danger"}
# Characters that must not begin or end a host, because they signal markup
# whose rendering is not text-preserving at a locator boundary.
# Aside markers are allowed: they render as their (default) title text.
UNSAFE_EDGE = re.compile(r"^\s*(```|~~~|<|\||import |export |\{/\*)")


def fold(text: str) -> tuple[str, list[int]]:
    """Return folded text and, per folded character, its original offset."""
    folded: list[str] = []
    positions: list[int] = []
    for index, original in enumerate(text):
        for char in "..." if original == "\u2026" else FOLDS.get(original, original):
            if char.isspace() or char in DROPPED:
                continue
            if char == "-" and folded and folded[-1] == "-":
                continue
            for lowered in char.lower():
                folded.append(lowered)
                positions.append(index)
    return "".join(folded), positions


def project_mdx(text: str) -> str:
    """Project MDX source to the text a reader would see, before folding.

    Code content (fenced blocks and inline spans) renders literally, so it is
    set aside before markup removal and restored afterwards.
    """
    protected: list[str] = []

    def protect(content: str) -> str:
        protected.append(content)
        return f"\x00{len(protected) - 1}\x00"

    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.DOTALL)
    text = re.sub(
        r"^[ \t]*(```|~~~)[^\n]*\n(.*?)^[ \t]*\1[^\n]*$",
        lambda match: protect(match.group(2)),
        text,
        flags=re.DOTALL | re.MULTILINE,
    )
    text = re.sub(r"`([^`\n]+)`", lambda match: protect(match.group(1)), text)
    text = re.sub(r"^(import|export)\s[^\n]*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\{/\*.*?\*/\}", "", text, flags=re.DOTALL)
    text = re.sub(r"^\s*(```|~~~)[^\n]*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"<(https?://[^>\s]+)>", r"\1", text)
    text = re.sub(r"</?[A-Za-z][^<>]*?/?>", " ", text, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", text)

    def aside(match: re.Match[str]) -> str:
        if match.group(3) is not None:
            return match.group(3)
        return ASIDE_TITLES.get(match.group(1) or "", "")

    text = re.sub(
        r"^\s*:::(\w+)?(\[([^\]]*)\])?[^\n]*$", aside, text, flags=re.MULTILINE
    )
    # Starlight 0.41.0 rehype-heading-links appends an sr-only anchor label.
    text = re.sub(
        r"^\s*#{1,6}\s+(.*?)\s*#*\s*$",
        lambda match: f'{match.group(1)} Section titled "{match.group(1)}"',
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\|?\s*:?-{3,}[-|:\s]*$", "", text, flags=re.MULTILINE)
    text = text.replace("|", " ")
    text = html.unescape(text)
    return re.sub(r"\x00(\d+)\x00", lambda match: protected[int(match.group(1))], text)


def find_all(needle: str, haystack: str) -> list[tuple[int, int]]:
    """All matches of folded ``needle`` in ``haystack``, in original coordinates."""
    target, _ = fold(needle)
    if not target:
        return []
    folded, positions = fold(haystack)
    spans = []
    start = folded.find(target)
    while start >= 0:
        spans.append((positions[start], positions[start + len(target) - 1] + 1))
        start = folded.find(target, start + 1)
    return spans


# Lines after which rendering may insert text absent from A0: code fences
# (frame labels) and capitalized MDX components (tab labels, badges).
BLOCK_BOUNDARY = re.compile(r"^\s*(```|~~~)|</?[A-Z][A-Za-z]*[\s/>]")


def _blocks(host: str) -> list[str]:
    blocks: list[list[str]] = [[]]
    for line in host.splitlines():
        if BLOCK_BOUNDARY.search(line):
            blocks.append([])
        else:
            blocks[-1].append(line)
    return [fold(project_mdx("\n".join(block)))[0] for block in blocks]


def locators(host: str, page: str) -> tuple[str, str]:
    """Shortest unique folded prefix/suffix of the host's edge blocks in the page."""
    folded_host, _ = fold(project_mdx(host))
    folded_page, _ = fold(project_mdx(page))
    blocks = [block for block in _blocks(host) if block]
    if not blocks or len(folded_host) < MIN_LOCATOR:
        raise ValueError("Host passage is too short to locate")
    if folded_page.count(folded_host) != 1:
        raise ValueError(
            f"Projected host passage occurs {folded_page.count(folded_host)} times in its A0 page (need 1)"
        )

    def shortest(block: str, suffix: bool) -> str:
        for length in range(MIN_LOCATOR, len(block) + 1):
            candidate = block[-length:] if suffix else block[:length]
            if folded_page.count(candidate) == 1:
                return candidate
        edge = "last" if suffix else "first"
        raise ValueError(f"The host's {edge} prose block has no unique locator")

    return shortest(blocks[0], False), shortest(blocks[-1], True)


def check_edges(host: str) -> None:
    """Hosts must begin and end in rendered prose, not markup."""
    lines = [line for line in host.strip().splitlines() if line.strip()]
    if not lines:
        raise ValueError("Empty host passage")
    for label, line in (("begins", lines[0]), ("ends", lines[-1])):
        if UNSAFE_EDGE.match(line) or line.strip() in {"---", "```"}:
            raise ValueError(f"Host passage {label} in markup: {line.strip()[:40]!r}")


def resolve_host(host: str, page_source: str, rendered: str) -> tuple[int, int]:
    """Resolve an A0 host passage in rendered text via its unique locators."""
    start_locator, end_locator = locators(host, page_source)
    starts = find_all(start_locator, rendered)
    ends = find_all(end_locator, rendered)
    if len(starts) != 1 or len(ends) != 1:
        raise ValueError(
            f"Host locators must match exactly once (start={len(starts)}, end={len(ends)})"
        )
    if ends[0][1] <= starts[0][0]:
        raise ValueError("Host end locator precedes its start")
    return starts[0][0], ends[0][1]


def resolve_anchor(
    anchor: str, rendered: str, within: tuple[int, int]
) -> tuple[int, int]:
    """Resolve an anchor exactly once inside a resolved host span."""
    spans = [
        span
        for span in find_all(anchor, rendered)
        if within[0] <= span[0] and span[1] <= within[1]
    ]
    if len(spans) != 1:
        raise ValueError(
            f"Anchor must resolve exactly once in its host (found {len(spans)})"
        )
    return spans[0]
