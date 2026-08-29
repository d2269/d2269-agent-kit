# Scripts

Deterministic tools for this kit. No third-party Python packages.

| Script | Purpose |
| --- | --- |
| `validate_skills.py` | Validate strict string-only YAML frontmatter, names, package-contained links, size, and English public content |
| `install_skills.py` | Copy or symlink canonical skills into a verified adapter path |

```bash
python3 scripts/validate_skills.py
python3 scripts/install_skills.py --help
python3 -m unittest discover -s scripts/tests -v
```

Platform paths and safety rules: [docs/installation.md](../docs/installation.md).
