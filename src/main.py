#!/usr/bin/env python3
"""
ROM Consolidation and Thumbnail Tool

Commands:
    consolidate - Merge multiple ROM sets into a single organized directory
    thumbnails  - Download game artwork from Libretro Thumbnails Server

Usage:
    # Consolidate ROMs
    python -m src.main consolidate --input /path/to/romset1 --output /path/to/output

    # Download thumbnails for consolidated ROMs
    python -m src.main thumbnails --input /path/to/consolidated --type boxart
"""

import argparse
import sys
from pathlib import Path

from .consolidator import consolidate_roms, ConsolidationResult
from .thumbnails import download_thumbnails, ThumbnailResult


def print_consolidation_summary(
    result: ConsolidationResult, dry_run: bool = False
) -> None:
    """Print a summary of the consolidation results."""
    action = "Would copy" if dry_run else "Copied"

    print("\n" + "=" * 60)
    print("CONSOLIDATION SUMMARY")
    print("=" * 60)
    print(f"  {action}: {result.copied} files")
    print(f"  Duplicates skipped: {result.skipped_duplicates}")
    if result.skipped_existing > 0:
        print(f"  Already in output: {result.skipped_existing}")
    if result.skipped_filtered > 0:
        print(f"  Filtered out (not in systems list): {result.skipped_filtered}")

    if result.errors:
        print(f"  Errors: {len(result.errors)}")
        for error in result.errors[:10]:  # Show first 10 errors
            print(f"    - {error}")
        if len(result.errors) > 10:
            print(f"    ... and {len(result.errors) - 10} more errors")

    # Group copied files by source directory
    if result.copied_files:
        print("\n" + "-" * 60)
        print("FILES BY SOURCE DIRECTORY")
        print("-" * 60)

        # Group by source directory
        by_source: dict[str, list[tuple[str, str]]] = {}
        for system, filename, dest, source in result.copied_files:
            if source not in by_source:
                by_source[source] = []
            by_source[source].append((system, filename))

        for source_dir, files in sorted(by_source.items()):
            print(f"\n  From: {source_dir}")
            print(f"  Games copied: {len(files)}")
            # Show first 10 files per source
            for system, filename in files[:10]:
                print(f"    - [{system}] {filename}")
            if len(files) > 10:
                print(f"    ... and {len(files) - 10} more")

    print("\n" + "=" * 60)


def print_thumbnail_summary(result: ThumbnailResult, dry_run: bool = False) -> None:
    """Print a summary of the thumbnail download results."""
    action = "Would download" if dry_run else "Downloaded"

    print("\n" + "=" * 60)
    print("THUMBNAIL SUMMARY")
    print("=" * 60)
    print(f"  {action}: {result.downloaded} images")
    if result.skipped_existing > 0:
        print(f"  Already exists: {result.skipped_existing}")
    if result.skipped_not_found > 0:
        print(f"  Not found on server: {result.skipped_not_found}")
    if result.skipped_no_mapping > 0:
        print(f"  No Libretro mapping: {result.skipped_no_mapping}")

    if result.errors:
        print(f"  Errors: {len(result.errors)}")
        for error in result.errors[:10]:
            print(f"    - {error}")
        if len(result.errors) > 10:
            print(f"    ... and {len(result.errors) - 10} more errors")

    print("=" * 60)


