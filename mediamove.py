import asyncio
import json
import os
import sys
from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel, Channel, Chat, User
from telethon.errors.rpcerrorlist import PeerIdInvalidError, FloodWaitError, AuthKeyUnregisteredError

# --- File Konfigurasi ---
CONFIG_FILE = 'config.json'

# --- Default Konfigurasi ---
# Ini akan digunakan jika file config.json tidak ditemukan atau kosong.
# PENTING: Ubah nilai-nilai di bawah ini dengan data Anda yang sebenarnya,
# atau masukkan melalui menu interaktif saat script dijalankan.
default_config = {
    'api_id': 0, # GANTI DENGAN API ID ANDA dari my.telegram.org (angka)
    'api_hash': "", # GANTI DENGAN API HASH ANDA dari my.telegram.org (string)
    'session_name': 'my_telegram_session', # Nama file sesi untuk Telethon (contoh: my_telegram_session.session)
    'source_group_ids': [], # Daftar ID grup/channel sumber Anda (kosongkan jika belum ada)
    'target_channel_id': 0, # GANTI DENGAN ID channel tujuan Anda (harus angka, contoh: -1001234567890)
    'processed_message_ids_file_base': 'processed_media_ids' # Nama dasar untuk file ID pesan yang sudah diproses
}

# Variabel global untuk konfigurasi yang sedang aktif dan client
config = {}
client = None # Client akan diinisialisasi di main

# --- ASCII Art untuk Tampilan Pembuka ---
ASCII_ART = r"""
     _  __             _ _             _         
    | |/ _|           | (_)           | |        
  __| | |_ ___ _ __ __| |_  __ _ _ __ | |_ _ __  
 / _` |  _/ _ \ '__/ _` | |/ _` | '_ \| __| '_ \ 
| (_| | ||  __/ | | (_| | | (_| | | | | |_| | | |
 \__,_|_| \___|_|  \__,_|_|\__,_|_| |_|\__|_| |_|
                                                 
                                                 
v2.21 by Gemini AI & dferdiantn
"""

# --- Fungsi untuk Mengelola Konfigurasi ---
def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            try:
                config = json.load(f)
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
            except json.JSONDecodeError:
                print("[-] Error membaca config.json. Menggunakan konfigurasi default.")
                config = default_config.copy()
    else:
        print("[*] config.json tidak ditemukan. Membuat dengan konfigurasi default.")
        config = default_config.copy()
    save_config()

def save_config():
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    # print("[*] Konfigurasi disimpan ke config.json.") # Jangan terlalu sering print ini

# --- Fungsi untuk Mengelola ID Pesan yang Sudah Diproses (masih dipertahankan untuk jaga-jaga jika nanti diperlukan) ---
async def get_processed_ids(group_id):
    filename = f"{config['processed_message_ids_file_base']}_{group_id}.json"
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            print(f"[-] Error membaca file processed IDs untuk grup {group_id}. Membuat yang baru.")
            return set()
    return set()


async def save_processed_ids(processed_ids, group_id):
    filename = f"{config['processed_message_ids_file_base']}_{group_id}.json"
    with open(filename, 'w') as f:
        json.dump(list(processed_ids), f)

