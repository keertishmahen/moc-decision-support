"""
tests/structure/test_docs.py — the repository's documentation stays true.

AGENTS.md is a map, so it must stay short and every link in the knowledge base must lead
somewhere. Generated documents must match the application. See docs/references/harness-engineering.md.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AGENTS_MAX_LINES = 120

KNOWLEDGE_BASE = [
    "AGENTS.md", "ARCHITECTURE.md", "CLAUDE.md", "README.md", "docs/QUALITY.md", "docs/DEPLOYMENT_CHANGES.md",
    *[p.relative_to(ROOT).as_posix() for folder in ("design-docs", "exec-plans", "product-specs", "references", "reports")
      for p in sorted((ROOT / "docs" / folder).rglob("*.md"))],
]
REQUIRED = [
    "AGENTS.md", "ARCHITECTURE.md", "docs/design-docs/index.md", "docs/design-docs/core-beliefs.md",
    "docs/product-specs/index.md", "docs/exec-plans/README.md", "docs/exec-plans/tech-debt-tracker.md",
    "docs/references/decision-allocation-model.md", "docs/generated/api-routes.md",
    "docs/generated/graph-schema.md", "docs/QUALITY.md",
]
_LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)\)")


def test_required_documents_exist():
    missing = [p for p in REQUIRED if not (ROOT / p).is_file()]
    assert not missing, f"Missing documents: {missing}. AGENTS.md links to them; create them or update the map."


def test_agents_md_stays_a_map():
    lines = (ROOT / "AGENTS.md").read_text(encoding="utf-8").splitlines()
    assert len(lines) <= AGENTS_MAX_LINES, (
        f"AGENTS.md has {len(lines)} lines (limit {AGENTS_MAX_LINES}). It is a table of contents: move the "
        "detail into a document under docs/ and link to it."
    )


@pytest.mark.parametrize("doc", KNOWLEDGE_BASE)
def test_relative_links_resolve(doc):
    path = ROOT / doc
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.S)             # ignore code blocks
    broken = []
    for target in _LINK.findall(text):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target_path = (path.parent / target.split("#", 1)[0]).resolve()
        if not target_path.exists():
            broken.append(target)
    assert not broken, f"{doc} links to files that do not exist: {broken}. Fix the link or add the document."


def test_generated_api_document_matches_the_application():
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_docs.py"), "--check"],
                            capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, (
        "docs/generated/api-routes.md is out of date with the routes in api/. "
        "Run: python scripts/generate_docs.py --api\n" + result.stdout + result.stderr[-400:]
    )


def test_every_design_doc_is_indexed():
    index = (ROOT / "docs" / "design-docs" / "index.md").read_text(encoding="utf-8")
    unlisted = [p.name for p in (ROOT / "docs" / "design-docs").glob("*.md")
                if p.name != "index.md" and p.name not in index]
    assert not unlisted, f"Add these to docs/design-docs/index.md: {unlisted}"
