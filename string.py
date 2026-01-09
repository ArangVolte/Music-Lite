import os
import sys
import subprocess

def install_dependencies():
    dependencies = [
        "tgcrypto",
        "git+https://github.com/ArangVolte/mod"
    ]
    for lib in dependencies:
        subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

try:
    from pyrogram import Client
except ImportError:
    install_dependencies()
    from pyrogram import Client

import asyncio

API_ID = 1234567  
API_HASH = "abcdef1234567890"

async def main():
    async with Client(
        name="session_gen",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
        device_model="Laptop (Windows 11)",
        system_version="Desktop/PC",
        app_version="Pyrogram mod"
    ) as app:
        string_session = await app.export_session_string()
        
        text = (
            "**BERHASIL MEMBUAT STRING SESSION**\n\n"
            f"**Device:** `Laptop (Windows 11)`\n"
            f"**String:**\n`{string_session}`"
        )
        
        await app.send_message("me", text)
        print("Selesai! String session sudah dikirim ke Pesan Tersimpan.")

if __name__ == "__main__":
    asyncio.run(main())
