#!/usr/bin/env python3
"""
ROM Consolidation Tool

Consolidate multiple ROM sets into a single organized directory,
removing duplicates based on normalized game names.

Usage:
    python -m src.main --input /path/to/romset1 --input /path/to/romset2 --output /path/to/output

    # Dry run (preview without copying)
    python -m src.main --input /path/to/romset1 --output /path/to/output --dry-run

    # Verbose output
    python -m src.main --input /path/to/romset1 --output /path/to/output --verbose
"""

import argparse
import sys
from pathlib import Path

from .consolidator import consolidate_roms, ConsolidationResult


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Consolidate ROM sets and remove duplicates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input ~/roms/set1 --input ~/roms/set2 --output ~/consolidated_roms
  %(prog)s --input ~/roms/set1 --output ~/consolidated_roms --dry-run --verbose
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        action='append',
        dest='input_dirs',
        type=Path,
        required=True,
        metavar='DIR',
        help='Input ROM set directory (can be specified multiple times)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=Path,
        required=True,
        metavar='DIR',
        help='Output directory for consolidated ROMs'
    )
    
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Preview changes without copying files'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed progress'
    )
    
    return parser.parse_args()


def print_summary(result: ConsolidationResult, dry_run: bool = False) -> None:
    """Print a summary of the consolidation results."""
    action = "Would copy" if dry_run else "Copied"

    print("\n" + "=" * 60)
    print("CONSOLIDATION SUMMARY")
    print("=" * 60)
    print(f"  {action}: {result.copied} files")
    print(f"  Duplicates skipped: {result.skipped_duplicates}")

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


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
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
    
    print(f"ROM Consolidation Tool")
    print(f"  Input directories: {len(args.input_dirs)}")
    for i, d in enumerate(args.input_dirs, 1):
        print(f"    {i}. {d}")
    print(f"  Output directory: {args.output}")
    if args.dry_run:
        print("  Mode: DRY RUN (no files will be copied)")
    print()
    
    # Run consolidation
    try:
        result = consolidate_roms(
            source_dirs=args.input_dirs,
            output_dir=args.output,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        
        print_summary(result, args.dry_run)
        
        return 0 if not result.errors else 1
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
