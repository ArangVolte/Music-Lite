#!/bin/bash

echo "--- Menginstal library Python ---"
pip3 install python-dotenv
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
fi

echo ""
echo "--- Konfigurasi Bot (Akan disimpan ke .env) ---"
read -p "Masukkan API_ID: " API_ID
read -p "Masukkan API_HASH: " API_HASH
read -p "Masukkan BOT_TOKEN: " BOT_TOKEN
read -p "Masukkan SESSION_STRING: " SESSION_STRING

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

python3 main.py
