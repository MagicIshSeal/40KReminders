import json
from reminders import UnitReminder
from catalog_manager import CatalogDownloader

def select_catalog():
    """Let user select a catalog"""
    downloader = CatalogDownloader()
    
    print("\nFetching available catalogs from GitHub...")
    catalogs = downloader.fetch_available_catalogs()
    
    if not catalogs:
        print("Failed to fetch catalogs. Please check your internet connection.")
        return None
    
    print(f"\nAvailable Armies ({len(catalogs)}):")
    print("-" * 70)
    for i, cat in enumerate(catalogs, 1):
        cached = "✓" if (downloader.cache_dir / cat['name'].replace('.cat', '.json')).exists() else " "
        print(f"  {cached} {i:2}. {cat['display_name']}")
    print("\n(✓ = Already downloaded)")
    
    while True:
        try:
            choice = input("\nSelect army number (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                return None
            
            idx = int(choice) - 1
            if 0 <= idx < len(catalogs):
                selected = catalogs[idx]['display_name']
                json_file = downloader.download_catalog(selected)
                return json_file
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a number.")
        except KeyboardInterrupt:
            return None

def interactive_mode():
    """Interactive mode for looking up unit reminders"""
    print("\n" + "="*70)
    print("40K REMINDERS - Interactive Mode")
    print("="*70)
    
    # Download game system once
    downloader = CatalogDownloader()
    print("Loading game system...")
    game_system_file = downloader.download_game_system()
    
    # Select catalog
    json_file = select_catalog()
    if not json_file:
        print("No catalog selected. Exiting.")
        return
    
    try:
        reminder = UnitReminder(json_file, game_system_file)
        print(f"\n✓ Loaded {len(reminder.units_cache)} units")
    except FileNotFoundError:
        print(f"Error: Could not load catalog file.")
        return
    except Exception as e:
        print(f"Error loading catalog: {e}")
        return
    
    print("\nCommands:")
    print("  - Enter unit name to see reminders")
    print("  - 'list' to see all units")
    print("  - 'switch' to change army")
    print("  - 'quit' or 'exit' to exit")
    print("="*70 + "\n")
    
    while True:
        try:
            user_input = input("Enter unit name (or command): ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if user_input.lower() == 'switch':
                print("\nSwitching army...")
                json_file = select_catalog()
                if json_file:
                    try:
                        reminder = UnitReminder(json_file, game_system_file)
                        print(f"\n✓ Loaded {len(reminder.units_cache)} units")
                    except Exception as e:
                        print(f"Error loading catalog: {e}")
                continue
            
            if user_input.lower() == 'list':
                reminder.list_all_units()
                continue
            
            reminder.display_reminders(user_input)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    interactive_mode()
