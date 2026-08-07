#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
from typing import Dict


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_METADATA_ROOT = REPO_ROOT / "fastlane" / "metadata"


def discover_release_notes(metadata_root: Path) -> Dict[str, Path]:
    result: Dict[str, Path] = {}
    if not metadata_root.exists():
        raise FileNotFoundError(f"metadata root not found: {metadata_root}")

    for child in sorted(metadata_root.iterdir()):
        if not child.is_dir():
            continue
        target = child / "release_notes.txt"
        if target.exists():
            result[child.name] = target
    return result


def load_translations(path: Path) -> Dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("translations file must be a JSON object")

    translations: Dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("translations JSON must map string locale to string content")
        translations[key] = value.rstrip() + "\n"
    return translations


def build_preview(notes_files: Dict[str, Path], translations: Dict[str, str]) -> str:
    lines: list[str] = []
    locales = sorted(notes_files.keys())
    lines.append("Target locales:")
    for locale in locales:
        lines.append(f"- {locale}")

    missing = [locale for locale in locales if locale not in translations]
    extra = [locale for locale in sorted(translations.keys()) if locale not in notes_files]
    if missing:
        lines.append("")
        lines.append("Missing translations:")
        for locale in missing:
            lines.append(f"- {locale}")
    if extra:
        lines.append("")
        lines.append("Translations without target file:")
        for locale in extra:
            lines.append(f"- {locale}")

    for locale in locales:
        if locale not in translations:
            continue
        current_text = notes_files[locale].read_text(encoding="utf-8")
        new_text = translations[locale]
        diff = difflib.unified_diff(
            current_text.splitlines(),
            new_text.splitlines(),
            fromfile=f"{locale}/release_notes.txt (current)",
            tofile=f"{locale}/release_notes.txt (new)",
            lineterm="",
        )
        lines.append("")
        lines.extend(diff)
    return "\n".join(lines).rstrip() + "\n"


def apply_translations(notes_files: Dict[str, Path], translations: Dict[str, str]) -> list[Path]:
    written: list[Path] = []
    for locale, path in notes_files.items():
        if locale not in translations:
            continue
        path.write_text(translations[locale], encoding="utf-8")
        written.append(path)
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or apply fastlane metadata release notes updates."
    )
    parser.add_argument(
        "--metadata-root",
        default=str(DEFAULT_METADATA_ROOT),
        help="Path to fastlane metadata root",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-locales", help="List locales that have release_notes.txt")

    for name in ("preview", "apply"):
        cmd = subparsers.add_parser(name, help=f"{name} release notes from translations JSON")
        cmd.add_argument(
            "--translations-file",
            required=True,
            help="JSON file mapping locale to translated release notes",
        )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata_root = Path(args.metadata_root).resolve()
    notes_files = discover_release_notes(metadata_root)

    if args.command == "list-locales":
        for locale in sorted(notes_files.keys()):
            print(locale)
        return 0

    translations = load_translations(Path(args.translations_file).resolve())
    if args.command == "preview":
        print(build_preview(notes_files, translations), end="")
        return 0

    written = apply_translations(notes_files, translations)
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
