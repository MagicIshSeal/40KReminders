import xml.etree.ElementTree as ET
import sys
import json
import io

# Set UTF-8 encoding for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def read_cat_file(filepath):
    """
    Read and parse a BattleScribe .cat (catalog) file
    """
    try:
        # Parse the XML file
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Extract namespace if present
        global ns
        ns = {'bs': 'http://www.battlescribe.net/schema/catalogueSchema'}
        if root.tag.startswith('{'):
            ns_url = root.tag.split('}')[0].strip('{')
            ns = {'bs': ns_url}
        
        # Display basic catalog information
        print(f"{'='*70}")
        print(f"CATALOG INFORMATION")
        print(f"{'='*70}")
        print(f"Catalog Name: {root.get('name', 'Unknown')}")
        print(f"Game System: {root.get('gameSystemId', 'Unknown')}")
        print(f"Revision: {root.get('revision', 'Unknown')}")
        print(f"Battle Scribe Version: {root.get('battleScribeVersion', 'Unknown')}")
        print(f"Library: {root.get('library', 'false')}")
        print(f"ID: {root.get('id', 'Unknown')}")
        print(f"Author: {root.get('authorName', 'Unknown')}")
        print(f"\n{'='*70}\n")
        
        # Count and display main sections
        sections = {}
        for child in root:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            sections[tag] = sections.get(tag, 0) + 1
        
        print("CATALOG STRUCTURE:")
        for section, count in sections.items():
            print(f"  {section}: {count}")
        
        print(f"\n{'='*70}\n")
        
        # Display detailed information
        display_publications(root)
        display_cost_types(root)
        display_profile_types(root)
        display_category_entries(root)
        display_shared_rules(root)
        display_shared_profiles(root)
        display_shared_selection_entries(root)
        display_shared_selection_entry_groups(root)
        display_catalogue_links(root)
        
        return root
        
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        return None
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return None

def display_publications(root):
    """Display publication information"""
    publications = root.find('bs:publications', ns)
    if publications is not None:
        print("PUBLICATIONS:")
        for pub in publications.findall('bs:publication', ns):
            name = pub.get('name', 'Unnamed')
            pub_id = pub.get('id', 'Unknown')
            print(f"  • {name} (ID: {pub_id})")
        print()

def display_cost_types(root):
    """Display cost types"""
    cost_types = root.find('bs:costTypes', ns)
    if cost_types is not None:
        print("COST TYPES:")
        for cost in cost_types.findall('bs:costType', ns):
            name = cost.get('name', 'Unnamed')
            default = cost.get('defaultCostLimit', 'N/A')
            print(f"  • {name} (Default Limit: {default})")
        print()

def display_profile_types(root):
    """Display profile types with their characteristics"""
    profile_types = root.find('bs:profileTypes', ns)
    if profile_types is not None:
        print("PROFILE TYPES:")
        for ptype in profile_types.findall('bs:profileType', ns):
            name = ptype.get('name', 'Unnamed')
            print(f"  • {name}")
            char_types = ptype.find('bs:characteristicTypes', ns)
            if char_types is not None:
                for char in char_types.findall('bs:characteristicType', ns):
                    char_name = char.get('name', 'Unnamed')
                    print(f"      - {char_name}")
        print()

def display_category_entries(root):
    """Display category entries"""
    category_entries = root.find('bs:categoryEntries', ns)
    if category_entries is not None:
        categories = list(category_entries.findall('bs:categoryEntry', ns))
        print(f"CATEGORIES: ({len(categories)} total)")
        for i, cat in enumerate(categories[:30], 1):
            name = cat.get('name', 'Unnamed')
            hidden = cat.get('hidden', 'false')
            print(f"  {i}. {name} (Hidden: {hidden})")
        if len(categories) > 30:
            print(f"  ... and {len(categories) - 30} more categories")
        print()

def display_shared_rules(root):
    """Display shared rules"""
    shared_rules = root.find('bs:sharedRules', ns)
    if shared_rules is not None:
        rules = list(shared_rules.findall('bs:rule', ns))
        print(f"SHARED RULES: ({len(rules)} total)")
        for i, rule in enumerate(rules[:20], 1):
            name = rule.get('name', 'Unnamed')
            hidden = rule.get('hidden', 'false')
            description = rule.find('bs:description', ns)
            desc_text = description.text if description is not None and description.text else "No description"
            desc_preview = desc_text[:100] + "..." if len(desc_text) > 100 else desc_text
            print(f"  {i}. {name}")
            print(f"     {desc_preview}")
        if len(rules) > 20:
            print(f"  ... and {len(rules) - 20} more rules")
        print()