def cmd_consolidate(args: argparse.Namespace) -> int:
    """Handle the consolidate subcommand."""
    # Validate input directories
    for input_dir in args.input_dirs:
        if not input_dir.exists():
            print(f"Error: Input directory not found: {input_dir}", file=sys.stderr)
            return 1
        if not input_dir.is_dir():
            print(f"Error: Not a directory: {input_dir}", file=sys.stderr)
            return 1

    # Create output directory if it doesn't exist (unless dry run)
    if not args.dry_run:
        args.output.mkdir(parents=True, exist_ok=True)

    # Parse systems filter
    systems_filter = None
    if args.systems:
        systems_filter = [s.strip().lower() for s in args.systems.split(",")]

    print("ROM Consolidation Tool")
    print(f"  Input directories: {len(args.input_dirs)}")
    for i, d in enumerate(args.input_dirs, 1):
        print(f"    {i}. {d}")
    print(f"  Output directory: {args.output}")
    if systems_filter:
        print(f"  Systems filter: {', '.join(systems_filter)}")
    if args.dry_run:
        print("  Mode: DRY RUN (no files will be copied)")
    print()

    # Run consolidation
    try:
        result = consolidate_roms(
            source_dirs=args.input_dirs,
            output_dir=args.output,
            dry_run=args.dry_run,
            verbose=args.verbose,
            systems_filter=systems_filter,
        )

        print_consolidation_summary(result, args.dry_run)

        return 0 if not result.errors else 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_thumbnails(args: argparse.Namespace) -> int:
    """Handle the thumbnails subcommand."""
    # Validate input directory
    if not args.input.exists():
        print(f"Error: Directory not found: {args.input}", file=sys.stderr)
        return 1
    if not args.input.is_dir():
        print(f"Error: Not a directory: {args.input}", file=sys.stderr)
        return 1

    # Parse systems filter
    systems_filter = None
    if args.systems:
        systems_filter = [s.strip().lower() for s in args.systems.split(",")]

    print("Thumbnail Downloader")
    print(f"  ROM directory: {args.input}")
    print(f"  Thumbnail type: {args.type}")
    if systems_filter:
        print(f"  Systems filter: {', '.join(systems_filter)}")
    if args.dry_run:
        print("  Mode: DRY RUN (no files will be downloaded)")
    print()

    # Run thumbnail download
    try:
        result = download_thumbnails(
            rom_dir=args.input,
            thumbnail_type=args.type,
            dry_run=args.dry_run,
            verbose=args.verbose,
            systems_filter=systems_filter,
            max_workers=args.workers,
        )

        print_thumbnail_summary(result, args.dry_run)

        return 0 if not result.errors else 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="ROM Consolidation and Thumbnail Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Consolidate subcommand
    consolidate_parser = subparsers.add_parser(
        "consolidate",
        help="Consolidate multiple ROM sets into one directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input ~/roms/set1 --input ~/roms/set2 --output ~/consolidated
  %(prog)s --input ~/roms/set1 --output ~/consolidated --systems gb,gba,gbc
        """,
    )
    consolidate_parser.add_argument(
        "--input",
        "-i",
        action="append",
        dest="input_dirs",
        type=Path,
        required=True,
        metavar="DIR",
        help="Input ROM set directory (can be specified multiple times)",
    )
    consolidate_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        metavar="DIR",
        help="Output directory for consolidated ROMs",
    )
    consolidate_parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Preview changes without copying files",
    )
    consolidate_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed progress",
    )
    consolidate_parser.add_argument(
        "--systems",
        "-s",
        type=str,
        default=None,
        metavar="SYSTEMS",
        help="Comma-separated list of systems to process (e.g., gb,gba,gbc)",
    )

    # Thumbnails subcommand
    thumbnails_parser = subparsers.add_parser(
        "thumbnails",
        help="Download game thumbnails from Libretro",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input ~/consolidated_roms --type boxart
  %(prog)s --input ~/consolidated_roms --systems gb,gba --type snap
        """,
    )
    thumbnails_parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        metavar="DIR",
        help="Directory containing consolidated ROMs",
    )
    thumbnails_parser.add_argument(
        "--type",
        "-t",
        type=str,
        default="boxart",
        choices=["boxart", "snap", "title"],
        help="Thumbnail type: boxart (box art), snap (screenshot), title (title screen)",
    )
    thumbnails_parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Preview without downloading",
    )
    thumbnails_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed progress",
    )
    thumbnails_parser.add_argument(
        "--systems",
        "-s",
        type=str,
        default=None,
        metavar="SYSTEMS",
        help="Comma-separated list of systems to process (e.g., gb,gba,gbc)",
    )
    thumbnails_parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=5,
        metavar="N",
        help="Number of concurrent downloads (default: 5)",
    )

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "consolidate":
        return cmd_consolidate(args)
    elif args.command == "thumbnails":
        return cmd_thumbnails(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
