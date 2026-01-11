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
    def __init__(self, json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.units_cache = {}
        self._build_units_cache()
    
    def _build_units_cache(self):
        """Build a searchable cache of units"""
        for entry in self.data['selectionEntries']:
            if entry['type'] in ['unit', 'model']:
                unit_name = entry['name'].lower()
                self.units_cache[unit_name] = entry
    
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
    
    def _categorize_ability(self, description: str) -> List[str]:
        """Analyze ability text to determine which phase(s) it applies to"""
        desc_lower = description.lower()
        phases = []
        
        # Phase detection keywords
        phase_keywords = {
            "Command Phase": [
                "command phase", "start of your command phase",
                "during the command phase", "in your command phase"
            ],
            "Movement Phase": [
                "movement phase", "when this unit advances",
                "when this unit falls back", "normal move", "remain stationary"
            ],
            "Shooting Phase": [
                "shooting phase", "ranged attack", "ranged weapon",
                "shoot", "when this unit shoots", "before selecting targets"
            ],
            "Charge Phase": [
                "charge phase", "when this unit charges",
                "declare a charge", "charge roll"
            ],
            "Fight Phase": [
                "fight phase", "melee attack", "melee weapon",
                "when this unit fights", "close combat", "pile in", "consolidate"
            ],
            "Any Phase": [
                "any phase", "at any time", "once per battle",
                "each time", "while this", "when an attack"
            ]
        }
        
        for phase, keywords in phase_keywords.items():
            for keyword in keywords:
                if keyword in desc_lower:
                    if phase not in phases:
                        phases.append(phase)
        
        # If no specific phase detected but has timing indicators
        if not phases:
            timing_words = ["when", "while", "each time", "if", "at the"]
            if any(word in desc_lower for word in timing_words):
                phases.append("Any Phase")
        
        return phases if phases else ["Always Active"]
    
    def get_reminders(self, unit_name: str) -> Dict[str, List[Dict]]:
        """Get phase-organized reminders for a unit"""
        unit = self.find_unit(unit_name)
        
        if not unit:
            return None
        
        # Organize abilities by phase
        phase_reminders = {phase: [] for phase in PHASES}
        phase_reminders["Always Active"] = []
        
        # Extract abilities from profiles
        for profile in unit.get('profiles', []):
            if profile.get('typeName') == 'Abilities':
                ability_name = profile['name']
                
                for char in profile.get('characteristics', []):
                    if char['name'] == 'Description':
                        description = char['value']
                        phases = self._categorize_ability(description)
                        
                        reminder = {
                            'ability': ability_name,
                            'description': description
                        }
                        
                        for phase in phases:
                            phase_reminders[phase].append(reminder)
        
        return {
            'unit_name': unit['name'],
            'unit_type': unit['type'],
            'cost': next((c['value'] for c in unit['costs'] if c['name'] == 'pts'), 0),
            'stats': self._get_unit_stats(unit),
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
    
    def display_reminders(self, unit_name: str):
        """Display formatted reminders for a unit"""
        result = self.get_reminders(unit_name)
        
        if not result:
            print(f"Unit '{unit_name}' not found.")
            return
        
        print(f"\n{'='*70}")
        print(f"UNIT REMINDERS: {result['unit_name']}")
        print(f"{'='*70}")
        print(f"Type: {result['unit_type']} | Cost: {result['cost']} pts")
        
        if result['stats']:
            stats_str = " | ".join([f"{k}: {v}" for k, v in result['stats'].items()])
            print(f"Stats: {stats_str}")
        
        print(f"\n{'='*70}")
        
        for phase in PHASES + ["Always Active"]:
            if phase in result['reminders'] and result['reminders'][phase]:
                print(f"\n📍 {phase.upper()}")
                print("-" * 70)
                for reminder in result['reminders'][phase]:
                    print(f"  ⚡ {reminder['ability']}")
                    print(f"     {reminder['description']}")
                    print()
        
        print(f"{'='*70}\n")
    
    def list_all_units(self):
        """List all available units"""
        print(f"\nAvailable Units ({len(self.units_cache)}):")
        print("-" * 50)
        for i, name in enumerate(sorted(self.units_cache.keys()), 1):
            print(f"  {i}. {self.units_cache[name]['name']}")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python reminders.py <unit_name>")
        print("Example: python reminders.py 'Captain in Gravis Armour'")
        print("Example: python reminders.py 'Intercessor Squad'")
        print("\nTo list all units: python reminders.py --list")
        return
    
    # Load the reminder system
    reminder = UnitReminder('space_marines.json')
    
    if sys.argv[1] == '--list':
        reminder.list_all_units()
    else:
        unit_name = ' '.join(sys.argv[1:])
        reminder.display_reminders(unit_name)


if __name__ == "__main__":
    main()
