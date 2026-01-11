# Warhammer 40K Roster Reminders

A tool for generating phase-based reminders from BattleScribe roster files for Warhammer 40,000 10th Edition.

## Features

- **Automatic catalog downloads** from BSData GitHub repository
- **Phase-organized reminders** for Command, Movement, Shooting, Charge, and Fight phases
- **Detachment support** with army-wide and detachment-specific rules
- **Roster file parsing** (.ros and .rosz formats)
- **PDF export** for easy printing and reference
- **Graphical User Interface** for simple operation

## Installation

1. Ensure Python 3.x is installed
2. Install required packages:
   ```bash
   pip install fpdf2
   ```

## Usage

### GUI Mode (Recommended)

Run the graphical interface:

```bash
python gui.py
```

**Steps:**

1. Click **"Browse..."** to select your roster file (.ros or .rosz)
2. Click **"Process Roster"** to generate reminders
3. Review the output in the text area
4. Click **"Export to PDF"** to save as a PDF file

### Command Line Mode

Process a roster file:

```bash
python reminders.py your_roster.rosz
```

The tool will:

- Parse the roster file
- Download necessary game system and catalog files
- Display reminders organized by phase
- Prompt to export to PDF

Process a single unit:

```bash
python reminders.py "Imperium - Space Wolves" "Captain in Terminator Armour"
```

With detachment:

```bash
python reminders.py "Imperium - Space Wolves" "Captain in Terminator Armour" "Gladius Task Force"
```

## Output Format

### Console/GUI Output

- **Army-Wide Rules**: Displayed once at the top (e.g., Oath of Moment, Combat Doctrines)
- **Unit Sections**: Each unit shows only its unique abilities
- **Phase Organization**: Reminders grouped by game phase
- **Icons**:
  - 🔹 Army rules
  - 🔷 Detachment rules
  - ⚡ Unit-specific abilities
  - 📌 Passive abilities

### PDF Output

- Clean, formatted document
- Army name and detachment header
- Army-wide rules section (shown once)
- Individual unit sections with composition
- Proper text wrapping and pagination

## File Structure

- **gui.py**: Graphical user interface
- **reminders.py**: Core reminder generation engine
- **rosterParser.py**: Roster file parser (.ros/.rosz)
- **catalog_manager.py**: BattleScribe catalog downloader
- **catConvert.py**: Catalog XML to JSON converter
- **cache/**: Downloaded catalog files (auto-generated)

## Supported Armies

All armies from the BSData/wh40k-10e repository, including:

- Space Marines (and all chapters)
- Tyranids
- Necrons
- Orks
- And many more...

## How It Works

1. **Roster Parsing**: Reads BattleScribe roster files to extract units and selections
2. **Catalog Download**: Automatically downloads required catalog files from GitHub
3. **Rule Resolution**: Resolves unit abilities, army rules, and detachment bonuses
4. **Phase Categorization**: Organizes abilities by game phase based on keywords
5. **Deduplication**: Shows army-wide rules once, not repeated for each unit
6. **Export**: Generates formatted PDF with all reminders

## Tips

- The tool caches downloaded catalogs in the `cache/` folder for faster subsequent runs
- Army-wide rules like "Oath of Moment" are shown once at the top
- Unit composition (e.g., sergeants with squads) is automatically grouped
- Passive abilities that are always active are listed separately

## Troubleshooting

**"Could not find unit"**: The unit name in your roster might not match the catalog. Check spelling and ensure you have the latest catalogs.

**Unicode errors in PDF**: The tool automatically converts special characters. If issues persist, the text is being cleaned to ASCII-safe equivalents.

**Catalog not found**: Ensure you have internet connection for the first run to download catalogs from GitHub.

## License

This tool uses data from the BattleScribe Data project (BSData) under their license terms.
