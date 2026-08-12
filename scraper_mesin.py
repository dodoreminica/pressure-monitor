import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import warnings
from IPython.display import display # Tambahkan ini untuk memunculkan tabel cantik

# Mengabaikan pesan warning dari pandas/yfinance agar log terminal GitHub tetap bersih
warnings.filterwarnings('ignore')

# ==============================================================================
# TAHAP 1: SETUP SESI SILUMAN (ANTI IP-BAN GITHUB ACTIONS)
# ==============================================================================
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})
retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))

# ==============================================================================
# TAHAP 2: DAFTAR ASET (KLASTER MAKROEKONOMI)
# ==============================================================================
daftar_aset = {
    # --- KLASTER MAKRO & MATA UANG ---
    'DXY_Index': 'DX-Y.NYB',
    'US_10Y_Yield': '^TNX',
    'US_2Y_Futures': 'ZT=F',
    'VIX_Fear': '^VIX',
    'USD_SGD': 'USDSGD=X',
    'USD_IDR': 'USDIDR=X',
    'USD_JPY': 'USDJPY=X',
    'USD_CNY': 'USDCNY=X',   # FIX: Menggunakan format ticker standar YF agar tidak NaN
    'IHSG_Indo': '^JKSE',
    'Indo_Foreign_Flow': 'EIDO',

    # --- KLASTER KOMODITAS & BAHAN BAKU AI ---
    'Gold_XAU': 'GC=F',
    'Minyak_Crude': 'CL=F',
    'Tembaga_Copper': 'HG=F',
    'RareEarth_REMX': 'REMX',
    'Gas_Alam': 'NG=F',
    'Minyak_Kedelai': 'ZL=F',
    'Indeks_Komoditas': 'DBC',

    # --- KLASTER TEKNOLOGI & INFRASTRUKTUR ---
    'Nasdaq_IXIC': '^IXIC',
    'Semicon_SOXX': 'SOXX',
    'Software_IGV': 'IGV',
    'CyberSec_CIBR': 'CIBR',
    'Biotech_IBB': 'IBB',
    'Power_XLU': 'XLU',
    'Energy_XLE': 'XLE',
    'Bitcoin': 'BTC-USD'
}

waktu_jakarta = pytz.timezone('Asia/Jakarta')
waktu_sekarang = datetime.now(waktu_jakarta).strftime('%Y-%m-%d %H:%M:%S')

print(f"Memulai pemindaian Makro-Ekonomi pada: {waktu_sekarang}\n")

kumpulan_series = {}

# ==============================================================================
# TAHAP 3: MESIN PENYEDOT DATA (SCRAPER)
# ==============================================================================
for nama_aset, kode_ticker in daftar_aset.items():
    print(f"Menyedot rekam jejak 1 TAHUN dari: {nama_aset} ({kode_ticker})...")
    try:
        # Penarikan langsung menggunakan yf.download (tanpa session agar tidak crash dengan requests)
        df_hist = yf.download(kode_ticker, period="1y", progress=False, auto_adjust=True)

        if not df_hist.empty:
            # Antisipasi jika yfinance mengembalikan DataFrame dengan MultiIndex
            close_data = df_hist['Close']
            if isinstance(close_data, pd.DataFrame):
                close_data = close_data.iloc[:, 0]

            # STANDARISASI TANGGAL: Buang timezone, ambil murni tanggalnya
            close_data.index = pd.to_datetime(close_data.index).tz_localize(None).normalize()

            # Hapus duplikat tanggal jika terjadi glitch di server YFinance
            close_data = close_data[~close_data.index.duplicated(keep='last')]

            # Simpan ke dictionary
            kumpulan_series[nama_aset] = close_data.round(4)
        else:
            print(f" -> Peringatan: Data {nama_aset} kosong.")

        time.sleep(1) # Jeda dinaikkan jadi 1 detik agar lebih aman dari blokir IP YF

    except Exception as e:
        print(f"[!] GAGAL EKSTRAKSI {nama_aset}: {e}")

print("\nProses pemindaian selesai. Merakit Master Table...")

