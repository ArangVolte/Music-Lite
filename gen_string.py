import os
import sys
import subprocess

# Gunakan nama file selain string.py
def install_dependencies():
    dependencies = [
        "tgcrypto",
        "git+https://github.com/ArangVolte/mod"
    ]
    for lib in dependencies:
        subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

try:
    from pyrogram import Client
except (ImportError, ModuleNotFoundError):
    install_dependencies()
    from pyrogram import Client

import asyncio

# Pastikan API ID dan Hash benar
API_ID = 1234567  
API_HASH = "abcdef1234567890"

async def main():
    try:
        async with Client(
            name="session_gen",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True
        ) as app:
            app.is_bot=False
            string_session = await app.export_session_string()
            await app.send_message("me", f"**String Session Berhasil Dibuat:**\n\n`{string_session}`")
            print("\n✅ Selesai! Cek Pesan Tersimpan di Telegram kamu.")
    except Exception as e:
        print(f"\n❌ Terjadi kesalahan: {e}")

if __name__ == "__main__":
    asyncio.run(main())
