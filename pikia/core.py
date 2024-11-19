from InquirerPy import inquirer
from InquirerPy.validator import PathValidator
import os

class PikIA:
    def __init__(self):
        self.directories = self._prompt_directories()
        self.recursive = inquirer.confirm(message="Scan directories recursively?", default=True).execute()
        self.model = "microsoft/Florence-2-large"

    def _prompt_directories(self):
        # Instructions
        print("Provide directories to scan for images")
        print("- Use arrows or tab to automplete")
        print("- Drag & Drop a directory to add")
        print("- Ctrl+C to end")

        # Prompt for directories
        directories = []
        keybindings = {
            "skip": [{"key": "c-c"}],
        }

        while True:
            new_dir = inquirer.filepath(
                message="Enter path to scan:",
                validate=PathValidator(is_dir=True, message="Input is not a directory"),
                only_directories=True,
                # FILTER NOTES
                # Need to concat `os.path.sep`: `os.path.abspath("C:")` -> `os.getcwd()`
                # Dont `os.path.join(e, os.path.sep)`: `os.path.join(".dir", os.path.sep)` -> `"\\"`
                filter=lambda e: os.path.abspath(e + os.path.sep if len(e) != 0 else ".")
                if e is not None
                else e,
                keybindings=keybindings,
                mandatory=(len(directories) == 0),
            ).execute()
            if new_dir is None:
                break
            directories.append(new_dir)
        
        # Remove duplicates
        directories = list(set(directories))

        return directories