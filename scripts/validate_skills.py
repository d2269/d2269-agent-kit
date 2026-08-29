#!/usr/bin/env python3
"""Validate canonical Agent Skills in this repository.

Stdlib only. Exit non-zero on any validation failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
YAML_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
MAX_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1024
MAX_SKILL_LINES = 500
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
# Letters in scripts that should not appear in public kit English.
NON_LATIN_RE = re.compile(
    r"[\u0400-\u04FF\u0500-\u052F\u0600-\u06FF\u3040-\u30FF\u3400-\u4DBF"
    r"\u4E00-\u9FFF\uAC00-\uD7AF]"
)

REQUIRED_FRONTMATTER = ("name", "description")


class FrontmatterError(ValueError):
    pass


def repo_root_from(start: Path | None = None) -> Path:
    here = (start or Path(__file__)).resolve()
    if here.is_file():
        here = here.parent
    for candidate in [here, *here.parents]:
        if (candidate / "skills").is_dir() and (candidate / "LICENSE").is_file():
            return candidate
    raise SystemExit("Could not locate repository root (expected skills/ and LICENSE).")


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        raise FrontmatterError("SKILL.md must start with YAML frontmatter delimited by ---")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("SKILL.md must start with a --- line")
    closing = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing = index
            break
    if closing is None:
        raise FrontmatterError("YAML frontmatter is not closed with ---")
    yaml_text = "".join(lines[1:closing])
    body = "".join(lines[closing + 1 :])
    return yaml_text, body


def _parse_scalar(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise FrontmatterError("Scalar values must not be empty")
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise FrontmatterError(f"Invalid double-quoted scalar: {value!r}") from exc
        if not isinstance(parsed, str):
            raise FrontmatterError(f"Expected a string scalar, got: {value!r}")
        return parsed
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise FrontmatterError(f"Invalid single-quoted scalar: {value!r}")
        inner = value[1:-1]
        if "'" in inner.replace("''", ""):
            raise FrontmatterError(f"Invalid single-quoted scalar: {value!r}")
        return inner.replace("''", "'")
    if value[0] in "-?:,[]{}#&*!|>'\"%@`":
        raise FrontmatterError(
            f"Unsupported or ambiguous plain scalar {value!r}; quote string values"
        )
    if not re.match(r"^[A-Za-z]", value):
        raise FrontmatterError(f"Plain string scalar must start with an ASCII letter: {value!r}")
    if ": " in value or " #" in value:
        raise FrontmatterError(
            f"Unsupported or ambiguous plain scalar {value!r}; quote string values"
        )
    return value


def parse_simple_yaml(yaml_text: str) -> dict[str, Any]:
    """Parse the strict, string-only YAML subset used by kit frontmatter."""
    result: dict[str, Any] = {}
    lines = yaml_text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.strip().startswith("#"):
            index += 1
            continue
        if "\t" in line:
            raise FrontmatterError(f"Tabs are not supported in frontmatter: {line!r}")
        if line.startswith(" "):
            raise FrontmatterError(f"Unexpected indentation at line: {line!r}")
        if ":" not in line:
            raise FrontmatterError(f"Expected key: value, got: {line!r}")
        key, rest = line.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        if not YAML_KEY_RE.fullmatch(key):
            raise FrontmatterError(f"Invalid YAML key: {key!r}")
        if key in result:
            raise FrontmatterError(f"Duplicate YAML key: {key!r}")
        if rest in {">", ">-", "|", "|-"}:
            folded = rest.startswith(">")
            block: list[str] = []
            index += 1
            while index < len(lines) and (
                not lines[index].strip() or lines[index].startswith(" ")
            ):
                block_line = lines[index]
                if "\t" in block_line:
                    raise FrontmatterError(
                        f"Tabs are not supported in frontmatter: {block_line!r}"
                    )
                if block_line.strip() and not block_line.startswith("  "):
                    raise FrontmatterError(
                        f"Block scalar content must be indented by two spaces: {block_line!r}"
                    )
                block.append(block_line[2:] if block_line.strip() else "")
                index += 1
            joined = (
                " ".join(part.strip() for part in block if part.strip())
                if folded
                else "\n".join(block)
            )
            result[key] = joined.strip()
            continue
        if rest == "":
            nested: dict[str, str] = {}
            index += 1
            while index < len(lines) and (
                lines[index].startswith((" ", "\t")) or not lines[index].strip()
            ):
                nested_line = lines[index]
                if not nested_line.strip():
                    index += 1
                    continue
                if "\t" in nested_line:
                    raise FrontmatterError(
                        f"Tabs are not supported in frontmatter: {nested_line!r}"
                    )
                if not nested_line.startswith("  ") or nested_line.startswith("   "):
                    raise FrontmatterError(
                        "Nested mappings must use exactly two spaces and may not nest again: "
                        f"{nested_line!r}"
                    )
                stripped = nested_line.strip()
                if ":" not in stripped:
                    raise FrontmatterError(f"Expected nested key: value, got: {stripped!r}")
                nested_key, nested_rest = stripped.split(":", 1)
                nested_key = nested_key.strip()
                if not YAML_KEY_RE.fullmatch(nested_key):
                    raise FrontmatterError(f"Invalid nested YAML key: {nested_key!r}")
                if nested_key in nested:
                    raise FrontmatterError(f"Duplicate nested YAML key: {nested_key!r}")
                if not nested_rest.strip():
                    raise FrontmatterError(
                        f"Nested YAML value must be a string scalar: {stripped!r}"
                    )
                nested[nested_key] = _parse_scalar(nested_rest)
                index += 1
            if not nested:
                raise FrontmatterError(f"YAML mapping {key!r} must contain string entries")
            result[key] = nested
            continue
        result[key] = _parse_scalar(rest)
        index += 1
    return result


def skill_directories(skills_root: Path) -> list[Path]:
    if not skills_root.is_dir():
        raise SystemExit(f"Missing skills directory: {skills_root}")
    return sorted(path for path in skills_root.iterdir() if path.is_dir() and not path.name.startswith("."))


def extract_markdown_targets(markdown: str) -> list[str]:
    targets: list[str] = []
    for match in MARKDOWN_LINK_RE.finditer(markdown):
        target = match.group(1).strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1].strip()
        if " " in target:
            target = target.split(" ", 1)[0]
        targets.append(target)
    return targets


def is_external_or_anchor(target: str) -> bool:
    lowered = target.lower()
    return (
        lowered.startswith(("http://", "https://", "mailto:", "tel:"))
        or target.startswith("#")
        or lowered.startswith("data:")
    )


def public_text_for_language_check(markdown: str) -> str:
    without_fences = re.sub(r"```.*?```", " ", markdown, flags=re.S)
    without_inline = re.sub(r"`[^`]+`", " ", without_fences)
    without_urls = re.sub(r"https?://\S+", " ", without_inline)
    return without_urls


def check_english(text: str, label: str) -> list[str]:
    sample = public_text_for_language_check(text)
    hits = NON_LATIN_RE.findall(sample)
    if hits:
        unique = "".join(sorted(set(hits)))[:20]
        return [f"{label}: public content contains non-English script characters ({unique!r})"]
    return []


def validate_skill_dir(skill_dir: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir.relative_to(repo_root)}: missing SKILL.md"]

    text = skill_md.read_text(encoding="utf-8")
    rel = skill_md.relative_to(repo_root).as_posix()
    line_count = text.count("\n") + (0 if text.endswith("\n") or text == "" else 1)
    if line_count > MAX_SKILL_LINES:
        errors.append(f"{rel}: SKILL.md has {line_count} lines (max {MAX_SKILL_LINES})")

    try:
        yaml_text, body = split_frontmatter(text)
        data = parse_simple_yaml(yaml_text)
    except FrontmatterError as exc:
        return [f"{rel}: {exc}"]

    for field in REQUIRED_FRONTMATTER:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{rel}: required frontmatter field {field!r} must be a string")

    for field, value in data.items():
        if field not in {*REQUIRED_FRONTMATTER, "metadata"} and not isinstance(value, str):
            errors.append(f"{rel}: frontmatter field {field!r} must be a string")

    raw_name = data.get("name", "")
    raw_description = data.get("description", "")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    description = raw_description.strip() if isinstance(raw_description, str) else ""
    if name:
        if len(name) > MAX_NAME_LEN:
            errors.append(f"{rel}: name exceeds {MAX_NAME_LEN} characters")
        if not NAME_RE.fullmatch(name):
            errors.append(
                f"{rel}: name {name!r} is not lowercase kebab-case "
                "(a-z, 0-9, single hyphens; no leading/trailing/consecutive hyphens)"
            )
        if name != skill_dir.name:
            errors.append(f"{rel}: name {name!r} does not match directory {skill_dir.name!r}")
    if description and len(description) > MAX_DESCRIPTION_LEN:
        errors.append(f"{rel}: description exceeds {MAX_DESCRIPTION_LEN} characters")

    if "metadata" in data and not isinstance(data["metadata"], dict):
        errors.append(f"{rel}: metadata must be a mapping of string keys to string values")

    errors.extend(check_english(text, rel))

    for target in extract_markdown_targets(text):
        if is_external_or_anchor(target):
            continue
        path_part = target.split("#", 1)[0]
        if not path_part:
            continue
        resolved = (skill_md.parent / path_part).resolve()
        try:
            resolved.relative_to(skill_dir.resolve())
        except ValueError:
            errors.append(f"{rel}: relative link escapes the skill package: {target}")
            continue
        if not resolved.exists():
            errors.append(f"{rel}: relative link does not resolve: {target}")

    return errors


def iter_public_markdown(repo_root: Path) -> list[Path]:
    roots = [
        repo_root / "docs",
        repo_root / "adapters",
        repo_root / "skills",
    ]
    files: list[Path] = []
    for path in repo_root.glob("*.md"):
        files.append(path)
    for root in roots:
        if root.is_dir():
            files.extend(root.rglob("*.md"))
    return sorted({path.resolve() for path in files if path.is_file()})


def validate_markdown_file(path: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    rel = path.relative_to(repo_root).as_posix()
    text = path.read_text(encoding="utf-8")
    errors.extend(check_english(text, rel))
    skills_root = (repo_root / "skills").resolve()
    try:
        package_relative = path.resolve().relative_to(skills_root)
        allowed_root = skills_root / package_relative.parts[0]
        escape_label = "skill package"
    except ValueError:
        allowed_root = repo_root.resolve()
        escape_label = "repository"
    for target in extract_markdown_targets(text):
        if is_external_or_anchor(target):
            continue
        path_part = target.split("#", 1)[0]
        if not path_part:
            continue
        resolved = (path.parent / path_part).resolve()
        try:
            resolved.relative_to(allowed_root)
        except ValueError:
            errors.append(f"{rel}: relative link escapes the {escape_label}: {target}")
            continue
        if not resolved.exists():
            errors.append(f"{rel}: relative link does not resolve: {target}")
    return errors


def declared_skill_name(skill_dir: Path) -> str | None:
    """Best-effort frontmatter name, or None when it cannot be read."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return None
    try:
        yaml_text, _body = split_frontmatter(skill_md.read_text(encoding="utf-8"))
        value = parse_simple_yaml(yaml_text).get("name")
    except (FrontmatterError, OSError, UnicodeDecodeError):
        return None
    return value.strip() if isinstance(value, str) and value.strip() else None


