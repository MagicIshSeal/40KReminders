import json
import re
from typing import List, Dict
from fpdf import FPDF
from datetime import datetime

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
        # Cache units from main catalog
        for entry in self.data['selectionEntries']:
            if entry['type'] in ['unit', 'model']:
                unit_name = entry['name'].lower()
                self.units_cache[unit_name] = entry
        
        # Cache units from imported catalogs
        for imported in self.imported_catalogs:
            for entry in imported.get('selectionEntries', []):
                if entry['type'] in ['unit', 'model']:
                    unit_name = entry['name'].lower()
                    # Don't overwrite units from main catalog
                    if unit_name not in self.units_cache:
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
    
    def display_roster_reminders(self, roster_units: list, detachment_name: str = None):
        """Display reminders for all units in a roster"""
        print(f"\n{'='*70}")
        print(f"ROSTER REMINDERS")
        if detachment_name:
            print(f"DETACHMENT: {detachment_name}")
        print(f"{'='*70}\n")
        
        # Collect army-wide and detachment-wide rules (show once)
        army_rules = {}
        detachment_rules = {}
        
        # Get first unit to extract army/detachment rules
        if roster_units:
            first_unit = roster_units[0]
            unit_name = first_unit.get('customName') or first_unit.get('name')
            result = self.get_reminders(unit_name, detachment_name)
            
            if result and result.get('reminders'):
                # Extract army and detachment rules
                for phase, reminders in result['reminders'].items():
                    for reminder in reminders:
                        source = reminder.get('source')
                        if source in ['army_rule', 'army_ability']:
                            if phase not in army_rules:
                                army_rules[phase] = []
                            army_rules[phase].append(reminder)
                        elif source == 'detachment':
                            if phase not in detachment_rules:
                                detachment_rules[phase] = []
                            detachment_rules[phase].append(reminder)
                
                # Display army-wide and detachment rules once
                if army_rules or detachment_rules:
                    print("ARMY-WIDE RULES")
                    print("─" * 70)
                    
                    for phase in PHASES:
                        phase_reminders = army_rules.get(phase, []) + detachment_rules.get(phase, [])
                        if phase_reminders:
                            print(f"\n  📍 {phase.upper()}")
                            for reminder in phase_reminders:
                                desc = reminder['description'].replace('**', '').replace('^^', '')
                                if len(desc) > 150:
                                    desc = desc[:147] + "..."
                                desc = desc.replace('\n', ' ').replace('  ', ' ')
                                
                                source_map = {
                                    'army_rule': '🔹',
                                    'army_ability': '🔹',
                                    'detachment': '🔷'
                                }
                                icon = source_map.get(reminder.get('source'), '⚡')
                                print(f"    {icon} {reminder['ability']}: {desc}")
                    
                    print(f"\n{'='*70}\n")
        
        units_found = 0
        units_not_found = []
        
        for unit_data in roster_units:
            unit_name = unit_data.get('customName') or unit_data.get('name')
            count = unit_data.get('number', 1)
            composition = unit_data.get('composition', [])
            
            result = self.get_reminders(unit_name, detachment_name)
            
            if not result:
                units_not_found.append(unit_name)
                continue
            
            units_found += 1
            
            # Display unit header with composition
            print(f"\n{'─'*70}")
            if count > 1:
                print(f"📋 {count}x {unit_name}")
            else:
                print(f"📋 {unit_name}")
            
            if composition:
                print(f"   └─ {', '.join(composition)}")
            print(f"{'─'*70}")
            
            # Display only unit-specific reminders (skip army/detachment rules)
            has_reminders = False
            for phase in PHASES:
                if phase in result['reminders'] and result['reminders'][phase]:
                    # Filter out army and detachment rules
                    unit_specific = [r for r in result['reminders'][phase] 
                                   if r.get('source') not in ['army_rule', 'army_ability', 'detachment']]
                    
                    if unit_specific:
                        has_reminders = True
                        print(f"\n  📍 {phase.upper()}")
                        for reminder in unit_specific:
                            desc = reminder['description'].replace('**', '').replace('^^', '')
                            if len(desc) > 150:
                                desc = desc[:147] + "..."
                            desc = desc.replace('\n', ' ').replace('  ', ' ')
                            print(f"    ⚡ {reminder['ability']}: {desc}")
            
            # Always active abilities (brief)
            if "Always Active" in result['reminders'] and result['reminders']['Always Active']:
                if has_reminders:
                    print()
                print("  📌 Passive:", end="")
                ability_names = [r['ability'] for r in result['reminders']['Always Active']]
                print(" " + ", ".join(ability_names))
            
            # If no unit-specific abilities, show message
            if not has_reminders and not result['reminders'].get('Always Active'):
                print("  No unit-specific abilities")
        
        # Summary
        print(f"\n{'='*70}")
        print(f"✓ Displayed reminders for {units_found} unit(s)")
        if units_not_found:
            print(f"⚠ Could not find: {', '.join(units_not_found)}")
        print(f"{'='*70}\n")

    def export_roster_to_pdf(self, roster_units: list, detachment_name: str = None, 
                            army_name: str = None, filename: str = "roster_reminders.pdf"):
        """Export roster reminders to a PDF file"""
        
        def clean_text(text):
            """Clean text for PDF encoding"""
            # Replace common unicode characters
            replacements = {
                ''': "'", ''': "'", '"': '"', '"': '"',
                '–': '-', '—': '-', '…': '...',
                '×': 'x', '•': '*'
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            # Remove any remaining non-ASCII characters
            return text.encode('ascii', 'ignore').decode('ascii')
        
        pdf = FPDF()
        pdf.set_margins(15, 15, 15)
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Title
        pdf.set_font('Helvetica', 'B', 16)
        pdf.cell(0, 10, 'WARHAMMER 40K ROSTER REMINDERS', new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', new_x="LMARGIN", new_y="NEXT", align='C')
        
        if army_name:
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 8, f'Army: {clean_text(army_name)}', new_x="LMARGIN", new_y="NEXT", align='C')
        
        if detachment_name:
            pdf.set_font('Helvetica', 'I', 11)
            pdf.cell(0, 6, f'Detachment: {clean_text(detachment_name)}', new_x="LMARGIN", new_y="NEXT", align='C')
        
        pdf.ln(5)
        
        # Collect army-wide and detachment-wide rules
        army_rules = {}
        detachment_rules = {}
        
        if roster_units:
            first_unit = roster_units[0]
            unit_name = first_unit.get('customName') or first_unit.get('name')
            result = self.get_reminders(unit_name, detachment_name)
            
            if result and result.get('reminders'):
                for phase, reminders in result['reminders'].items():
                    for reminder in reminders:
                        source = reminder.get('source')
                        if source in ['army_rule', 'army_ability']:
                            if phase not in army_rules:
                                army_rules[phase] = []
                            army_rules[phase].append(reminder)
                        elif source == 'detachment':
                            if phase not in detachment_rules:
                                detachment_rules[phase] = []
                            detachment_rules[phase].append(reminder)
                
                # Display army-wide and detachment rules
                if army_rules or detachment_rules:
                    pdf.set_fill_color(220, 220, 220)
                    pdf.set_font('Helvetica', 'B', 12)
                    pdf.cell(0, 8, 'ARMY-WIDE RULES', new_x="LMARGIN", new_y="NEXT", fill=True)
                    pdf.ln(2)
                    
                    for phase in PHASES:
                        phase_reminders = army_rules.get(phase, []) + detachment_rules.get(phase, [])
                        if phase_reminders:
                            pdf.set_font('Helvetica', 'B', 11)
                            pdf.cell(0, 6, phase.upper(), new_x="LMARGIN", new_y="NEXT")
                            
                            for reminder in phase_reminders:
                                source_prefix = '* ' if reminder.get('source') in ['army_rule', 'army_ability'] else '+ '
                                pdf.set_font('Helvetica', '', 10)
                                
                                ability = clean_text(reminder['ability'])
                                desc = clean_text(reminder['description'].replace('**', '').replace('^^', '').replace('\n', ' '))
                                
                                # Handle long text - use explicit width
                                text = f"{source_prefix}{ability}: {desc}"
                                pdf.multi_cell(w=0, h=5, text=text, new_x="LMARGIN", new_y="NEXT")
                            
                            pdf.ln(2)
                    
                    pdf.ln(3)
        
        # Display units
        units_found = 0
        for unit_data in roster_units:
            unit_name = unit_data.get('customName') or unit_data.get('name')
            count = unit_data.get('number', 1)
            composition = unit_data.get('composition', [])
            
            result = self.get_reminders(unit_name, detachment_name)
            
            if not result:
                continue
            
            units_found += 1
            
            # Unit header
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font('Helvetica', 'B', 11)
            if count > 1:
                pdf.cell(0, 7, clean_text(f'{count}x {unit_name}'), new_x="LMARGIN", new_y="NEXT", fill=True)
            else:
                pdf.cell(0, 7, clean_text(unit_name), new_x="LMARGIN", new_y="NEXT", fill=True)
            
            if composition:
                pdf.set_font('Helvetica', 'I', 9)
                pdf.cell(0, 5, '  ' + clean_text(', '.join(composition)), new_x="LMARGIN", new_y="NEXT")
            
            pdf.ln(1)
            
            # Display only unit-specific reminders
            has_reminders = False
            for phase in PHASES:
                if phase in result['reminders'] and result['reminders'][phase]:
                    unit_specific = [r for r in result['reminders'][phase] 
                                   if r.get('source') not in ['army_rule', 'army_ability', 'detachment']]
                    
                    if unit_specific:
                        has_reminders = True
                        pdf.set_font('Helvetica', 'B', 10)
                        pdf.cell(0, 5, phase.upper(), new_x="LMARGIN", new_y="NEXT")
                        
                        for reminder in unit_specific:
                            pdf.set_font('Helvetica', '', 9)
                            ability = clean_text(reminder['ability'])
                            desc = clean_text(reminder['description'].replace('**', '').replace('^^', '').replace('\n', ' '))
                            text = f"  > {ability}: {desc}"
                            pdf.multi_cell(w=0, h=4, text=text, new_x="LMARGIN", new_y="NEXT")
                        
                        pdf.ln(1)
            
            # Always active abilities
            if "Always Active" in result['reminders'] and result['reminders']['Always Active']:
                pdf.set_font('Helvetica', 'I', 9)
                ability_names = [clean_text(r['ability']) for r in result['reminders']['Always Active']]
                text = f"  Passive: {', '.join(ability_names)}"
                pdf.multi_cell(w=0, h=4, text=text, new_x="LMARGIN", new_y="NEXT")
            
            if not has_reminders and not result['reminders'].get('Always Active'):
                pdf.set_font('Helvetica', 'I', 9)
                pdf.cell(0, 4, '  No unit-specific abilities', new_x="LMARGIN", new_y="NEXT")
            
            pdf.ln(3)
        
        # Save PDF
        try:
            pdf.output(filename)
            print(f"\n✓ PDF exported to: {filename}")
            return filename
        except Exception as e:
            print(f"\n✗ Failed to export PDF: {e}")
            return None
    
    def list_all_units(self):
        """List all available units"""
        print(f"\nAvailable Units ({len(self.units_cache)}):")
        print("-" * 50)
        for i, name in enumerate(sorted(self.units_cache.keys()), 1):
            print(f"  {i}. {self.units_cache[name]['name']}")


def main():
    import sys
    from catalog_manager import CatalogDownloader
    from rosterParser import RosterParser
    from pathlib import Path
    
    if len(sys.argv) < 2:
        print("Usage: python reminders.py <roster_file.ros|.rosz>")
        print("       python reminders.py <army_name> <unit_name> [detachment_name]")
        print("       python reminders.py <army_name> --list-detachments")
        print("       python reminders.py --list-armies")
        print("\nRoster Mode:")
        print("  python reminders.py my_army.rosz")
        print("\nManual Mode:")
        print("  python reminders.py 'Space Marines' 'Captain in Gravis Armour' 'Gladius Task Force'")
        print("  python reminders.py 'Tyranids' 'Hive Tyrant'")
        print("  python reminders.py 'Space Marines' --list-detachments")
        return
    
    downloader = CatalogDownloader()
    
    # Check if first argument is a roster file
    first_arg = sys.argv[1]
    if Path(first_arg).suffix.lower() in ['.ros', '.rosz']:
        # ROSTER MODE
        try:
            print(f"Loading roster: {first_arg}")
            roster = RosterParser(first_arg)
            
            print("\n" + roster.get_summary())
            print()
            
            army_name = roster.get_army_name()
            detachment = roster.get_detachment()
            units = roster.get_units()
            
            if not units:
                print("No units found in roster.")
                return
            
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
            
            # Display reminders for all units
            reminder.display_roster_reminders(units, detachment)
            
            # Ask if user wants to export to PDF
            try:
                export = input("\nExport to PDF? (y/n): ").strip().lower()
                if export == 'y':
                    pdf_filename = f"{Path(first_arg).stem}_reminders.pdf"
                    reminder.export_roster_to_pdf(units, detachment, army_name, pdf_filename)
            except (KeyboardInterrupt, EOFError):
                print()  # Clean newline after interrupt
            
        except Exception as e:
            print(f"Error processing roster: {e}")
        return
    
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
