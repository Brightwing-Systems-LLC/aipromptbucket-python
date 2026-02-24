"""CLI entry point for the `apb` command."""

from __future__ import annotations

import argparse
import sys

from .client import Client
from .scanner import Scanner


def _print_findings(findings):
    print(f"\nFound {len(findings)} potential prompt(s):\n")
    for i, f in enumerate(findings, 1):
        vars_info = f" ({len(f.variables)} vars)" if f.variables else ""
        preview = f.text[:60].replace("\n", " ")
        print(f'  {i}. {f.file}:{f.line}  -- "{preview}..."{vars_info}')


def _interactive_select(findings):
    """Let user choose which findings to import."""
    sys.stdout.write("\nImport all? [Y/n/select] ")
    sys.stdout.flush()
    choice = input().strip().lower()

    if choice == "n":
        print("Aborted.")
        return []
    elif choice == "select":
        sys.stdout.write("Enter numbers to import (comma-separated): ")
        sys.stdout.flush()
        nums = input().strip()
        indices = [int(n.strip()) - 1 for n in nums.split(",") if n.strip().isdigit()]
        return [findings[i] for i in indices if 0 <= i < len(findings)]
    return findings


def cmd_scan(args):
    """Scan a directory for hardcoded prompts and optionally import them."""
    scanner = Scanner(min_length=args.min_length)
    findings = scanner.scan(args.path)

    if not findings:
        print("No potential prompts found.")
        return

    _print_findings(findings)

    if args.dry_run:
        print("\n--dry-run: No changes made.")
        return

    if args.auto:
        to_import = findings
    else:
        to_import = _interactive_select(findings)
        if not to_import:
            return

    client = Client()
    imported = 0

    for finding in to_import:
        slug = Scanner.generate_slug(finding)
        name = Scanner.generate_name(finding)

        result = client.create_prompt(
            name=name,
            slug=slug,
            template_text=finding.text,
            description=f"Imported from {finding.file}:{finding.line}",
            template_format=finding.detected_format,
            tags=["imported", "apb-scan"],
        )

        if result.ok:
            imported += 1
            print(f"  Imported: {slug}")
        elif "already exists" in (result.error or ""):
            print(f"  Skipping '{slug}' (already exists)")
        else:
            print(f"  Failed to import '{slug}': {result.error}")

    print(f"\nImported {imported} prompt(s).")


def main():
    parser = argparse.ArgumentParser(
        prog="apb",
        description="AI Prompt Bucket CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    # scan subcommand
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan a directory for hardcoded prompts",
    )
    scan_parser.add_argument("path", help="Directory to scan")
    scan_parser.add_argument(
        "--team", required=True, help="Team slug to import prompts into"
    )
    scan_parser.add_argument(
        "--dry-run", action="store_true", help="Show findings without importing"
    )
    scan_parser.add_argument(
        "--auto", action="store_true", help="Import all without confirmation"
    )
    scan_parser.add_argument(
        "--min-length",
        type=int,
        default=100,
        help="Minimum string length to consider (default: 100)",
    )

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