def display_shared_profiles(root):
    """Display shared profiles"""
    shared_profiles = root.find('bs:sharedProfiles', ns)
    if shared_profiles is not None:
        profiles = list(shared_profiles.findall('bs:profile', ns))
        print(f"SHARED PROFILES: ({len(profiles)} total)")
        for i, profile in enumerate(profiles[:15], 1):
            name = profile.get('name', 'Unnamed')
            ptype = profile.get('typeName', 'Unknown Type')
            print(f"  {i}. {name} ({ptype})")
            
            # Show characteristics
            characteristics = profile.find('bs:characteristics', ns)
            if characteristics is not None:
                char_data = []
                for char in characteristics.findall('bs:characteristic', ns):
                    char_name = char.get('name', '')
                    char_value = char.text or char.get('value', '')
                    if char_value:
                        char_data.append(f"{char_name}: {char_value}")
                if char_data:
                    print(f"     {' | '.join(char_data)}")
        if len(profiles) > 15:
            print(f"  ... and {len(profiles) - 15} more profiles")
        print()

def display_shared_selection_entries(root):
    """Display shared selection entries (units, weapons, etc.)"""
    shared_entries = root.find('bs:sharedSelectionEntries', ns)
    if shared_entries is not None:
        entries = list(shared_entries.findall('bs:selectionEntry', ns))
        print(f"SHARED SELECTION ENTRIES: ({len(entries)} total)")
        for i, entry in enumerate(entries[:25], 1):
            name = entry.get('name', 'Unnamed')
            entry_type = entry.get('type', 'Unknown')
            hidden = entry.get('hidden', 'false')
            
            # Get costs
            costs = entry.find('bs:costs', ns)
            cost_str = ""
            if costs is not None:
                cost_values = []
                for cost in costs.findall('bs:cost', ns):
                    cost_name = cost.get('name', '')
                    cost_value = cost.get('value', '0')
                    if float(cost_value) > 0:
                        cost_values.append(f"{cost_value} {cost_name}")
                if cost_values:
                    cost_str = f" - Cost: {', '.join(cost_values)}"
            
            print(f"  {i}. {name} [{entry_type}]{cost_str}")
            
            # Show any profiles
            profiles = entry.find('bs:profiles', ns)
            if profiles is not None:
                for profile in list(profiles.findall('bs:profile', ns))[:2]:
                    pname = profile.get('name', '')
                    ptype = profile.get('typeName', '')
                    print(f"     Profile: {pname} ({ptype})")
        
        if len(entries) > 25:
            print(f"  ... and {len(entries) - 25} more entries")
        print()

def display_shared_selection_entry_groups(root):
    """Display shared selection entry groups"""
    shared_groups = root.find('bs:sharedSelectionEntryGroups', ns)
    if shared_groups is not None:
        groups = list(shared_groups.findall('bs:selectionEntryGroup', ns))
        print(f"SHARED SELECTION ENTRY GROUPS: ({len(groups)} total)")
        for i, group in enumerate(groups[:15], 1):
            name = group.get('name', 'Unnamed')
            hidden = group.get('hidden', 'false')
            print(f"  {i}. {name}")
        if len(groups) > 15:
            print(f"  ... and {len(groups) - 15} more groups")
        print()

def display_catalogue_links(root):
    """Display catalogue links"""
    cat_links = root.find('bs:catalogueLinks', ns)
    if cat_links is not None:
        print("CATALOGUE LINKS:")
        for link in cat_links.findall('bs:catalogueLink', ns):
            name = link.get('name', 'Unnamed')
            target_id = link.get('targetId', 'Unknown')
            link_type = link.get('type', 'Unknown')
            print(f"  • {name} (Type: {link_type}, Target: {target_id})")
        print()