# --- Fungsi untuk Mengambil Info Nama Grup dan Channel dengan Deteksi ID Otomatis ---
async def get_group_channel_info(ids):
    info_list = []
    if client and client.is_connected():
        for item_id in ids:
            resolved_id = None
            resolved_name = None
            original_id_str = str(item_id) # Simpan dalam string untuk manipulasi

            # Coba ID asli dulu
            try:
                entity = await client.get_entity(item_id)
                resolved_id = item_id
                resolved_name = entity.title if hasattr(entity, 'title') else (entity.first_name if hasattr(entity, 'first_name') else f"ID Tanpa Nama: {item_id}")
            except (PeerIdInvalidError, ValueError, IndexError, AttributeError): # Tangkap AttributeError untuk kasus user yang tidak punya title
                # Jika gagal, coba dengan penyesuaian -100
                if isinstance(item_id, int):
                    # Coba tambahkan -100 jika positif dan tidak terlihat seperti sudah ada 100 di depannya
                    if item_id > 0 and not original_id_str.startswith('100'): 
                        try_id_negative_prefix = int(f"-100{item_id}")
                        try:
                            entity = await client.get_entity(try_id_negative_prefix)
                            resolved_id = try_id_negative_prefix
                            resolved_name = entity.title if hasattr(entity, 'title') else f"ID Tanpa Nama: {try_id_negative_prefix}"
                        except Exception:
                            pass # Gagal coba ini, lanjut ke coba yang lain
                    # Coba hapus -100 jika negatif dan mungkin grup lama
                    if resolved_id is None and item_id < 0 and original_id_str.startswith('-100'):
                        try_id_positive_suffix = int(original_id_str[4:]) # Hapus '-100'
                        try:
                            entity = await client.get_entity(try_id_positive_suffix)
                            resolved_id = try_id_positive_suffix
                            resolved_name = entity.title if hasattr(entity, 'title') else f"ID Tanpa Nama: {try_id_positive_suffix}"
                        except Exception:
                            pass # Gagal coba ini

            if resolved_id is not None:
                info_list.append({'id': resolved_id, 'name': resolved_name})
            else:
                info_list.append({'id': item_id, 'name': f"ID Tidak Valid/Tidak Dapat Diakses: {item_id}"})
                print(f"[-] Peringatan: Gagal mendapatkan info untuk ID {item_id}. Pastikan itu ID yang benar dan akun Anda anggota.")
    else:
        for item_id in ids:
            info_list.append({'id': item_id, 'name': f"ID: {item_id} (Nama Tidak Tersedia - Belum Terhubung)"})
    return info_list

# --- Fungsi Interaktif per Opsi Menu ---
async def change_api_id_interactive():
    print(f"\n--- UBAH API ID ---")
    print(f"  API ID Saat Ini: {config['api_id']}")
    new_api_id_str = input(f"[*] Masukkan API ID baru (kosongkan jika tidak berubah): ")
    if new_api_id_str:
        try:
            config['api_id'] = int(new_api_id_str)
            save_config()
            print("[+] API ID diperbarui.")
            print("[*] Untuk menerapkan perubahan API ID, Anda perlu me-restart script.")
        except ValueError:
            print("[-] API ID harus berupa angka. Tidak diubah.")
    input("Tekan Enter untuk kembali ke menu utama...")

async def change_api_hash_interactive():
    print(f"\n--- UBAH API HASH ---")
    print(f"  API Hash Saat Ini: {config['api_hash']}")
    new_api_hash = input(f"[*] Masukkan API Hash baru (kosongkan jika tidak berubah): ")
    if new_api_hash:
        config['api_hash'] = new_api_hash
        save_config()
        print("[+] API Hash diperbarui.")
        print("[*] Untuk menerapkan perubahan API Hash, Anda perlu me-restart script.")
    input("Tekan Enter untuk kembali ke menu utama...")

