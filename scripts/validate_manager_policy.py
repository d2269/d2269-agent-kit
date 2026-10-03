#!/usr/bin/env python3
"""Validate an optional project-local D2269 manager policy.

Stdlib only. Exit non-zero on any validation failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1"
SKILL_NAMES = (
    "d2269-architect",
    "d2269-tech-lead",
    "d2269-developer",
    "d2269-code-review",
    "d2269-qa",
    "d2269-researcher",
    "d2269-technical-documentation",
    "d2269-orchestrator",
)
SECRET_FIELD_RE = re.compile(
    r"(?:api[-_]?key|access[-_]?token|auth(?:orization)?|credential|"
    r"password|passwd|private[-_]?key|secret|(?:^|_)token(?:$|_))",
    re.IGNORECASE,
)
SECRET_ARGUMENT_RE = re.compile(
    r"^--?(?:api[-_]?key|access[-_]?token|auth(?:orization)?|credential|"
    r"password|passwd|private[-_]?key|secret|token)(?:=|$)",
    re.IGNORECASE,
)
ENV_WRAPPERS = frozenset(("--env", "--environment", "-e"))
ENV_WRAPPER_ASSIGNMENTS = ("--environment=", "--env=", "-e=")
SENSITIVE_ENV_NAME_RE = re.compile(
    r"(?:^|_)(?:API_KEY|APIKEY|ACCESS_KEY(?:_ID)?|ACCESS_TOKEN|AUTH_TOKEN|"
    r"AUTHORIZATION|PRIVATE_KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIALS?)(?:_|$)",
    re.IGNORECASE,
)
SECRET_VALUE_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{10,}\b", re.IGNORECASE),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", re.IGNORECASE),
)


class PolicyError(ValueError):
    """Raised when policy JSON is invalid or unsafe."""


def _is_sensitive_environment_name(name: str) -> bool:
    normalized = name.strip().upper()
    if re.fullmatch(r"(?:[A-Z0-9]+_)*MAX_OUTPUT_TOKENS", normalized):
        return False
    return bool(SENSITIVE_ENV_NAME_RE.search(normalized))


def _environment_name(spec: str) -> str:
    """Return the name part of an environment assignment or wrapper spec."""
    stripped = spec.strip()
    delimiters = [
        position
        for position in (stripped.find("="), stripped.find(","))
        if position >= 0
    ]
    return stripped[: min(delimiters)].strip() if delimiters else stripped


def _validate_environment_arguments(args: list[str]) -> None:
    def validate_name(name: str) -> None:
        if _is_sensitive_environment_name(name):
            raise PolicyError("credential-like environment argument is not allowed")

    index = 0
    while index < len(args):
        argument = args[index]
        inline_prefix = next(
            (prefix for prefix in ENV_WRAPPER_ASSIGNMENTS if argument.startswith(prefix)),
            None,
        )
        if inline_prefix is not None:
            validate_name(_environment_name(argument[len(inline_prefix):]))
            index += 1
            continue
        if argument not in ENV_WRAPPERS:
            if "=" in argument:
                validate_name(_environment_name(argument))
            index += 1
            continue
        if index + 1 >= len(args):
            index += 1
            continue
        validate_name(_environment_name(args[index + 1]))
        index += 1


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PolicyError("duplicate JSON field")
        result[key] = value
    return result


def load_policy(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyError(f"cannot read policy file: {exc.strerror or exc}") from exc
    try:
        return json.loads(text, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, PolicyError) as exc:
        raise PolicyError(f"invalid JSON: {exc}") from exc


def _check_no_secret_fields(value: Any, location: str = "policy") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_FIELD_RE.search(key.replace("-", "_").replace(".", "_")):
                raise PolicyError("credential-like field is not allowed")
            _check_no_secret_fields(child, location)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_no_secret_fields(child, f"{location}[{index}]")
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS):
            raise PolicyError("credential-like value is not allowed")
        _validate_environment_arguments([value])


def _object_fields(value: Any, *, required: set[str], allowed: set[str], location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PolicyError(f"{location} must be an object")
    missing = required - value.keys()
    unknown = value.keys() - allowed
    if missing:
        raise PolicyError(f"{location} is missing required field(s)")
    if unknown:
        raise PolicyError(f"{location} has unknown field(s)")
    return value


def _validate_executor(value: Any, location: str) -> None:
    if not isinstance(value, dict):
        raise PolicyError(f"{location} must be an executor object")
    executor = value.get("executor")
    if executor == "native":
        fields = _object_fields(
            value,
            required={"executor", "model"},
            allowed={"executor", "model"},
            location=location,
        )
        model = fields["model"]
        if not isinstance(model, str) or not model.strip():
            raise PolicyError(f"{location}.model must be a non-empty string")
        return
    if executor == "herdr":
        fields = _object_fields(
            value,
            required={"executor", "kind", "model", "args"},
            allowed={"executor", "kind", "model", "args"},
            location=location,
        )
        if not isinstance(fields["kind"], str) or not fields["kind"].strip():
            raise PolicyError(f"{location}.kind must be a non-empty string")
        if not isinstance(fields["model"], str) or not fields["model"].strip():
            raise PolicyError(f"{location}.model must be a non-empty string")
        args = fields["args"]
        if not isinstance(args, list) or any(not isinstance(arg, str) for arg in args):
            raise PolicyError(f"{location}.args must be an array of strings")
        _validate_environment_arguments(args)
        for index, arg in enumerate(args):
            if SECRET_ARGUMENT_RE.search(arg):
                raise PolicyError(
                    "credential-like command-line argument is not allowed"
                )
        split_bearer_value = any(
            re.search(r"\bBearer\s*$", argument, re.IGNORECASE)
            and next_argument.strip()
            for argument, next_argument in zip(args, args[1:])
        )
        if split_bearer_value or any(
            pattern.search(arg) for arg in args for pattern in SECRET_VALUE_PATTERNS
        ):
            raise PolicyError("credential-like command-line value is not allowed")
        return
    raise PolicyError(f"{location}.executor must be 'native' or 'herdr'")


def validate_policy(value: Any) -> list[str]:
    """Return an empty list for a valid policy, otherwise safe diagnostics."""
    try:
        _check_no_secret_fields(value)
        policy = _object_fields(
            value,
            required={"schema_version", "routes"},
            allowed={"schema_version", "routes"},
            location="policy",
        )
        if policy["schema_version"] != SCHEMA_VERSION:
            raise PolicyError(f"schema_version must be {SCHEMA_VERSION!r}")
        routes = _object_fields(
            policy["routes"],
            allowed=set(SKILL_NAMES),
            required=set(),
            location="routes",
        )
        for skill, route_value in routes.items():
            route = _object_fields(
                route_value,
                required={"primary", "alternatives"},
                allowed={"primary", "alternatives"},
                location=f"routes.{skill}",
            )
            _validate_executor(route["primary"], f"routes.{skill}.primary")
            alternatives = route["alternatives"]
            if not isinstance(alternatives, list):
                raise PolicyError(f"routes.{skill}.alternatives must be an array")
            for index, executor in enumerate(alternatives):
                _validate_executor(executor, f"routes.{skill}.alternatives[{index}]")
    except PolicyError as exc:
        return [str(exc)]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a project-local D2269 manager policy JSON file."
    )
    parser.add_argument(
        "policy",
        nargs="?",
        type=Path,
        default=Path(".d2269/manager-policy.json"),
        help="policy JSON path (default: .d2269/manager-policy.json)",
    )
    args = parser.parse_args(argv)
    try:
        policy = load_policy(args.policy)
    except PolicyError as exc:
        print(f"Invalid manager policy: {exc}", file=sys.stderr)
        return 2
    errors = validate_policy(policy)
    if errors:
        for error in errors:
            print(f"Invalid manager policy: {error}", file=sys.stderr)
        return 1
    print(f"Valid manager policy: {args.policy}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
