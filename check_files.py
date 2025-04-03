import os
import json

def check_files():
    print("Checking required files...")
    
    # Check data directory
    if not os.path.exists("data"):
        print("❌ data directory not found")
        return False
    
    # Check JSON files
    json_files = ["translations.json", "services.json", "contacts.json"]
    for file in json_files:
        path = f"data/{file}"
        if os.path.exists(path):
            print(f"✅ {path} exists")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    json.load(f)
                print(f"  ✅ {file} is valid JSON")
            except Exception as e:
                print(f"  ❌ {file} is not valid JSON: {e}")
        else:
            print(f"❌ {path} not found")
    
    # Check videos directory
    if not os.path.exists("data/videos"):
        print("❌ data/videos directory not found")
        return False
    else:
        print("✅ data/videos directory exists")
    
    # Check video files
    video_files = [
        "location_ru.mp4",
        "location_uz.mp4",
        "clinic_ru.mp4",
        "clinic_uz.mp4"
    ]
    
    missing_videos = []
    for file in video_files:
        path = f"data/videos/{file}"
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024  # Size in KB
            print(f"✅ {path} exists ({size:.1f} KB)")
        else:
            print(f"❌ {path} not found")
            missing_videos.append(file)
    
    # Check .env file
    if os.path.exists(".env"):
        print("✅ .env file exists")
        try:
            with open(".env", 'r') as f:
                content = f.read()
                if "BOT_TOKEN" in content:
                    print("  ✅ BOT_TOKEN found in .env")
                else:
                    print("  ❌ BOT_TOKEN not found in .env")
                
                if "ADMIN_ID" in content:
                    print("  ✅ ADMIN_ID found in .env")
                else:
                    print("  ❌ ADMIN_ID not found in .env")
        except Exception as e:
            print(f"  ❌ Error reading .env: {e}")
    else:
        print("❌ .env file not found")
    
    print("\nSummary:")
    print("1. Make sure all JSON files exist and are valid")
    
    if missing_videos:
        print("\n2. Missing video files:")
        for video in missing_videos:
            print(f"   - {video}")
        print("   Please add these video files to the data/videos directory.")
        print("   Video files should be in MP4 format and not too large (under 50MB).")
    else:
        print("2. All required video files are present")
    
    print("3. Ensure .env file has BOT_TOKEN and ADMIN_ID")
    print("4. Run the bot with: python main.py")

if __name__ == "__main__":
    check_files() 