async def add_source_group_interactive():
    print("\n--- TAMBAH GRUP SUMBER ---")
    current_groups_info = await get_group_channel_info(config['source_group_ids'])
    print("Grup Sumber Terdaftar Saat Ini:")
    if not current_groups_info:
        print("  (Tidak ada grup terdaftar)")
    for info in current_groups_info:
        print(f"- ID: {info['id']} -> Nama: {info['name']}")

    new_group_input = input("[*] Masukkan ID Grup baru (pisahkan dengan koma jika lebih dari satu): ")
    new_ids = []
    for item in new_group_input.split(','):
        try:
            gid = int(item.strip())
            # Coba verifikasi ID dan dapatkan nama dengan deteksi otomatis
            temp_info = await get_group_channel_info([gid])
            if temp_info and temp_info[0]['name'] != f"ID Tidak Valid/Tidak Dapat Diakses: {gid}":
                resolved_gid = temp_info[0]['id']
                if resolved_gid not in config['source_group_ids']:
                    new_ids.append(resolved_gid)
                    print(f"[+] Grup ID {resolved_gid} ('{temp_info[0]['name']}') berhasil diverifikasi dan akan ditambahkan.")
                else:
                    print(f"[*] Grup ID {resolved_gid} ('{temp_info[0]['name']}') sudah ada.")
            else:
                print(f"[-] Gagal memverifikasi ID '{item.strip()}'. Pastikan ID benar dan akun Anda adalah anggota grup tersebut. Tidak ditambahkan.")
        except ValueError:
            print(f"[-] '{item.strip()}' bukan ID grup yang valid. Dilewati.")
    
    if new_ids:
        config['source_group_ids'].extend(new_ids)
        save_config()
        print(f"[+] {len(new_ids)} grup ditambahkan ke konfigurasi.")
    input("Tekan Enter untuk kembali ke menu utama...")

async def remove_source_group_interactive():
    print("\n--- HAPUS GRUP SUMBER ---")
    current_groups_info = await get_group_channel_info(config['source_group_ids'])
    print("Grup Sumber Terdaftar Saat Ini:")
    if not current_groups_info:
        print("  (Tidak ada grup terdaftar)")
        input("Tekan Enter untuk kembali ke menu utama...")
        return
    for idx, info in enumerate(current_groups_info):
        print(f"  {idx + 1}. ID: {info['id']} -> Nama: {info['name']}")

    remove_choice = input("[*] Masukkan nomor urut grup yang ingin dihapus, atau 'b' untuk batal: ").strip().lower()
    if remove_choice == 'b':
        input("Tekan Enter untuk kembali ke menu utama...")
        return

    try:
        idx_to_remove = int(remove_choice) - 1
        if 0 <= idx_to_remove < len(current_groups_info):
            removed_id = current_groups_info[idx_to_remove]['id']
            config['source_group_ids'].remove(removed_id)
            save_config()
            print(f"[+] Grup ID {removed_id} ('{current_groups_info[idx_to_remove]['name']}') dihapus.")
        else:
            print("[-] Nomor urut tidak valid.")
    except ValueError:
        print("[-] Input tidak valid. Masukkan nomor atau 'b'.")
    except Exception as e:
        print(f"[-] Terjadi kesalahan saat menghapus grup: {e}")
    input("Tekan Enter untuk kembali ke menu utama...")

async def change_target_channel_interactive():
    print(f"\n--- UBAH CHANNEL TUJUAN ---")
    target_channel_info = await get_group_channel_info([config['target_channel_id']])
    if target_channel_info and 'name' in target_channel_info[0]:
        print(f"  ID Channel Tujuan Saat Ini: {config['target_channel_id']} -> Nama: {target_channel_info[0]['name']}")
    else:
        print(f"  ID Channel Tujuan Saat Ini: {config['target_channel_id']}") # Fallback if name not found

    new_target_id_str = input("[*] Masukkan ID Channel Tujuan baru (kosongkan jika tidak berubah, pastikan ID valid): ")
    if new_target_id_str:
        try:
            new_id_int = int(new_target_id_str)
            # Coba verifikasi ID dan dapatkan nama dengan deteksi otomatis
            temp_info = await get_group_channel_info([new_id_int])
            if temp_info and temp_info[0]['name'] != f"ID Tidak Valid/Tidak Dapat Diakses: {new_id_int}":
                config['target_channel_id'] = temp_info[0]['id'] # Gunakan ID yang sudah di-resolve
                save_config()
                print(f"[+] ID Channel Tujuan diperbarui menjadi {temp_info[0]['id']} ('{temp_info[0]['name']}').")
            else:
                print(f"[-] Gagal memverifikasi ID '{new_target_id_str}'. Pastikan ID benar dan akun Anda dapat mengakses channel tersebut. Tidak diubah.")
        except ValueError:
            print("[-] ID Channel Tujuan harus berupa angka. Tidak diubah.")
    input("Tekan Enter untuk kembali ke menu utama...")

