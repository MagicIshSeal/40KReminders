import json
from reminders import UnitReminder

def interactive_mode():
    """Interactive mode for looking up unit reminders"""
    print("\n" + "="*70)
    print("40K REMINDERS - Interactive Mode")
    print("="*70)
    print("Loading Space Marines catalog...")
    
    try:
        reminder = UnitReminder('space_marines.json')
        print(f"✓ Loaded {len(reminder.units_cache)} units")
    except FileNotFoundError:
        print("Error: space_marines.json not found!")
        print("Run: python catConvert.py 'Imperium - Space Marines.cat' --json -o space_marines.json")
        return
    
    print("\nCommands:")
    print("  - Enter unit name to see reminders")
    print("  - 'list' to see all units")
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
