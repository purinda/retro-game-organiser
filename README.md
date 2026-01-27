# ROM Consolidation Tool

A Python CLI tool to consolidate multiple ROM sets into a single organized directory, with smart region-aware duplicate detection.

## Features

- **Multiple Input Sources**: Accept multiple ROM set directories
- **Region-Aware Deduplication**: 
  - Keeps all unique region variants (e.g., both `Game (USA)` and `Game (EU)`)
  - Only removes exact duplicates (same game + same region)
  - Strips numeric prefixes like `001 ` but preserves region info
- **Directory Flattening**: Handles subdirectories within system folders
- **Organized Output**: Creates folders with format `SHORTHAND-Full Name` (e.g., `PSP-Sony PlayStation Portable`)
- **Dry Run Mode**: Preview changes without copying files

## Quick Start

```bash
# Clone and setup
cd /Users/purinda/src/retro-game-organiser
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Preview consolidation (dry run)
python -m src.main \
    --input /path/to/romset1 \
    --input /path/to/romset2 \
    --output /path/to/consolidated \
    --dry-run --verbose

# Actual consolidation
python -m src.main \
    --input /path/to/romset1 \
    --input /path/to/romset2 \
    --output /path/to/consolidated
```

## Example

Given these input ROM sets:

```
romset1/saturn/
├── Game (USA).bin
└── Game (Europe).bin

romset2/saturn/
├── 001 Game (USA).bin  # Duplicate (same region as Game (USA).bin)
└── Game (Japan).bin    # Unique (different region)
```

Output:
```
consolidated/saturn-Sega Saturn/
├── Game (USA).bin
├── Game (Europe).bin
└── Game (Japan).bin
```

Note: `001 Game (USA).bin` was skipped (duplicate of `Game (USA).bin`).

## Duplicate Detection Logic

Two files are duplicates if they have:
1. Same system (case-insensitive)
2. Same base game name (after stripping prefixes like `001 `)
3. **Same region/version** (different regions are NOT duplicates)

## Running Tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

## Supported Systems

150+ retro gaming systems. See `src/systems.py` for the complete list.