# --- Fungsi Loading Animation ---
async def spinner(message, stop_event):
    # Menggunakan titik yang bertambah dan menghilang secara berurutan
    spinner_chars = ['.  ', '.. ', '...', '   ']
    i = 0
    # Tambahkan buffer cukup besar untuk clear line
    clear_line_length = len(message) + 4 # 4 karena max len dari '...'
    
    while not stop_event.is_set():
        sys.stdout.write(f"\r{message}{spinner_chars[i % len(spinner_chars)]}")
        sys.stdout.flush()
        i = (i + 1) % len(spinner_chars) # Pastikan i tidak melebihi indeks spinner_chars
        await asyncio.sleep(0.3) # Jeda sedikit lebih lama agar transisi titik terlihat jelas

    sys.stdout.write('\r' + ' ' * clear_line_length + '\r') # Clear spinner line
    sys.stdout.flush()

# --- Fungsi Utama Menu ---
async def run_main_menu():
    running = True
    while running:
        # Tampilkan informasi akun dan grup di sini (akan di-refresh setiap kembali ke menu)
        me_user = await client.get_me()
        monitored_group_names_info = await get_group_channel_info(config['source_group_ids'])
        target_channel_name_info = await get_group_channel_info([config['target_channel_id']])

        # --- Informasi Akun dan Grup di Atas Menu ---
        print("\n" + "="*50)
        print("       INFORMASI MEDIA MOVER TELEGRAM")
        print("="*50)
        print(f"Akun Terhubung: {me_user.first_name} (@{me_user.username if me_user.username else 'N/A'})")
        print("\n--- Grup yang Dipantau ---")
        if not monitored_group_names_info:
            print("- (Belum ada grup sumber terdaftar)")
        else:
            for info in monitored_group_names_info: 
                print(f"- ID: {info['id']} -> Nama: {info['name']}")
        
        print("\n--- Channel Tujuan Media ---")
        if target_channel_name_info and 'name' in target_channel_name_info[0]:
            print(f"- ID: {config['target_channel_id']} -> Nama: {target_channel_name_info[0]['name']}")
        else:
            print(f"- ID: {config['target_channel_id']} (Nama Channel Tidak Dikenal/Tidak Dapat Diakses)")
        print("="*50 + "\n")
        # --- Akhir Informasi ---

        print("\n--- MENU UTAMA MEDIA MOVER TELEGRAM ---")
        print("  1. Ubah API ID")
        print("  2. Ubah API Hash")
        print("  3. Tambah ID Grup Sumber")
        print("  4. Hapus ID Grup Sumber")
        print("  5. Ubah ID Channel Tujuan")
        print("  6. Mulai Memantau & Proses Media") # Mengubah nomor menjadi 6
        print("  7. Keluar") # Mengubah nomor menjadi 7
        
        choice = input("Pilihan Anda (1-7): ").strip() # Pilihan 1-7 sekarang

        if choice == '1':
            await change_api_id_interactive()
        elif choice == '2':
            await change_api_hash_interactive()
        elif choice == '3':
            await add_source_group_interactive()
        elif choice == '4':
            await remove_source_group_interactive()
        elif choice == '5':
            await change_target_channel_interactive()
        elif choice == '6': # Opsi ini sekarang untuk mulai monitoring
            running = False # Keluar dari menu loop untuk mulai monitoring
        elif choice == '7': # Opsi ini sekarang untuk keluar
            print("[*] Keluar dari script. Sampai jumpa!")
            if client and client.is_connected():
                await client.disconnect()
            exit()
        else:
            print("[-] Pilihan tidak valid. Silakan coba lagi.")
            input("Tekan Enter untuk melanjutkan...")

