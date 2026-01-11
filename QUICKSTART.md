# Quick Start Guide

## Installation

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the interactive mode:**

   ```bash
   python interactive.py
   ```

3. Select your army from the list (downloads automatically)
4. Enter unit names to get phase-organized reminders

## Quick Commands

```bash
# Interactive mode (recommended for first-time use)
python interactive.py

# Quick lookup
python reminders.py "Space Marines" "Captain"

# List all armies
python reminders.py --list-armies

# List available catalogs
python catalog_manager.py --list
```

## What's New

- ✅ **Auto-downloads catalogs** from GitHub BSData/wh40k-10e
- ✅ **46 armies available** - all official 10th edition catalogs
- ✅ **Caching system** - Download once, use offline
- ✅ **Army switching** - Type 'switch' in interactive mode
- ✅ **No manual file management** - Everything is automatic

## Next Steps

1. Run `pip install -r requirements.txt` to install dependencies
2. Run `python interactive.py` to start
3. Select your army from the list
4. Look up units and their phase-based reminders!

All catalogs are automatically downloaded from the official [BSData/wh40k-10e](https://github.com/BSData/wh40k-10e) repository and cached locally for offline use.
