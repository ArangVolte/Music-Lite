# 🎵 Music-Lite

Bot musik Telegram modern yang dibangun dengan **Pyrogram** dan **PyTgCalls**. Mendukung pemutaran musik dan video di Voice Chat Grup maupun Channel dengan fitur pembuatan thumbnail otomatis.

## ✨ Fitur Unggulan

- **Pemutaran Multimedia**: Mendukung pencarian YouTube (Audio/Video), link langsung, dan file Telegram (Audio/Voice).
- **Thumbnail Generator**: Membuat gambar preview otomatis secara real-time yang menampilkan judul, pemohon, dan durasi.
- **Progress Bar Interaktif**: Keyboard inline yang diupdate otomatis untuk menunjukkan durasi lagu yang sedang berjalan.
- **Channel Streaming (CPlay)**: Hubungkan grup ke channel dan putar musik di Voice Chat Channel melalui grup.
- **Smart Queue**: Sistem antrean lagu yang stabil.
- **Admin Control**: Fitur Skip, Pause, Resume, Stop, Mute/Unmute, dan Volume (1-200%).
- **Userbot Integration**: Menggunakan akun user (Userbot) untuk kualitas streaming yang lebih stabil.

# 📚 Tutorial Deploy di Google Colab

## 🚀 Cara Instalasi Cepat di Colab

### Langkah 1: Buka Google Colab
1. Buka [Google Colab](https://colab.research.google.com/)
2. Buat notebook baru (`File` → `New Notebook`)

### Langkah 3: Clone Repository dan Jalankan
```bash
!git clone https://github.com/ArangVolte/Music-Lite && cd Music-Lite && bash start.sh
```

## 📝 Catatan Penting
1. **Waktu Runtime**: Colab memiliki batasan waktu runtime (maksimal 12 jam)
2. **Environment Variables**: Pastikan sudah mengisi file `.env` dengan kredensial yang valid sebelum menjalankan
3. **Resource**: Pastikan menggunakan GPU/TPU di Colab untuk performa lebih baik
4. **Persistensi Data**: Data di Colab akan hilang setelah runtime berakhir

## ⚠️ Troubleshooting
- Jika bot tidak berjalan, pastikan semua kredensial di `.env` sudah benar
- Untuk session string, jalankan generator session terlebih dahulu
- Pastikan semua dependencies terinstall dengan baik

## ⌨️ Perintah Bot

### Perintah Publik
| Perintah | Deskripsi |
|---|---|
| `/play [judul/link]` | Memutar musik/video di VC Grup |
| `/cplay [judul/link]` | Memutar musik/video di VC Channel |
| `/queue` | Melihat daftar antrean lagu |
| `/now` | Melihat detail lagu yang sedang diputar |

### Perintah Admin
| Perintah | Deskripsi |
|---|---|
| `/skip` | Melewati lagu ke antrean berikutnya |
| `/stop` | Menghentikan pemutaran dan menghapus antrean |
| `/pause` / `/resume` | Menjeda atau melanjutkan pemutaran |
| `/volume [1-200]` | Mengatur level suara |
| `/mute` / `/unmute` | Mematikan atau menghidupkan suara Userbot |
| `/connect [ID]` | Menghubungkan grup ke Channel |
| `/loop [mode]` | Mode loop: none, single, atau queue |

## 📝 Lisensi
Proyek ini dilisensikan di bawah **MIT License**.

Dibuat dengan ❤️ menggunakan **Pyrogram** dan **PyTgCalls**.