# --- Fungsi Utama Proses Monitoring ---
async def start_monitoring_process():
    # Fetch final names for monitoring message
    me_user = await client.get_me() # Ambil ulang data user
    monitored_group_names_info = await get_group_channel_info(config['source_group_ids'])
    target_channel_name_info = await get_group_channel_info([config['target_channel_id']])
    
    # Cetak ulang status pemantauan sebelum benar-benar memulai
    print(f"\n--- STATUS PEMANTAUAN FINAL ---")
    print(f"Akun Terhubung: {me_user.first_name} (@{me_user.username if me_user.username else 'N/A'})")
    
    print("Grup yang Dipantau:")
    if not monitored_group_names_info:
        print("- (Tidak ada grup terdaftar. Pemantauan pesan baru tidak akan aktif.)")
    else:
        for info in monitored_group_names_info:
            print(f"- ID: {info['id']} -> Nama: {info['name']}")
    
    print("Channel Tujuan:")
    if target_channel_name_info and 'name' in target_channel_name_info[0]:
        print(f"- ID: {config['target_channel_id']} -> Nama: {target_channel_name_info[0]['name']}")
    else:
        print(f"- ID: {config['target_channel_id']} (Nama Channel Tidak Dikenal/Tidak Dapat Diakses)")
    print("-------------------------------\n")

    # Fitur pengambilan media lama dihapus, jadi tidak ada panggilan fetch_all_historical_media

    # Menentukan handler untuk pesan baru yang masuk ke grup sumber
    if config['source_group_ids']:
        @client.on(events.NewMessage(chats=config['source_group_ids']))
        async def new_message_handler(event):
            if event.media:
                chat_title = event.chat.title if hasattr(event.chat, 'title') else f"Grup ID: {event.chat_id}"
                # Menentukan tipe media untuk pernyataan yang lebih jelas
                media_type = "gambar" if event.photo else ("video" if event.video else "media lain")
                
                print(f"[*] Menemukan {media_type} baru dari grup '{chat_title}' (ID: {event.chat_id}).") # Pesan lebih sederhana
                try:
                    target_peer = PeerChannel(channel_id=config['target_channel_id'])
                    await client.send_message(target_peer, file=event.media, message=event.text if event.text else None)
                    print(f"[+] Berhasil memindahkan {media_type} baru ke channel {config['target_channel_id']}.")
                except FloodWaitError as e:
                    print(f"[-] Terdeteksi FloodWaitError ({e.seconds} detik). Menunggu...")
                    await asyncio.sleep(e.seconds + 5)
                except Exception as e:
                    print(f"[-] Gagal memindahkan {media_type} baru dari '{chat_title}': {e}")
            else:
                chat_title = event.chat.title if hasattr(event.chat, 'title') else f"Grup ID: {event.chat_id}"
                # print(f"[*] Pesan baru tanpa media di grup '{chat_title}' (ID: {event.chat_id}). Abaikan.") # Terlalu verbose saat monitoring

    else:
        print("[*] Tidak ada grup sumber yang terdaftar, pemantauan pesan baru tidak aktif.")


    print("[*] Script berjalan sebagai 'perangkap' media baru. Tekan Ctrl+C untuk menghentikan.")
    await client.run_until_disconnected()