# ==============================================================================
# TAHAP 4: MASTER CALENDAR ALIGNMENT (SINKRONISASI & PENGHAPUSAN NaN)
# ==============================================================================
# Gabungkan semua data
df_master = pd.DataFrame(kumpulan_series)

# Ambil rentang tanggal dari data yang didapat
tanggal_mulai = df_master.index.min()
tanggal_akhir = df_master.index.max()

# Bdate_range = Business Date Range (Hanya Senin s/d Jumat)
kalender_bursa = pd.bdate_range(start=tanggal_mulai, end=tanggal_akhir)

# Re-index tabel menggunakan Kalender Bursa
df_master = df_master.reindex(kalender_bursa)

# Mengisi data kosong (NaN) akibat hari libur nasional dengan harga penutupan terakhir (ffill)
df_master = df_master.ffill()

# Mengisi baris awal jika ada yang kosong (bfill)
df_master = df_master.bfill()

# ==============================================================================
# TAHAP 5: FINISHING & EKSPOR CSV
# ==============================================================================
df_master.index.name = 'Tanggal_Pasar'
df_master.columns.name = None
df_master.reset_index(inplace=True)

# Format ulang tanggal menjadi string YYYY-MM-DD
df_master['Tanggal_Pasar'] = df_master['Tanggal_Pasar'].dt.strftime('%Y-%m-%d')

# Tambahkan waktu eksekusi sebagai log di mesin
df_master['Timestamp_Mesin'] = waktu_sekarang

# Pindahkan Timestamp ke kolom paling depan agar rapi
kolom_urut = ['Timestamp_Mesin', 'Tanggal_Pasar'] + list(daftar_aset.keys())
df_master = df_master[kolom_urut]

# Sesuai request: Nama file tetap dipertahankan
nama_file = "pressure_6mo_history.csv"
df_master.to_csv(nama_file, index=False)

print(f"\n[SUKSES] Data 20 Aset historis telah disimpan menjadi: {nama_file}")

# ==============================================================================
# TAHAP 6: MENAMPILKAN HASIL DALAM 3 TABEL (SPLIT)
# ==============================================================================
print("\n" + "="*90)
print("MEMECAH TABEL MENJADI 3 KLASTER UNTUK ANALISIS...")
print("="*90)

# Pastikan USD_CNY digunakan menggantikan CNH agar sinkron dengan data baru
klaster_makro = ['Tanggal_Pasar', 'US_10Y_Yield', 'US_2Y_Futures','Gold_XAU', 'VIX_Fear','Bitcoin', 'DXY_Index', 'USD_IDR', 'USD_SGD', 'USD_JPY', 'USD_CNY']
klaster_us_tech = ['Tanggal_Pasar', 'Nasdaq_IXIC', 'Semicon_SOXX', 'Software_IGV', 'CyberSec_CIBR', 'Biotech_IBB', 'Power_XLU', 'Energy_XLE']
klaster_em_komoditas = ['Tanggal_Pasar', 'IHSG_Indo', 'Indo_Foreign_Flow', 'Indeks_Komoditas', 'Minyak_Crude', 'Tembaga_Copper', 'RareEarth_REMX', 'Gas_Alam', 'Minyak_Kedelai']

# Memisahkan DataFrame berdasarkan list klaster di atas
df_makro = df_master[klaster_makro]
df_us_tech = df_master[klaster_us_tech]
df_em_komoditas = df_master[klaster_em_komoditas]

print("\n🌍 TABEL 1: MAKROEKONOMI & VALAS (Menampilkan 5 hari terakhir)")
display(df_makro.tail(5)) # Memakai tail(5) agar tidak terlalu panjang ke bawah

print("\n💻 TABEL 2: US TECH & INFRASTRUKTUR AI (Menampilkan 5 hari terakhir)")
display(df_us_tech.tail(5))

print("\n🇮🇩 TABEL 3: EMERGING MARKETS & KOMODITAS (Menampilkan 5 hari terakhir)")
display(df_em_komoditas.tail(5))
