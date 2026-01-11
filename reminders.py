import json
import re
from typing import List, Dict

# 40K Game Phases
PHASES = [
    "Command Phase",
    "Movement Phase", 
    "Shooting Phase",
    "Charge Phase",
    "Fight Phase",
    "Any Phase"
]

class UnitReminder:
    def __init__(self, json_file, game_system_file=None):
        with open(json_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        # Load game system file if provided
        self.game_system_data = None
        if game_system_file:
            try:
                with open(game_system_file, 'r', encoding='utf-8') as f:
                    self.game_system_data = json.load(f)
            except:
                pass
        
        # Load imported catalogs
        self.imported_catalogs = []
        self._load_imported_catalogs(json_file)
        
        # Build lookup tables
        self.units_cache = {}
        self.rules_cache = {}
        self.profiles_cache = {}
        self._build_caches()
    
    def _load_imported_catalogs(self, json_file):
        """Load catalogs that this catalog imports from"""
        from pathlib import Path
        cache_dir = Path(json_file).parent
        
        for link in self.data.get('catalogueLinks', []):
            if link.get('name'):
                # Try to find corresponding JSON file
                catalog_name = link['name'] + '.json'
                catalog_path = cache_dir / catalog_name
                
                if catalog_path.exists():
                    try:
                        with open(catalog_path, 'r', encoding='utf-8') as f:
                            imported_data = json.load(f)
                            self.imported_catalogs.append(imported_data)
                    except:
                        pass
    
    def _build_caches(self):
        """Build searchable caches"""
        # Cache units
        for entry in self.data['selectionEntries']:
            if entry['type'] in ['unit', 'model']:
                unit_name = entry['name'].lower()
                self.units_cache[unit_name] = entry
        
        # Cache detachments
        self.detachments_cache = {}
        for group in self.data.get('selectionEntryGroups', []):
            if group['name'] == 'Detachment':
                for det_entry in group.get('selectionEntries', []):
                    self.detachments_cache[det_entry['name']] = det_entry
        
        # Also check imported catalogs for detachments
        for imported in self.imported_catalogs:
            for group in imported.get('selectionEntryGroups', []):
                if group['name'] == 'Detachment':
                    for det_entry in group.get('selectionEntries', []):
                        if det_entry['name'] not in self.detachments_cache:
                            self.detachments_cache[det_entry['name']] = det_entry
        
        # Cache rules from catalog
        for rule in self.data.get('sharedRules', []):
            self.rules_cache[rule['id']] = rule
        
        # Cache profiles from catalog
        for profile in self.data.get('sharedProfiles', []):
            self.profiles_cache[profile['id']] = profile
        
        # Cache from imported catalogs
        for imported in self.imported_catalogs:
            for rule in imported.get('sharedRules', []):
                if rule['id'] not in self.rules_cache:
                    self.rules_cache[rule['id']] = rule
            
            for profile in imported.get('sharedProfiles', []):
                if profile['id'] not in self.profiles_cache:
                    self.profiles_cache[profile['id']] = profile
        
        # Cache rules and profiles from game system if available
        if self.game_system_data:
            for rule in self.game_system_data.get('sharedRules', []):
                if rule['id'] not in self.rules_cache:
                    self.rules_cache[rule['id']] = rule
            
            for profile in self.game_system_data.get('sharedProfiles', []):
                if profile['id'] not in self.profiles_cache:
                    self.profiles_cache[profile['id']] = profile
    
    def find_unit(self, unit_name: str) -> Dict:
        """Find a unit by name (case-insensitive partial match)"""
        unit_name_lower = unit_name.lower()
        
        # Exact match first
        if unit_name_lower in self.units_cache:
            return self.units_cache[unit_name_lower]
        
        # Partial match
        matches = []
        for name, unit in self.units_cache.items():
            if unit_name_lower in name:
                matches.append(unit)
        
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            print(f"Multiple matches found:")
            for i, unit in enumerate(matches, 1):
                print(f"  {i}. {unit['name']}")
            return None
        
        return None
    
    def list_detachments(self):
        """List all available detachments"""
        if not self.detachments_cache:
            print("No detachments found in this catalog.")
            return []
        
        print(f"\nAvailable Detachments ({len(self.detachments_cache)}):")
        print("-" * 50)
        for i, name in enumerate(sorted(self.detachments_cache.keys()), 1):
            print(f"  {i}. {name}")
        return list(self.detachments_cache.keys())
    
    def _categorize_ability(self, description: str) -> List[str]:
        """Analyze ability text to determine which phase(s) it applies to"""
        # Clean up special formatting characters and normalize spaces
        desc_lower = description.lower().replace('**', '').replace('^^', '')
        # Replace non-breaking spaces and other unicode spaces with regular spaces
        desc_lower = desc_lower.replace('\u00a0', ' ').replace('\u2009', ' ')
        
        # Skip generic always-active rules first
        if any(skip in desc_lower for skip in [
            'this model can be attached to',
            'while a bodyguard unit contains a leader',
            'each time the last model in a bodyguard',
            'embarking within transports',
            'scouts',
            'stealth'
        ]):
            return ["Always Active"]
        
        # Check for SPECIFIC phase triggers FIRST (most specific)
        if "at the start of your command phase" in desc_lower:
            return ["Command Phase"]
        
        # Check for movement phase first
        if "at the start of your movement phase" in desc_lower or "in your movement phase" in desc_lower:
            return ["Movement Phase"]
        
        # Then check for command phase (less specific)
        if "in your command phase" in desc_lower:
            return ["Command Phase"]
        
        # Check for "once per battle" in command phase
        if "in either player" in desc_lower and "command phase" in desc_lower:
            return ["Command Phase"]
        
        if "at the start of the fight phase" in desc_lower:
            return ["Fight Phase"]
        
        if "in the fight phase" in desc_lower or "when this unit fights" in desc_lower:
            return ["Fight Phase"]
        
        if "in the shooting phase" in desc_lower or "when this unit shoots" in desc_lower:
            return ["Shooting Phase"]
        
        if "in the charge phase" in desc_lower or "when this unit charges" in desc_lower:
            return ["Charge Phase"]
        
        if "deep strike" in desc_lower:
            return ["Movement Phase"]
        
        # Only after checking all specific phases, check for always active
        return ["Always Active"]
    
    def get_reminders(self, unit_name: str, detachment_name: str = None) -> Dict[str, List[Dict]]:
        """Get phase-organized reminders for a unit"""
        unit = self.find_unit(unit_name)
        
        if not unit:
            return None
        
        # Organize abilities by phase
        phase_reminders = {phase: [] for phase in PHASES}
        phase_reminders["Always Active"] = []
        seen_abilities = {}  # Track to avoid duplicates
        
        # Extract abilities from profiles
        for profile in unit.get('profiles', []):
            if profile.get('typeName') == 'Abilities':
                ability_name = profile['name']
                
                # Skip generic/useless abilities
                skip_ability_names = ['Leader', 'Scouts', 'Stealth', 'Deep Strike', 'Embarking within Transports']
                if ability_name in skip_ability_names:
                    continue
                
                for char in profile.get('characteristics', []):
                    if char['name'] == 'Description':
                        description = char['value']
                        
                        # Skip overly verbose generic rules
                        if len(description) > 500:
                            continue
                        
                        phases = self._categorize_ability(description)
                        
                # Skip if categorized as passive/generic
                        if phases == ["Always Active"] and any(skip in description.lower() for skip in [
                            'this model can be attached',
                            'embarking within transports',
                            'invulnerable save'
                        ]):
                            continue
                        
                        # Create unique key to avoid duplicates
                        ability_key = f"{ability_name}:{description[:50]}"
                        if ability_key in seen_abilities:
                            continue
                        seen_abilities[ability_key] = True
                        
                        reminder = {
                            'ability': ability_name,
                            'description': description,
                            'source': 'unit'
                        }
                        
                        # Only add to first matching phase
                        if phases:
                            phase_reminders[phases[0]].append(reminder)
        
        # Extract abilities from infoLinks
        for info_link in unit.get('infoLinks', []):
            if info_link.get('hidden', 'false') == 'true':
                continue
            
            target_id = info_link.get('targetId', '')
            link_type = info_link.get('type', '')
            ability_name = info_link.get('name', '')
            
            # Skip generic rules that clutter output
            skip_rules = ['Leader', 'Deep Strike', 'Invulnerable Save', 'Scouts', 'Stealth', 'Embarking within Transports', 'Deadly Demise', 'Lethal Hits', 'Sustained Hits', 'Devastating Wounds', 'Feel No Pain']
            if ability_name in skip_rules or any(skip in ability_name for skip in ['Invulnerable Save', 'Deadly Demise', 'Feel No Pain']):
                continue
            
            # Resolve rule
            if link_type == 'rule' and target_id in self.rules_cache:
                rule = self.rules_cache[target_id]
                description = rule.get('description', '')
                
                # Skip overly long descriptions (keep important army rules)
                if len(description) > 800 or not description:
                    continue
                
                # Create unique key
                ability_key = f"{rule['name']}:{description[:50]}"
                if ability_key in seen_abilities:
                    continue
                seen_abilities[ability_key] = True
                
                phases = self._categorize_ability(description)
                
                reminder = {
                    'ability': rule['name'],
                    'description': description,
                    'source': 'army_rule'
                }
                
                # Only add to first matching phase
                if phases:
                    phase_reminders[phases[0]].append(reminder)
            
            # Resolve profile
            elif link_type == 'profile' and target_id in self.profiles_cache:
                profile = self.profiles_cache[target_id]
                
                for char in profile.get('characteristics', []):
                    if char['name'] == 'Description':
                        description = char['value']
                        
                        # Skip overly long descriptions
                        if len(description) > 800 or not description:
                            continue
                        
                        # Create unique key
                        ability_key = f"{profile['name']}:{description[:50]}"
                        if ability_key in seen_abilities:
                            continue
                        seen_abilities[ability_key] = True
                        
                        phases = self._categorize_ability(description)
                        
                        reminder = {
                            'ability': profile['name'],
                            'description': description,
                            'source': 'army_ability'
                        }
                        
                        # Only add to first matching phase
                        if phases:
                            phase_reminders[phases[0]].append(reminder)
        
        # Extract detachment-specific abilities
        if detachment_name and detachment_name in self.detachments_cache:
            detachment = self.detachments_cache[detachment_name]
            
            for profile in detachment.get('profiles', []):
                if profile.get('typeName') == 'Abilities':
                    ability_name = profile['name']
                    
                    for char in profile.get('characteristics', []):
                        if char['name'] == 'Description':
                            description = char['value']
                            
                            if len(description) > 800 or not description:
                                continue
                            
                            ability_key = f"detachment:{ability_name}:{description[:50]}"
                            if ability_key in seen_abilities:
                                continue
                            seen_abilities[ability_key] = True
                            
                            phases = self._categorize_ability(description)
                            
                            reminder = {
                                'ability': ability_name,
                                'description': description,
                                'source': 'detachment'
                            }
                            
                            if phases:
                                phase_reminders[phases[0]].append(reminder)
        
        return {
            'unit_name': unit['name'],
            'unit_type': unit['type'],
            'cost': next((c['value'] for c in unit['costs'] if c['name'] == 'pts'), 0),
            'stats': self._get_unit_stats(unit),
            'detachment': detachment_name,
            'reminders': {k: v for k, v in phase_reminders.items() if v}
        }
    
    def _get_unit_stats(self, unit: Dict) -> Dict:
        """Extract unit stats"""
        for profile in unit.get('profiles', []):
            if profile.get('typeName') == 'Unit':
                stats = {}
                for char in profile.get('characteristics', []):
                    stats[char['name']] = char['value']
                return stats
        return {}
    
    def display_reminders(self, unit_name: str, detachment_name: str = None):
        """Display formatted reminders for a unit"""
        result = self.get_reminders(unit_name, detachment_name)
        
        if not result:
            print(f"Unit '{unit_name}' not found.")
            return
        
        print(f"\n{'='*70}")
        print(f"UNIT: {result['unit_name']}")
        if result.get('detachment'):
            print(f"DETACHMENT: {result['detachment']}")
        print(f"{'='*70}")
        print(f"Cost: {result['cost']} pts", end="")
        
        if result['stats']:
            stats_str = " | ".join([f"{k}: {v}" for k, v in result['stats'].items()])
            print(f" | {stats_str}")
        else:
            print()
        
        print(f"{'='*70}")
        
        # Display reminders organized by phase
        for phase in PHASES:
            if phase in result['reminders'] and result['reminders'][phase]:
                print(f"\n📍 {phase.upper()}")
                print("-" * 70)
                for reminder in result['reminders'][phase]:
                    # Shorter description (truncate if too long)
                    desc = reminder['description']
                    # Remove formatting characters
                    desc = desc.replace('**', '').replace('^^', '')
                    if len(desc) > 250:
                        desc = desc[:247] + "..."
                    
                    # Clean up formatting
                    desc = desc.replace('\n', ' ').replace('  ', ' ')
                    desc = desc.replace('■', '\n      •')
                    
                    source_map = {
                        'army_rule': ('🔹', '[Army] '),
                        'army_ability': ('🔹', '[Army] '),
                        'detachment': ('🔷', '[Detachment] ')
                    }
                    source_icon, source_label = source_map.get(reminder.get('source'), ('⚡', ''))
                    
                    print(f"  {source_icon} {source_label}{reminder['ability']}")
                    print(f"      {desc}")
                    print()
        
        # Always active abilities (keep these minimal)
        if "Always Active" in result['reminders'] and result['reminders']['Always Active']:
            print(f"\n📌 PASSIVE ABILITIES")
            print("-" * 70)
            for reminder in result['reminders']['Always Active']:
                desc = reminder['description']
                # Remove formatting characters
                desc = desc.replace('**', '').replace('^^', '')
                if len(desc) > 150:
                    desc = desc[:147] + "..."
                desc = desc.replace('\n', ' ').replace('  ', ' ')
                print(f"  • {reminder['ability']}: {desc}")
        
        print(f"\n{'='*70}\n")
    
    def list_all_units(self):
        """List all available units"""
        print(f"\nAvailable Units ({len(self.units_cache)}):")
        print("-" * 50)
        for i, name in enumerate(sorted(self.units_cache.keys()), 1):
            print(f"  {i}. {self.units_cache[name]['name']}")


def main():
    import sys
    from catalog_manager import CatalogDownloader
    
    if len(sys.argv) < 2:
        print("Usage: python reminders.py <army_name> <unit_name> [detachment_name]")
        print("       python reminders.py <army_name> --list-detachments")
        print("       python reminders.py --list-armies")
        print("\nExample: python reminders.py 'Space Marines' 'Captain in Gravis Armour' 'Gladius Task Force'")
        print("Example: python reminders.py 'Tyranids' 'Hive Tyrant'")
        print("Example: python reminders.py 'Space Marines' --list-detachments")
        return
    
    downloader = CatalogDownloader()
    
    # List armies
    if sys.argv[1] == '--list-armies':
        downloader.list_catalogs()
        return
    
    # Get army and unit
    if len(sys.argv) < 3:
        print("Please provide both army name and unit name.")
        print("Example: python reminders.py 'Space Marines' 'Captain'")
        return
    
    army_name = sys.argv[1]
    
    # Download game system file
    print("Loading game system...")
    game_system_file = downloader.download_game_system()
    
    # Download/load catalog
    print(f"Loading {army_name} catalog...")
    json_file = downloader.download_catalog(army_name)
    
    if not json_file:
        print(f"Failed to load catalog for {army_name}")
        return
    
    # Load the reminder system
    reminder = UnitReminder(json_file, game_system_file)
    
    # Check if listing detachments
    if len(sys.argv) > 2 and sys.argv[2] == '--list-detachments':
        reminder.list_detachments()
        return
    
    # Get unit and detachment names
    unit_name = sys.argv[2] if len(sys.argv) > 2 else None
    if not unit_name:
        print("Please provide a unit name.")
        return
    
    # Check if detachment specified (remaining args after unit name)
    detachment_name = None
    if len(sys.argv) > 3:
        detachment_name = ' '.join(sys.argv[3:])
    
    reminder.display_reminders(unit_name, detachment_name)


if __name__ == "__main__":
    main()