# --- Fungsi Main Utama ---
async def main():
    global client
    load_config() # Muat konfigurasi dari file

    # Cetak ASCII Art di awal
    print(ASCII_ART)
    print("\n[!] Memulai Media Mover Telegram...")
    
    # Inisialisasi client lebih awal untuk digunakan di menu
    client = TelegramClient(config['session_name'], config['api_id'], config['api_hash'])

    # Sambungkan dan otorisasi client sekali di awal
    stop_spinner_event = asyncio.Event()
    spinner_task = None
    try:
        # Pengecekan awal API ID dan Hash
        if config['api_id'] == 0 or config['api_hash'] == "":
            print("[-] API ID atau API Hash belum dikonfigurasi. Silakan atur melalui menu.")
            # Jangan memulai spinner jika belum dikonfigurasi
        else:
            spinner_task = asyncio.create_task(spinner("Menghubungkan ke Telegram", stop_spinner_event))

        await client.connect()
        stop_spinner_event.set() # Stop spinner
        if not await client.is_user_authorized():
            # If not authorized, prompt for phone and code outside spinner, then restart spinner for sign_in
            # Clear previous spinner message before asking for input
            sys.stdout.write('\r' + ' ' * (len("Menghubungkan ke Telegram") + 2 + 3) + '\r') # 3 karena max len dari '...'
            sys.stdout.flush()
            phone = input('Masukkan nomor telepon Telegram Anda (contoh: +628123456789): ')
            await client.send_code_request(phone)
            code = input('Masukkan kode verifikasi dari Telegram: ')
            stop_spinner_event_auth = asyncio.Event() # New event for sign_in spinner
            spinner_task_auth = asyncio.create_task(spinner("Mengautentikasi akun", stop_spinner_event_auth))
            await client.sign_in(phone, code)
            stop_spinner_event_auth.set() # Stop spinner for sign_in
        
    except FloodWaitError as e:
        if spinner_task: spinner_task.cancel()
        if 'spinner_task_auth' in locals() and spinner_task_auth: spinner_task_auth.cancel()
        print(f"[-] Error: Terdeteksi FloodWaitError saat koneksi ({e.seconds} detik). Coba lagi setelah jeda.")
        print("[*] Script akan keluar. Silakan jalankan ulang setelah beberapa saat.")
        if client and client.is_connected():
            await client.disconnect()
        return
    except AuthKeyUnregisteredError:
        if spinner_task: spinner_task.cancel()
        if 'spinner_task_auth' in locals() and spinner_task_auth: spinner_task_auth.cancel()
        print("[-] Error: AuthKeyUnregisteredError. Ini bisa terjadi jika Anda mencabut sesi Telegram Anda atau API ID/Hash Anda berubah.")
        print("[*] Menghapus file sesi dan config.json. Silakan jalankan ulang script dan login kembali.")
        session_file = f"{config['session_name']}.session"
        if os.path.exists(session_file):
            os.remove(session_file)
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        return
    except Exception as e:
        if spinner_task: spinner_task.cancel()
        if 'spinner_task_auth' in locals() and spinner_task_auth: spinner_task_auth.cancel()
        print(f"[-] Error saat menghubungkan ke Telegram atau otorisasi: {e}")
        # Tambahkan kondisi jika API ID atau Hash masih default/0
        if config['api_id'] == 0 or config['api_hash'] == "":
            print("[*] Catatan: API ID atau API Hash Anda mungkin belum diatur atau salah. Silakan periksa melalui menu.")
        print("[*] Pastikan API ID dan API Hash benar, koneksi internet stabil, dan tidak ada blokir firewall.")
        if client and client.is_connected():
            await client.disconnect()
        return
    finally:
        # Ensure spinners are cancelled even if an exception occurs before set() is called
        if spinner_task and not spinner_task.done():
            spinner_task.cancel()
        if 'spinner_task_auth' in locals() and spinner_task_auth and not spinner_task_auth.done():
            spinner_task_auth.cancel()

    # Jalankan menu interaktif
    await run_main_menu()

    # Setelah keluar dari menu, lanjutkan ke proses monitoring
    await start_monitoring_process()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Script dihentikan oleh pengguna.")
    finally:
        if client and client.is_connected():
            asyncio.run(client.disconnect())
            print("[*] Client Telegram terputus.")

