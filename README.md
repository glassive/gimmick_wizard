# Taiko Gimmick Wizard

Built with PyInstaller. Uses only Python standard library (no external packages required).


## How to use

Upon launch, the program will either find your osu! songs folder automatically (if it is located in the default Windows install path), or you will be prompted to specify it yourself.
If anything goes wrong, you can manually edit `config.txt` and change the songs_dir value, for example:
```yaml
[General]
songs_dir = C:/Users/Username/AppData/Local/osu!/Songs
```

Using the program goes as follows:
- Open your map of choice in the editor
- Select the desired objects, copy the selection, then paste it in the `Selection` field
- Specify the BPM of that section
- Click the button corresponding to the gimmick you want to apply
- That's it!

For more advanced use, additional options are available in the `config.txt` file. Make sure to restart the program after making changes to the config.


## Building from source (for Windows)

Build requirements:
- Python >= 3.6

To build from the repo, run the following commands:
```batch
pip install pyinstaller
pyinstaller --noconsole --onefile --icon=icon.ico --name="Gimmick Wizard" use.py
copy icon.ico dist
```