def convert_to_json(filepath, output_file=None):
    """
    Convert a BattleScribe .cat file to JSON format
    """
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Extract namespace if present
        global ns
        ns = {'bs': 'http://www.battlescribe.net/schema/catalogueSchema'}
        if root.tag.startswith('{'):
            ns_url = root.tag.split('}')[0].strip('{')
            ns = {'bs': ns_url}
        
        # Build JSON structure
        catalog_data = {
            'metadata': {
                'name': root.get('name', 'Unknown'),
                'id': root.get('id', 'Unknown'),
                'gameSystemId': root.get('gameSystemId', 'Unknown'),
                'revision': root.get('revision', 'Unknown'),
                'battleScribeVersion': root.get('battleScribeVersion', 'Unknown'),
                'library': root.get('library', 'false'),
                'authorName': root.get('authorName', 'Unknown')
            },
            'publications': [],
            'costTypes': [],
            'profileTypes': [],
            'categories': [],
            'sharedRules': [],
            'sharedProfiles': [],
            'selectionEntries': [],
            'selectionEntryGroups': [],
            'catalogueLinks': []
        }
        
        # Parse publications
        publications = root.find('bs:publications', ns)
        if publications is not None:
            for pub in publications.findall('bs:publication', ns):
                catalog_data['publications'].append({
                    'id': pub.get('id', ''),
                    'name': pub.get('name', '')
                })
        
        # Parse cost types
        cost_types = root.find('bs:costTypes', ns)
        if cost_types is not None:
            for cost in cost_types.findall('bs:costType', ns):
                catalog_data['costTypes'].append({
                    'id': cost.get('id', ''),
                    'name': cost.get('name', ''),
                    'defaultCostLimit': cost.get('defaultCostLimit', '-1')
                })
        
        # Parse profile types
        profile_types = root.find('bs:profileTypes', ns)
        if profile_types is not None:
            for ptype in profile_types.findall('bs:profileType', ns):
                characteristics = []
                char_types = ptype.find('bs:characteristicTypes', ns)
                if char_types is not None:
                    for char in char_types.findall('bs:characteristicType', ns):
                        characteristics.append({
                            'id': char.get('id', ''),
                            'name': char.get('name', '')
                        })
                catalog_data['profileTypes'].append({
                    'id': ptype.get('id', ''),
                    'name': ptype.get('name', ''),
                    'characteristics': characteristics
                })
        
        # Parse categories
        category_entries = root.find('bs:categoryEntries', ns)
        if category_entries is not None:
            for cat in category_entries.findall('bs:categoryEntry', ns):
                catalog_data['categories'].append({
                    'id': cat.get('id', ''),
                    'name': cat.get('name', ''),
                    'hidden': cat.get('hidden', 'false')
                })
        
        # Parse shared rules
        shared_rules = root.find('bs:sharedRules', ns)
        if shared_rules is not None:
            for rule in shared_rules.findall('bs:rule', ns):
                description = rule.find('bs:description', ns)
                catalog_data['sharedRules'].append({
                    'id': rule.get('id', ''),
                    'name': rule.get('name', ''),
                    'hidden': rule.get('hidden', 'false'),
                    'description': description.text if description is not None else ''
                })
        
        # Parse shared profiles
        shared_profiles = root.find('bs:sharedProfiles', ns)
        if shared_profiles is not None:
            for profile in shared_profiles.findall('bs:profile', ns):
                characteristics = []
                char_list = profile.find('bs:characteristics', ns)
                if char_list is not None:
                    for char in char_list.findall('bs:characteristic', ns):
                        characteristics.append({
                            'name': char.get('name', ''),
                            'value': char.text or ''
                        })
                
                catalog_data['sharedProfiles'].append({
                    'id': profile.get('id', ''),
                    'name': profile.get('name', ''),
                    'typeName': profile.get('typeName', ''),
                    'hidden': profile.get('hidden', 'false'),
                    'characteristics': characteristics
                })
        
        # Parse shared selection entries (units, weapons, etc.)
        shared_entries = root.find('bs:sharedSelectionEntries', ns)
        if shared_entries is not None:
            for entry in shared_entries.findall('bs:selectionEntry', ns):
                # Get costs
                costs = []
                cost_list = entry.find('bs:costs', ns)
                if cost_list is not None:
                    for cost in cost_list.findall('bs:cost', ns):
                        costs.append({
                            'name': cost.get('name', ''),
                            'typeId': cost.get('typeId', ''),
                            'value': float(cost.get('value', '0'))
                        })
                
                # Get profiles
                profiles = []
                profile_list = entry.find('bs:profiles', ns)
                if profile_list is not None:
                    for profile in profile_list.findall('bs:profile', ns):
                        characteristics = []
                        char_list = profile.find('bs:characteristics', ns)
                        if char_list is not None:
                            for char in char_list.findall('bs:characteristic', ns):
                                characteristics.append({
                                    'name': char.get('name', ''),
                                    'value': char.text or ''
                                })
                        
                        profiles.append({
                            'id': profile.get('id', ''),
                            'name': profile.get('name', ''),
                            'typeName': profile.get('typeName', ''),
                            'characteristics': characteristics
                        })
                
                # Get infoLinks (references to shared rules/profiles)
                info_links = []
                info_link_list = entry.find('bs:infoLinks', ns)
                if info_link_list is not None:
                    for info_link in info_link_list.findall('bs:infoLink', ns):
                        info_links.append({
                            'id': info_link.get('id', ''),
                            'name': info_link.get('name', ''),
                            'type': info_link.get('type', ''),
                            'targetId': info_link.get('targetId', ''),
                            'hidden': info_link.get('hidden', 'false')
                        })
                
                catalog_data['selectionEntries'].append({
                    'id': entry.get('id', ''),
                    'name': entry.get('name', ''),
                    'type': entry.get('type', ''),
                    'hidden': entry.get('hidden', 'false'),
                    'costs': costs,
                    'profiles': profiles,
                    'infoLinks': info_links
                })
        
        # Parse shared selection entry groups
        shared_groups = root.find('bs:sharedSelectionEntryGroups', ns)
        if shared_groups is not None:
            for group in shared_groups.findall('bs:selectionEntryGroup', ns):
                # Extract nested selectionEntries from the group
                group_entries = []
                entries_list = group.find('bs:selectionEntries', ns)
                if entries_list is not None:
                    for entry in entries_list.findall('bs:selectionEntry', ns):
                        # Extract profiles
                        profiles = []
                        profile_list = entry.find('bs:profiles', ns)
                        if profile_list is not None:
                            for profile in profile_list.findall('bs:profile', ns):
                                characteristics = []
                                char_list = profile.find('bs:characteristics', ns)
                                if char_list is not None:
                                    for char in char_list.findall('bs:characteristic', ns):
                                        characteristics.append({
                                            'name': char.get('name', ''),
                                            'value': char.text or ''
                                        })
                                profiles.append({
                                    'id': profile.get('id', ''),
                                    'name': profile.get('name', ''),
                                    'typeName': profile.get('typeName', ''),
                                    'characteristics': characteristics
                                })
                        
                        group_entries.append({
                            'id': entry.get('id', ''),
                            'name': entry.get('name', ''),
                            'type': entry.get('type', ''),
                            'profiles': profiles
                        })
                
                if group.get('name') == 'Detachment':
                    print(f"  ✓ Extracted {len(group_entries)} detachments from '{group.get('name')}' group")
                
                catalog_data['selectionEntryGroups'].append({
                    'id': group.get('id', ''),
                    'name': group.get('name', ''),
                    'hidden': group.get('hidden', 'false'),
                    'selectionEntries': group_entries
                })
        
        # Parse catalogue links
        cat_links = root.find('bs:catalogueLinks', ns)
        if cat_links is not None:
            for link in cat_links.findall('bs:catalogueLink', ns):
                catalog_data['catalogueLinks'].append({
                    'id': link.get('id', ''),
                    'name': link.get('name', ''),
                    'targetId': link.get('targetId', ''),
                    'type': link.get('type', '')
                })
        
        # Output JSON
        json_output = json.dumps(catalog_data, indent=2, ensure_ascii=False)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"JSON data written to {output_file}")
        else:
            print(json_output)
        
        return catalog_data
        
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        return None
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python catConvert.py <path_to_cat_file> [--json] [-o output.json]")
        print("Example: python catConvert.py army_catalog.cat")
        print("Example: python catConvert.py army_catalog.cat --json")
        print("Example: python catConvert.py army_catalog.cat --json -o output.json")
    else:
        cat_file = sys.argv[1]
        
        # Check for JSON output flag
        if '--json' in sys.argv:
            output_file = None
            if '-o' in sys.argv:
                try:
                    output_index = sys.argv.index('-o')
                    output_file = sys.argv[output_index + 1]
                except (IndexError, ValueError):
                    print("Error: -o flag requires an output filename")
                    sys.exit(1)
            convert_to_json(cat_file, output_file)
        else:
            read_cat_file(cat_file)