def validate_repository(repo_root: Path) -> list[str]:
    repo_root = repo_root.resolve()
    skills_root = repo_root / "skills"
    errors: list[str] = []
    # Case-insensitive so a collision is caught here rather than by whichever
    # filesystem the kit is installed onto.
    names: dict[str, Path] = {}
    directories = skill_directories(skills_root)
    if not directories:
        errors.append("no skill directories found under skills/")
    for skill_dir in directories:
        declared = declared_skill_name(skill_dir) or skill_dir.name
        key = declared.casefold()
        if key in names:
            errors.append(
                f"duplicate skill name {declared!r}: "
                f"{names[key].relative_to(repo_root).as_posix()} and "
                f"{skill_dir.relative_to(repo_root).as_posix()}"
            )
        else:
            names[key] = skill_dir
        errors.extend(validate_skill_dir(skill_dir, repo_root))
    for markdown in iter_public_markdown(repo_root):
        # SKILL.md is already checked with stricter rules above.
        if markdown.name == "SKILL.md" and skills_root.resolve() in markdown.parents:
            continue
        errors.extend(validate_markdown_file(markdown, repo_root))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate canonical Agent Skills.")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: detect from this script)",
    )
    args = parser.parse_args(argv)
    repo_root = args.root.resolve() if args.root else repo_root_from()
    errors = validate_repository(repo_root)
    if errors:
        print("Skill validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    skill_count = len(skill_directories(repo_root / "skills"))
    print(f"OK: {skill_count} skill(s) validated under {repo_root / 'skills'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
