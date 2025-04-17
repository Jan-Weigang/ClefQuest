import os
import yaml
import json

# Get the absolute path of the 'files' directory inside utils
FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")

def load_yaml(filename):
    """Reads a YAML file from utils/files/ and returns its parsed content."""
    file_path = os.path.join(FILES_DIR, filename)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{filename}' not found in {FILES_DIR}")

    with open(file_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

def load_json(filename):
    """Reads a JSON file from utils/files/ and returns its parsed content."""
    file_path = os.path.join(FILES_DIR, filename)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{filename}' not found in {FILES_DIR}")

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)
