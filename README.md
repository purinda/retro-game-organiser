# ROM Consolidation & BoxArt Downloader Tool

A Python CLI tool to consolidate multiple ROM sets into a single organized directory, with smart region-aware duplicate detection and thumbnail downloading from Libretro.

## Features

- **Multiple Input Sources**: Accept multiple ROM set directories
- **Systems Filter**: Process only specific systems (e.g., `--systems gb,gba,gbc`)
- **Region-Aware Deduplication**: Keeps regional variants, removes exact duplicates
- **Thumbnail Downloads**: Fetch box art, screenshots, and title screens from Libretro
- **Organized Output**: Creates folders with format `SHORTHAND-Full Name`
- **Dry Run Mode**: Preview changes without copying/downloading

## Quick Start

```bash
# Setup
cd /Users/purinda/src/retro-game-organiser
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Commands

### Consolidate ROMs

```bash
# Preview consolidation (dry run)
python -m src.main consolidate \
    --input /path/to/romset1 \
    --input /path/to/romset2 \
    --output /path/to/consolidated \
    --dry-run --verbose

# Actual consolidation
python -m src.main consolidate \
    --input /path/to/romset1 \
    --output /path/to/consolidated

# Consolidate only specific systems
python -m src.main consolidate \
    --input /path/to/romset1 \
    --output /path/to/consolidated \
    --systems gb,gba,gbc
```

### Download Thumbnails

Download game artwork from the [Libretro Thumbnails Server](https://github.com/libretro-thumbnails):

```bash
# Download box art for all systems
python -m src.main thumbnails \
    --input /path/to/consolidated \
    --type boxart

# Download screenshots for Game Boy systems only
python -m src.main thumbnails \
    --input /path/to/consolidated \
    --systems gb,gba,gbc \
    --type snap

# Preview without downloading
python -m src.main thumbnails \
    --input /path/to/consolidated \
    --dry-run --verbose
```

**Thumbnail types:**
- `boxart` - Box art / cover images
- `snap` - In-game screenshots
- `title` - Title screen images

**Output structure:**
```
consolidated/
  gb-Nintendo Game Boy/
    images/
      boxarts/
        Pokemon Red (USA).png
      snaps/
        Pokemon Red (USA).png
```

## Duplicate Detection

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
Thumbnail support for 50+ systems via Libretro mapping.
