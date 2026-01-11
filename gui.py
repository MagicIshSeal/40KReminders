import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from pathlib import Path
import sys
from io import StringIO

from rosterParser import RosterParser
from catalog_manager import CatalogDownloader
from reminders import UnitReminder

class RosterReminderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Warhammer 40K Roster Reminders")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Variables
        self.roster_file = tk.StringVar()
        self.status_text = tk.StringVar(value="Ready to process roster")
        self.roster = None
        self.reminder = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Warhammer 40K Roster Reminders", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # File selection frame
        file_frame = ttk.LabelFrame(main_frame, text="Select Roster File", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="Roster File:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Entry(file_frame, textvariable=self.roster_file, state='readonly').grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(file_frame, text="Browse...", command=self.browse_file).grid(
            row=0, column=2, padx=(5, 0))
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        self.process_btn = ttk.Button(button_frame, text="Process Roster", 
                                      command=self.process_roster, state='disabled')
        self.process_btn.grid(row=0, column=0, padx=5)
        
        self.export_btn = ttk.Button(button_frame, text="Export to PDF", 
                                     command=self.export_pdf, state='disabled')
        self.export_btn.grid(row=0, column=1, padx=5)
        
        ttk.Button(button_frame, text="Clear", command=self.clear_output).grid(
            row=0, column=2, padx=5)
        
        # Output area
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="10")
        output_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, 
                                                      height=20, font=('Consolas', 9))
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(status_frame, textvariable=self.status_text, 
                                      relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.grid(row=0, column=1, padx=(5, 0), sticky=tk.E)
        
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select Roster File",
            filetypes=[
                ("BattleScribe Rosters", "*.ros *.rosz"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.roster_file.set(filename)
            self.process_btn['state'] = 'normal'
            self.status_text.set(f"Ready to process: {Path(filename).name}")
            self.log_output(f"Selected file: {filename}\n")
    
    def log_output(self, message):
        self.output_text.insert(tk.END, message)
        self.output_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_output(self):
        self.output_text.delete(1.0, tk.END)
        
    def process_roster(self):
        # Disable buttons during processing
        self.process_btn['state'] = 'disabled'
        self.export_btn['state'] = 'disabled'
        self.progress.start(10)
        
        # Run processing in a separate thread to keep UI responsive
        thread = threading.Thread(target=self._process_roster_thread, daemon=True)
        thread.start()
    
    def _process_roster_thread(self):
        try:
            roster_file = self.roster_file.get()
            
            # Clear previous output
            self.root.after(0, lambda: self.output_text.delete(1.0, tk.END))
            
            self.root.after(0, lambda: self.status_text.set("Loading roster..."))
            self.root.after(0, lambda: self.log_output(f"Loading roster: {roster_file}\n"))
            
            # Parse roster
            self.roster = RosterParser(roster_file)
            
            # Get roster info
            army_name = self.roster.get_army_name()
            detachment = self.roster.get_detachment()
            units = self.roster.get_units()
            
            # Display roster summary
            summary = self.roster.get_summary()
            self.root.after(0, lambda: self.log_output(f"\n{summary}\n\n"))
            
            if not units:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", "No units found in roster."))
                return
            
            # Download game system
            self.root.after(0, lambda: self.status_text.set("Downloading game system..."))
            self.root.after(0, lambda: self.log_output("Loading game system...\n"))
            
            downloader = CatalogDownloader()
            game_system_file = downloader.download_game_system()
            
            # Download catalog
            self.root.after(0, lambda: self.status_text.set(f"Downloading {army_name} catalog..."))
            self.root.after(0, lambda: self.log_output(f"Loading {army_name} catalog...\n"))
            
            json_file = downloader.download_catalog(army_name)
            
            if not json_file:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", f"Failed to load catalog for {army_name}"))
                return
            
            # Load reminder system
            self.root.after(0, lambda: self.status_text.set("Generating reminders..."))
            self.root.after(0, lambda: self.log_output("Generating reminders...\n\n"))
            
            self.reminder = UnitReminder(json_file, game_system_file)
            
            # Display reminders
            self._display_reminders_in_gui(units, detachment)
            
            self.root.after(0, lambda: self.status_text.set("✓ Reminders generated successfully!"))
            self.root.after(0, lambda: self.export_btn.configure(state='normal'))
            
        except Exception as e:
            error_msg = f"Error processing roster: {str(e)}"
            self.root.after(0, lambda: self.log_output(f"\n❌ {error_msg}\n"))
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root.after(0, lambda: self.status_text.set("Error processing roster"))
        
        finally:
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.process_btn.configure(state='normal'))
    
    def _display_reminders_in_gui(self, units, detachment_name):
        """Display reminders in the GUI output area"""
        output = []
        
        output.append("=" * 70)
        output.append("ROSTER REMINDERS")
        if detachment_name:
            output.append(f"DETACHMENT: {detachment_name}")
        output.append("=" * 70)
        output.append("")
        
        # Collect army-wide and detachment-wide rules
        army_rules = {}
        detachment_rules = {}
        
        if units:
            first_unit = units[0]
            unit_name = first_unit.get('customName') or first_unit.get('name')
            result = self.reminder.get_reminders(unit_name, detachment_name)
            
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
                    output.append("ARMY-WIDE RULES")
                    output.append("─" * 70)
                    output.append("")
                    
                    from reminders import PHASES
                    for phase in PHASES:
                        phase_reminders = army_rules.get(phase, []) + detachment_rules.get(phase, [])
                        if phase_reminders:
                            output.append(f"  📍 {phase.upper()}")
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
                                output.append(f"    {icon} {reminder['ability']}: {desc}")
                            output.append("")
                    
                    output.append("=" * 70)
                    output.append("")
        
        # Display units
        for unit_data in units:
            unit_name = unit_data.get('customName') or unit_data.get('name')
            count = unit_data.get('number', 1)
            composition = unit_data.get('composition', [])
            
            result = self.reminder.get_reminders(unit_name, detachment_name)
            
            if not result:
                continue
            
            output.append("")
            output.append("─" * 70)
            if count > 1:
                output.append(f"📋 {count}x {unit_name}")
            else:
                output.append(f"📋 {unit_name}")
            
            if composition:
                output.append(f"   └─ {', '.join(composition)}")
            output.append("─" * 70)
            
            # Display only unit-specific reminders
            has_reminders = False
            from reminders import PHASES
            for phase in PHASES:
                if phase in result['reminders'] and result['reminders'][phase]:
                    unit_specific = [r for r in result['reminders'][phase] 
                                   if r.get('source') not in ['army_rule', 'army_ability', 'detachment']]
                    
                    if unit_specific:
                        has_reminders = True
                        output.append("")
                        output.append(f"  📍 {phase.upper()}")
                        for reminder in unit_specific:
                            desc = reminder['description'].replace('**', '').replace('^^', '')
                            if len(desc) > 150:
                                desc = desc[:147] + "..."
                            desc = desc.replace('\n', ' ').replace('  ', ' ')
                            output.append(f"    ⚡ {reminder['ability']}: {desc}")
            
            # Always active abilities
            if "Always Active" in result['reminders'] and result['reminders']['Always Active']:
                if has_reminders:
                    output.append("")
                ability_names = [r['ability'] for r in result['reminders']['Always Active']]
                output.append(f"  📌 Passive: {', '.join(ability_names)}")
            
            if not has_reminders and not result['reminders'].get('Always Active'):
                output.append("  No unit-specific abilities")
        
        output.append("")
        output.append("=" * 70)
        output.append("")
        
        # Display in GUI
        output_str = "\n".join(output)
        self.root.after(0, lambda: self.log_output(output_str))
    
    def export_pdf(self):
        if not self.roster or not self.reminder:
            messagebox.showerror("Error", "Please process a roster first")
            return
        
        # Ask for save location
        default_name = Path(self.roster_file.get()).stem + "_reminders.pdf"
        filename = filedialog.asksaveasfilename(
            title="Save PDF As",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            self.status_text.set("Exporting to PDF...")
            self.progress.start(10)
            
            units = self.roster.get_units()
            detachment = self.roster.get_detachment()
            army_name = self.roster.get_army_name()
            
            result = self.reminder.export_roster_to_pdf(units, detachment, army_name, filename)
            
            if result:
                self.log_output(f"\n✓ PDF exported to: {filename}\n")
                self.status_text.set(f"✓ PDF saved: {Path(filename).name}")
                messagebox.showinfo("Success", f"PDF exported successfully!\n\n{filename}")
            else:
                self.status_text.set("Failed to export PDF")
                messagebox.showerror("Error", "Failed to export PDF")
                
        except Exception as e:
            error_msg = f"Error exporting PDF: {str(e)}"
            self.log_output(f"\n❌ {error_msg}\n")
            messagebox.showerror("Error", error_msg)
            self.status_text.set("Error exporting PDF")
        
        finally:
            self.progress.stop()

def main():
    root = tk.Tk()
    app = RosterReminderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
