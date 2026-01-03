import json
import subprocess
from datetime import datetime
from pathlib import Path
import sys
import os

def get_config_path():
    # Check current directory
    path = Path("config/settings.json")
    if path.exists():
        return path
    
    # Check parent directory (if running from tools/)
    path = Path("../config/settings.json")
    if path.exists():
        return path
        
    return None

def load_config(path):
    with open(path, 'r') as f:
        return json.load(f)

def save_config(path, config):
    with open(path, 'w') as f:
        json.dump(config, f, indent=4)

def increment_version(version_str):
    try:
        # Strip 'v' if present
        clean_ver = version_str.lstrip('v')
        parts = clean_ver.split('.')
        if len(parts) < 3:
            # Handle short versions like 1.0
            while len(parts) < 3:
                parts.append('0')
                
        major, minor, patch = map(int, parts)
        patch += 1
        return f"{major}.{minor}.{patch}"
    except Exception as e:
        print(f"Warning: Could not parse version '{version_str}': {e}. Resetting to 0.1.0")
        return "0.1.0"

def run_git_commands(version):
    commands = [
        ["git", "add", "."],
        ["git", "commit", "-m", f"Release version {version}"],
        ["git", "push"]
    ]
    
    for cmd in commands:
        print(f"Running: {' '.join(cmd)}")
        try:
            # We don't check=True for everything because git status might be clean
            result = subprocess.run(cmd, text=True, capture_output=True)
            if result.returncode != 0:
                print(f"Command failed (or nothing to do): {result.stderr}")
            else:
                print(result.stdout)
        except Exception as e:
            print(f"Execution error: {e}")

def update_version_history(version, date, ai_ide="TRAE"):
    """
    Append new version to Version_History.md
    """
    history_path = Path("Version_History.md")
    if not history_path.exists():
        # Try finding it relative to script if run from tools/
        history_path = Path("../Version_History.md")
        
    if not history_path.exists():
        print("Warning: Version_History.md not found. Creating new one.")
        with open("Version_History.md", "w") as f:
            f.write("# Version History\n\n| Version | Date | Description | AI IDE |\n|:---:|:---:|:---|:---:|\n")
        history_path = Path("Version_History.md")

    new_line = f"| **v{version}** | {date} | Auto-release update | {ai_ide} |\n"
    
    try:
        with open(history_path, "a") as f:
            f.write(new_line)
        print(f"Updated {history_path}")
    except Exception as e:
        print(f"Failed to update history: {e}")

def main():
    print("Starting release process...")
    
    config_path = get_config_path()
    if not config_path:
        print("Error: config/settings.json not found in current or parent directory.")
        sys.exit(1)
        
    print(f"Using config file: {config_path}")
    
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"Failed to load config: {e}")
        return

    current_version = config.get("local_dev_version", "0.0.0")
    new_version = increment_version(current_version)
    today = datetime.now().strftime("%Y-%m-%d")
    
    print(f"Updating version: {current_version} -> {new_version}")
    print(f"Updating date: {today}")
    
    config["local_dev_version"] = new_version
    config["local_dev_date"] = today
    config["last_version_github"] = f"v{new_version}"
    
    save_config(config_path, config)
    print("Settings updated.")
    
    # Update Version History
    ai_ide = config.get("dev_ai_ide", "TRAE")
    update_version_history(new_version, today, ai_ide)

    run_git_commands(new_version)
    print("Release process finished.")

if __name__ == "__main__":
    main()
