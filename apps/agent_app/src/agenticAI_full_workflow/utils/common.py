import yaml
from pathlib import Path
from box import ConfigBox # Optional: Isse dictionary ['key'] ki jagah .key use ho jata hai

def read_yaml(path: Path) -> dict:
    try:
        with open(path, "r") as f:
            content = yaml.safe_load(f)
            return content
    except Exception as e:
        raise Exception(f"Error reading config file at {path}: {e}")