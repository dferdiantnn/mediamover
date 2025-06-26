# Telegram Media Mover

Sebuah skrip Python otomatis untuk memindahkan (menyedot) media (gambar dan video) baru dari grup-grup Telegram yang kamu tentukan ke channel Telegram pribadi kamu. **Dibangun menggunakan pustaka `Telethon`**, skrip ini dirancang agar mudah digunakan dengan antarmuka CLI yang interaktif.

## ✨ Fitur Utama

* **Pemindahan Media Otomatis:** Secara otomatis mendeteksi dan memindahkan media (gambar & video) baru dari grup sumber ke channel tujuan.
* **Konfigurasi Interaktif:** Pengaturan script dapat diubah dengan mudah melalui menu interaktif di terminal, tanpa perlu mengedit kode Python secara langsung.
* **Penyimpanan Pengaturan Persisten:** Semua konfigurasi (API ID, API Hash, daftar grup, channel tujuan) disimpan secara otomatis di file `config.json` sehingga tidak perlu diatur ulang setiap kali script dijalankan.
* **Manajemen Grup Sumber yang Cerdas:**
    * Dukungan untuk memantau **banyak grup sumber** sekaligus.
    * Mampu menampilkan **nama asli grup/channel** di menu pengaturan untuk memudahkan identifikasi.
    * Deteksi otomatis format ID (`-100` atau non-`-100`) saat menambahkan grup/channel.
    * Fitur tambah dan hapus ID grup sumber dengan mudah.
* **Log yang Bersih & Informatif:** Output terminal dirampingkan untuk memberikan informasi status yang jelas tanpa terlalu banyak detail teknis.
* **Tampilan CLI yang Menarik:** Dilengkapi dengan ASCII art kustom dan animasi loading (spinner) untuk pengalaman pengguna yang lebih baik.
* **Penanganan Error Robust:** Meliputi penanganan `FloodWaitError` (jeda otomatis saat deteksi spam Telegram), `AuthKeyUnregisteredError` (pembersihan sesi otomatis), dan validasi ID.
* **Didesain untuk Berjalan Persisten:** Dapat dengan mudah dijalankan di *background* menggunakan `tmux` atau `screen` di server Linux.

## 🚀 Cara Memulai

### Prasyarat

* Python 3.8 atau lebih tinggi.
* `pip` (manajer paket Python).
* Koneksi internet yang stabil.
* Akun Telegram dengan:
    * **API ID & API Hash:** Dapatkan dari [my.telegram.org](https://my.telegram.org/).
    * **Keanggunaan di Grup Sumber:** Akun Telegram yang kamu gunakan harus menjadi anggota dari semua grup/channel sumber yang ingin kamu pantau.
    * **Izin Mengirim Pesan:** Akun Telegram kamu harus memiliki izin untuk mengirim pesan ke channel tujuan.

### Instalasi

1.  **Clone repositori ini:**
    ```bash
    git clone [https://github.com/USERNAME_KAMU/NAMA_REPO_KAMU.git](https://github.com/USERNAME_KAMU/NAMA_REPO_KAMU.git)
    cd NAMA_REPO_KAMU # Ganti dengan nama folder repositori kamu
    ```
    *(Catatan: Jika ini belum di GitHub, langkah ini opsional. Kamu bisa langsung ke `cd ~/telegram_scripts` jika scriptnya ada di sana)*

2.  **Navigasi ke direktori script:**
    ```bash
    cd ~/telegram_scripts # Atau lokasi di mana mediamove.py berada
    ```

3.  **Buat dan aktifkan *virtual environment*:**
    Sangat disarankan untuk menginstal dependensi di lingkungan virtual untuk menghindari konflik.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **Instal dependensi Python (termasuk `Telethon`):**
    ```bash
    pip install telethon
    ```

### Konfigurasi Awal & Menjalankan Script

1.  **Jalankan script untuk pertama kali:**
    ```bash
    # Jika sudah menyiapkan launcher di ~/.local/bin/
    mediamover.sh 
    # Atau secara langsung:
    # python mediamove.py
    ```
2.  **Ikuti panduan di terminal:**
    * Script akan meminta Anda untuk **login Telegram** dengan nomor telepon dan kode verifikasi yang dikirim ke aplikasi Telegram Anda.
    * Setelah login, Anda akan masuk ke **Menu Utama**. Di sini Anda bisa:
        * Mengubah **API ID** dan **API Hash** (`Opsi 1` & `Opsi 2`).
        * **Menambah atau menghapus ID grup sumber** (`Opsi 3` & `Opsi 4`). Script akan mencoba mengambil nama grup untuk konfirmasi.
        * Mengubah **ID channel tujuan** (`Opsi 5`).
        * Setelah selesai mengatur, pilih **`Opsi 7. Keluar`** untuk menyimpan perubahan ke `config.json` dan keluar dari script.

3.  **Jalankan script lagi untuk memulai pemantauan:**
    ```bash
    mediamover.sh # Atau python mediamove.py
    ```
    Script akan menampilkan ringkasan informasi dan kemudian mulai beroperasi sebagai "perangkap" media baru.

### Menjalankan di Background (Persisten)

Untuk menjaga script tetap berjalan meskipun kamu menutup koneksi SSH (misalnya Termius), gunakan `tmux` atau `screen`.

#### Menggunakan `tmux` (Direkomendasikan)

1.  **Instal `tmux`:** `sudo apt install tmux`
2.  **Mulai sesi `tmux` baru:** `tmux new -s nama_sesi_kamu`
3.  **Di dalam sesi `tmux`:**
    ```bash
    cd ~/telegram_scripts
    source venv/bin/activate
    python mediamove.py # Atau mediamover.sh
    ```
4.  **Lepas (Detach) dari sesi `tmux`:** Tekan `Ctrl + B`, lalu `d`.
5.  **Untuk kembali ke sesi:** `tmux attach -t nama_sesi_kamu`
6.  **Untuk menghentikan:** Masuk ke sesi, lalu `Ctrl + C` untuk script, lalu `exit` untuk sesi `tmux`.

## ⚠️ Penting!

* Selalu patuhi **Kebijakan Privasi dan Ketentuan Layanan Telegram**. Penggunaan script ini sepenuhnya menjadi tanggung jawab Anda.
* Pastikan akun Telegram yang terhubung dengan script ini memiliki **akses dan izin yang benar** ke semua grup sumber dan channel tujuan. Error seperti `PeerIdInvalidError` atau `Invalid object ID` hampir selalu disebabkan oleh masalah izin/keanggotaan.
* Jika mengalami `TimeoutError` saat koneksi, periksa **koneksi internet** dan **pengaturan firewall** (misalnya UFW di Ubuntu) di perangkat Anda.

---
