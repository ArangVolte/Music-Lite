#!/bin/bash

# 1. Install System Dependencies
echo "--- Menginstal dependensi sistem ---"
sudo apt-get update && sudo apt-get install -y fonts-noto-color-emoji

# 2. Install Python Library (Termasuk python-dotenv)
echo "--- Menginstal library Python ---"
pip3 install python-dotenv
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
fi

# 3. Input Variabel & Simpan ke file .env
echo ""
echo "--- Konfigurasi Bot (Akan disimpan ke .env) ---"
read -p "Masukkan API_ID: " API_ID
read -p "Masukkan API_HASH: " API_HASH
read -p "Masukkan BOT_TOKEN: " BOT_TOKEN
read -p "Masukkan SESSION_STRING: " SESSION_STRING

# Menulis ke file .env (menimpa file lama jika ada)
cat <<EOF > .env
API_ID=$API_ID
API_HASH=$API_HASH
BOT_TOKEN=$BOT_TOKEN
SESSION_STRING=$SESSION_STRING
EOF

echo "--------------------------------------"
echo "✅ File .env berhasil dibuat/diperbarui."
echo "🚀 Menjalankan bot..."
echo "--------------------------------------"

# 4. Jalankan Bot
python3 main.py
