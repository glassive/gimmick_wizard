from taiko_gimmick import TaikoGimmick
from configparser import ConfigParser
import ctypes
from ctypes import wintypes
import os
from time import sleep
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

ctypes.windll.shcore.SetProcessDpiAwareness(1)
# tkinter blur fix

def create_default_config():
    """Create default config file if it doesn't exist."""
    conf = ConfigParser()
    conf.add_section('General')
    conf.set('General', 'songs_dir', '')
    
    conf.add_section('Barlines')
    conf.set('Barlines', 'don', '1')
    conf.set('Barlines', 'kat', '-5,-2,1,4,7')

    conf.add_section('Sliders')
    conf.set('Sliders', 'stack', '3')

    with open("config.txt", "w") as configfile:
        conf.write(configfile)
    return conf

try:
    conf = ConfigParser()
    if not conf.read("config.txt"):
        conf = create_default_config()
except Exception as e:
    conf = create_default_config()

# create config.txt file if it doesn't exist

class WindowFinder:
    def __init__(self):
        self.windows = []
    
    def callback(self, hwnd, _):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            self.windows.append((hwnd, buff.value))
        return True

def get_osu_windowname():
    """Find the osu! editor window and return its title"""
    finder = WindowFinder()
    enumWindows = ctypes.windll.user32.EnumWindows
    enumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    enumWindows(enumWindowsProc(finder.callback), 0)
    
    for hwnd, title in finder.windows:
        if title.startswith("osu!  - ") and title.endswith(".osu"):
            return title.split("osu!  - ")[1]
    return None
# windows wizardry i have no idea about

def find(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)

class GimmickWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gimmick Wizard")
        self.geometry("400x520")
        self.configure(
            padx=10,
            pady=10,
        )
        self.resizable(False, False)

        try:
            self.iconbitmap("icon.ico")
        except tk.TclError:
            pass

        self.wm_title("Gimmick Wizard")
        
        # Status variables
        self.current_file = tk.StringVar(value="No file loaded")
        self.bpm = tk.StringVar(value="120")
        self.selection = tk.StringVar()
        self.flash_kat = tk.BooleanVar(value=True)
        
        self.create_widgets()
        self.check_songs_folder()
        self.start_file_watcher()
    
    def create_widgets(self):
        # File status
        ttk.Label(self, text="Current file:").pack(anchor="w")
        ttk.Label(self, textvariable=self.current_file, wraplength=380).pack(fill="x")
        
        # Input frame
        input_frame = ttk.LabelFrame(self, text="Parameters", padding=5)
        input_frame.pack(fill="x", pady=10)
        
        ttk.Label(input_frame, text="Selection:").pack(anchor="w")
        ttk.Entry(input_frame, textvariable=self.selection).pack(fill="x")
        
        ttk.Label(input_frame, text="BPM:").pack(anchor="w")
        ttk.Entry(input_frame, textvariable=self.bpm).pack(fill="x")
        
        # Gimmick buttons
        buttons_frame = ttk.LabelFrame(self, text="Gimmicks", padding=5)
        buttons_frame.pack(fill="x", pady=10)
        
        ttk.Button(buttons_frame, text="Barlines", command=self.apply_barlines).pack(fill="x", pady=2)
        ttk.Button(buttons_frame, text="Sliders", command=self.apply_sliders).pack(fill="x", pady=2)

        flash_frame = ttk.Frame(buttons_frame)
        flash_frame.pack(fill="x", pady=2)
        ttk.Checkbutton(flash_frame, text="kat", variable=self.flash_kat).pack(side="left")
        ttk.Button(flash_frame, text="Flash Sliders", command=self.apply_flash).pack(fill="x")

        ttk.Button(buttons_frame, text="Slider obstruction").pack(fill="x", pady=2)
        ttk.Button(buttons_frame, text="Invisible note").pack(fill="x", pady=2)

    def check_songs_folder(self):
        if not conf.get('General', 'SONGS_DIR', fallback=None):
            self.find_osu_songs_folder()
    
    def find_osu_songs_folder(self):
        default_path = os.path.join(os.getenv('LOCALAPPDATA'), 'osu!', 'Songs')
        if os.path.exists(default_path):
            conf.set('General', 'SONGS_DIR', default_path)
        else:
            selected_folder = filedialog.askdirectory(title="Select osu! Songs folder")
            if selected_folder.endswith("osu!/Songs") and os.path.exists(selected_folder):
                conf.set('General', 'SONGS_DIR', selected_folder)
            else:
                messagebox.showerror("Error", "Invalid folder selected")
                self.quit()
                return
        
        with open("config.txt", "w") as configfile:
            conf.write(configfile)
    
    def start_file_watcher(self):
        self.after(250, self.check_file)
    
    def check_file(self):
        filename = get_osu_windowname()
        if filename != self.current_file.get():
            self.current_file.set(filename if filename else "No file loaded")
        self.after(250, self.check_file)
    
    def get_gimmick(self):
        filename = self.current_file.get()
        if filename == "No file loaded":
            messagebox.showwarning("Warning", "No file loaded")
            return None
        
        filepath = find(filename, conf.get("General", "SONGS_DIR"))
        return TaikoGimmick(filepath)
    
    def apply_barlines(self):
        gimmick = self.get_gimmick()
        if gimmick:
            try:
                gimmick.barline_gimmick(self.selection.get(), bpm=int(self.bpm.get()))
                messagebox.showinfo("Da-don!", f"Added {len(gimmick.interpret_selection(self.selection.get()))} barlines!")
                self.selection.set("")
            except ValueError as e:
                messagebox.showerror("Uh-oh :(", str(e))
    
    def apply_sliders(self):
        gimmick = self.get_gimmick()
        if gimmick:
            try:
                gimmick.slider_gimmick(self.selection.get(), bpm=int(self.bpm.get()))
                messagebox.showinfo("Da-don!", f"Added {len(gimmick.interpret_selection(self.selection.get()))} sliders!")
                self.selection.set("")
            except ValueError as e:
                messagebox.showerror("Uh-oh :(", str(e))

    def apply_flash(self):
        gimmick = self.get_gimmick()
        if gimmick:
            try:
                gimmick.slider_gimmick(
                    selection=self.selection.get(), 
                    bpm=int(self.bpm.get()),
                    stack=3,
                    flash_kat=self.flash_kat.get(),
                    shine=True
                )
                messagebox.showinfo("Da-don!", "Flash sliders applied!")
                self.selection.set("")
            except ValueError as e:
                messagebox.showerror("Uh-oh :(", str(e))

if __name__ == "__main__":
    app = GimmickWizard()
    app.mainloop()