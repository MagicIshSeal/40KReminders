import xml.etree.ElementTree as ET
import zipfile
import json
from pathlib import Path
from typing import Dict, List, Optional

class RosterParser:
    """Parse BattleScribe roster files (.ros or .rosz)"""
    
    def __init__(self, roster_file: str):
        self.roster_file = Path(roster_file)
        self.ns = {'bs': 'http://www.battlescribe.net/schema/rosterSchema'}
        self.data = None
        self._parse()
    
    def _parse(self):
        """Parse the roster file"""
        try:
            # Handle .rosz (zipped) files
            if self.roster_file.suffix.lower() == '.rosz':
                with zipfile.ZipFile(self.roster_file, 'r') as zip_ref:
                    # Find the .ros file inside
                    ros_files = [f for f in zip_ref.namelist() if f.endswith('.ros')]
                    if not ros_files:
                        raise ValueError("No .ros file found in .rosz archive")
                    
                    # Read the first .ros file
                    with zip_ref.open(ros_files[0]) as f:
                        tree = ET.parse(f)
            else:
                # Handle .ros files directly
                tree = ET.parse(self.roster_file)
            
            root = tree.getroot()
            
            # Extract namespace if present
            if root.tag.startswith('{'):
                ns_url = root.tag.split('}')[0].strip('{')
                self.ns = {'bs': ns_url}
            
            self.data = {
                'name': root.get('name', 'Unknown'),
                'battleScribeVersion': root.get('battleScribeVersion', 'Unknown'),
                'gameSystemName': root.get('gameSystemName', 'Unknown'),
                'cost': self._get_cost(root),
                'forces': []
            }
            
            # Parse forces (army lists)
            forces = root.findall('bs:forces/bs:force', self.ns)
            for force in forces:
                force_data = self._parse_force(force)
                self.data['forces'].append(force_data)
                
        except Exception as e:
            raise ValueError(f"Error parsing roster file: {e}")
    
    def _get_cost(self, element) -> Dict[str, float]:
        """Extract cost values"""
        costs = {}
        cost_list = element.find('bs:costs', self.ns)
        if cost_list is not None:
            for cost in cost_list.findall('bs:cost', self.ns):
                cost_name = cost.get('name', '')
                cost_value = float(cost.get('value', 0))
                costs[cost_name] = cost_value
        return costs
    
    def _parse_force(self, force_element) -> Dict:
        """Parse a force (army list)"""
        force_data = {
            'name': force_element.get('name', 'Unknown'),
            'catalogueName': force_element.get('catalogueName', 'Unknown'),
            'cost': self._get_cost(force_element),
            'detachment': None,
            'units': []
        }
        
        # Find top-level selections (direct children of force/selections)
        for selection in force_element.findall('bs:selections/bs:selection', self.ns):
            selection_type = selection.get('type', '')
            selection_name = selection.get('name', '')
            
            # Detect detachment (usually type="upgrade" with specific names)
            if selection_type == 'upgrade':
                # Check if this is a detachment container
                for nested in selection.findall('bs:selections/bs:selection', self.ns):
                    nested_name = nested.get('name', '')
                    if any(keyword in nested_name.lower() 
                        for keyword in ['task force', 'detachment', 'fleet', 'swarm', 'host', 'onslaught', 
                                       'assault group', 'spearhead', 'siege', 'conclave', 'blade', 'broodsurge',
                                       'stampede', 'claw', 'nexus', 'vanguard']):
                        force_data['detachment'] = nested_name
                        break
            
            # Units are typically type="model" or "unit"
            elif selection_type in ['model', 'unit']:
                # Count models in this unit
                models = selection.findall('bs:selections/bs:selection[@type="model"]', self.ns)
                model_count = sum(int(m.get('number', 1)) for m in models)
                
                # Get unit composition details
                composition = []
                for model in models:
                    model_name = model.get('name', '')
                    model_num = int(model.get('number', 1))
                    if model_num > 1:
                        composition.append(f"{model_num}x {model_name}")
                    else:
                        composition.append(model_name)
                
                unit_data = {
                    'name': selection_name,
                    'type': selection_type,
                    'cost': self._get_cost(selection),
                    'customName': selection.get('customName', ''),
                    'number': int(selection.get('number', 1)),
                    'model_count': model_count if model_count > 0 else 1,
                    'composition': composition
                }
                force_data['units'].append(unit_data)
        
        return force_data
    
    def _get_parent_type(self, element) -> Optional[str]:
        """Get the type of the parent selection"""
        parent = element.find('..')
        if parent is not None and parent.tag.endswith('selection'):
            return parent.get('type', '')
        return None
    
    def get_army_name(self) -> str:
        """Get the army/catalogue name"""
        if self.data and self.data['forces']:
            return self.data['forces'][0]['catalogueName']
        return 'Unknown'
    
    def get_detachment(self) -> Optional[str]:
        """Get the selected detachment"""
        if self.data and self.data['forces']:
            return self.data['forces'][0]['detachment']
        return None
    
    def get_units(self) -> List[Dict]:
        """Get all units in the roster"""
        if self.data and self.data['forces']:
            return self.data['forces'][0]['units']
        return []
    
    def get_summary(self) -> str:
        """Get a text summary of the roster"""
        if not self.data:
            return "No roster data"
        
        lines = []
        lines.append(f"Roster: {self.data['name']}")
        lines.append(f"Game System: {self.data['gameSystemName']}")
        
        if self.data['cost'].get('pts'):
            lines.append(f"Total Points: {self.data['cost']['pts']}")
        
        lines.append("")
        
        for force in self.data['forces']:
            lines.append(f"Force: {force['name']}")
            lines.append(f"Army: {force['catalogueName']}")
            
            if force['detachment']:
                lines.append(f"Detachment: {force['detachment']}")
            
            if force['cost'].get('pts'):
                lines.append(f"Force Points: {force['cost']['pts']}")
            
            lines.append(f"\nUnits ({len(force['units'])}):")
            for unit in force['units']:
                unit_name = unit['customName'] or unit['name']
                count = unit['number']
                cost = unit['cost'].get('pts', 0)
                model_count = unit.get('model_count', 1)
                composition = unit.get('composition', [])
                
                # Display unit with model count if it's a squad
                if count > 1:
                    lines.append(f"  • {count}x {unit_name} ({cost} pts)")
                else:
                    if model_count > 1 and composition:
                        # Show squad composition
                        lines.append(f"  • {unit_name} ({cost} pts)")
                        lines.append(f"      └─ {', '.join(composition)}")
                    else:
                        lines.append(f"  • {unit_name} ({cost} pts)")
        
        return '\n'.join(lines)
    
    def to_json(self, output_file: Optional[str] = None) -> str:
        """Convert roster to JSON"""
        json_output = json.dumps(self.data, indent=2, ensure_ascii=False)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"JSON data written to {output_file}")
        
        return json_output


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python rosterParser.py <roster_file.ros|.rosz> [--json] [-o output.json]")
        print("\nExample: python rosterParser.py my_army.rosz")
        print("Example: python rosterParser.py my_army.ros --json -o output.json")
        return
    
    roster_file = sys.argv[1]
    
    try:
        parser = RosterParser(roster_file)
        
        if '--json' in sys.argv:
            output_file = None
            if '-o' in sys.argv:
                try:
                    output_index = sys.argv.index('-o')
                    output_file = sys.argv[output_index + 1]
                except (IndexError, ValueError):
                    print("Error: -o flag requires an output filename")
                    return
            
            parser.to_json(output_file)
        else:
            print(parser.get_summary())
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
