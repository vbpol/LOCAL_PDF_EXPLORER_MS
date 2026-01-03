from src.core.settings import Settings
import os

def test_settings_persistence():
    settings_file = "config/test_settings.json"
    
    # Clean up
    if os.path.exists(settings_file):
        os.remove(settings_file)
        
    # 1. Test Default Loading
    settings = Settings(settings_file)
    assert settings.config["last_version_github"] == ""
    assert settings.config["date_of_publication"] == ""
    assert settings.config["github_repository_url"] == ""
    
    # 2. Test Saving
    new_data = {
        "last_version_github": "v1.0.0",
        "date_of_publication": "2023-10-27",
        "github_repository_url": "https://github.com/user/repo"
    }
    settings.save_config(new_data)
    
    # 3. Test Reloading
    settings_reloaded = Settings(settings_file)
    assert settings_reloaded.config["last_version_github"] == "v1.0.0"
    assert settings_reloaded.config["date_of_publication"] == "2023-10-27"
    assert settings_reloaded.config["github_repository_url"] == "https://github.com/user/repo"
    
    print("Settings persistence verification passed!")
    
    # Clean up
    if os.path.exists(settings_file):
        os.remove(settings_file)

if __name__ == "__main__":
    test_settings_persistence()
