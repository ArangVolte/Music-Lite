import os
import sys
import subprocess
import asyncio

def install_dependencies():
    dependencies = [
        "tgcrypto",
        "git+https://github.com/ArangVolte/mod"
    ]
    for lib in dependencies:
        subprocess.check_call([sys.executable, "-m", "pip", "install", lib, "--upgrade"])

try:
    from pyrogram import Client
except (ImportError, ModuleNotFoundError):
    install_dependencies()
    from pyrogram import Client

API_ID = 23688933  
API_HASH = "fb36db8f0482a909a320752f7d72abc6"

async def main():
    app = Client(
        name="session_gen",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
        device_model="Laptop (Windows 11)",
        system_version="Desktop/PC",
        app_version="Pyrogram mod"
    )
    
    app.is_bot = False 
    
    try:
        await app.start()
        string_session = await app.export_session_string()
        
        text = (
            "**BERHASIL MEMBUAT STRING SESSION**\n\n"
            "**Device:** `Laptop (Windows 11)`\n"
            f"**String:**\n`{string_session}`"
        )
        
        await app.send_message("me", text)
        print("\n✅ Berhasil! Cek Saved Messages.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if app.is_connected:
            await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
