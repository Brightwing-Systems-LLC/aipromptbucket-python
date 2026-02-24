"""Codebase scanner for hardcoded prompts — pure stdlib, no Django."""

from __future__ import annotations

import ast
import re
import unicodedata
from pathlib import Path

from .types import ScanFinding

# Patterns that suggest a string is a prompt
PROMPT_KEYWORDS = [
    r"\byou are\b",
    r"\bassistant\b",
    r"\bsystem\b",
    r"\brespond\b",
    r"\banswer\b",
    r"\binstruction\b",
    r"\brole\b",
    r"\btask\b",
]

JINJA2_VAR_RE = re.compile(r"\{\{[\s]*(\w+)")
FSTRING_VAR_RE = re.compile(r"\{(\w+)\}")

# Directories that likely contain text/markdown prompts
PROMPT_DIRS = {"prompts", "templates", "system_prompts"}

# Jinja2 keywords to exclude from variable lists
_JINJA_KEYWORDS = {"if", "else", "endif", "for", "endfor", "block", "endblock", "extends", "include"}


def _slugify(value: str) -> str:
    """Pure-Python slugify (replaces django.utils.text.slugify)."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


class Scanner:
    """Scan a directory for hardcoded prompts.

    Usage:
        scanner = Scanner(min_length=100)
        findings = scanner.scan("/path/to/project")
    """

    def __init__(self, min_length: int = 100):
        self.min_length = min_length

    def scan(self, path: str | Path) -> list[ScanFinding]:
        """Scan directory recursively and return findings."""
        scan_path = Path(path).resolve()
        if not scan_path.exists():
            return []

        findings: list[ScanFinding] = []

        # Scan Python files
        for py_file in scan_path.rglob("*.py"):
            findings.extend(self._scan_python_file(py_file))

        # Scan text/markdown files in prompt-related directories
        for ext in ("*.txt", "*.md"):
            for f in scan_path.rglob(ext):
                if any(d in f.parts for d in PROMPT_DIRS):
                    findings.extend(self._scan_text_file(f))

        return findings

    def _scan_python_file(self, filepath: Path) -> list[ScanFinding]:
        findings: list[ScanFinding] = []
        try:
            source = filepath.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(filepath))
        except (SyntaxError, ValueError):
            return findings

        for node in ast.walk(tree):
            texts: list[tuple[str, int]] = []
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                texts.append((node.value, node.lineno))
            elif isinstance(node, ast.JoinedStr):
                parts: list[str] = []
                for val in node.values:
                    if isinstance(val, ast.Constant):
                        parts.append(str(val.value))
                    elif isinstance(val, ast.FormattedValue):
                        if isinstance(val.value, ast.Name):
                            parts.append(f"{{{val.value.id}}}")
                        else:
                            parts.append("{...}")
                joined = "".join(parts)
                texts.append((joined, node.lineno))

            for text, lineno in texts:
                if len(text) < self.min_length:
                    continue
                if self._looks_like_prompt(text):
                    variables = self._extract_variables(text)
                    findings.append(
                        ScanFinding(
                            file=str(filepath),
                            line=lineno,
                            text=text,
                            variables=variables,
                            detected_format=self._detect_format(text),
                        )
                    )
        return findings

    def _scan_text_file(self, filepath: Path) -> list[ScanFinding]:
        findings: list[ScanFinding] = []
        try:
            text = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return findings

        if len(text) < self.min_length:
            return findings

        if self._looks_like_prompt(text):
            variables = self._extract_variables(text)
            findings.append(
                ScanFinding(
                    file=str(filepath),
                    line=1,
                    text=text,
                    variables=variables,
                    detected_format=self._detect_format(text),
                )
            )
        return findings

    @staticmethod
    def _looks_like_prompt(text: str) -> bool:
        text_lower = text.lower()
        matches = sum(1 for p in PROMPT_KEYWORDS if re.search(p, text_lower))
        return matches >= 2

    @staticmethod
    def _extract_variables(text: str) -> list[str]:
        variables: set[str] = set()
        variables.update(JINJA2_VAR_RE.findall(text))
        variables.update(FSTRING_VAR_RE.findall(text))
        variables -= _JINJA_KEYWORDS
        return sorted(variables)

    @staticmethod
    def _detect_format(text: str) -> str:
        if "{{" in text and "}}" in text:
            if "{%" in text:
                return "jinja2"
            return "mustache"
        if "{" in text and "}" in text:
            return "fstring"
        return "jinja2"

    @staticmethod
    def generate_slug(finding: ScanFinding) -> str:
        """Generate a slug from a scan finding."""
        path = Path(finding.file)
        base = f"{path.stem}-{finding.line}"
        return _slugify(base)

    @staticmethod
    def generate_name(finding: ScanFinding) -> str:
        """Generate a human-friendly name from a scan finding."""
        path = Path(finding.file)
        return f"Imported: {path.stem}:{finding.line}"
