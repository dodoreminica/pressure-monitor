import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import warnings
from IPython.display import display 

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
    'USD_CNY': 'USDCNY=X',
    'IHSG_Indo': '^JKSE',
    'Indo_Foreign_Flow': 'EIDO',

    # --- KLASTER KOMODITAS & BAHAN BAKU AI ---
    'Gold_XAU_USD': 'GC=F', 
    'Minyak_Bumi_WTI': 'CL=F',    # Bahan Bakar: Minyak Bumi AS
    'Minyak_Bumi_Brent': 'BZ=F',  # Bahan Bakar: Minyak Bumi Global
    'Minyak_Sawit_CPO': 'FCPO.KL',# Pangan: Minyak Kelapa Sawit (Cooking Oil)
    'Batu_Bara': 'MTF=F',         # Energi: Batu Bara Rotterdam
    'Tembaga_Copper': 'HG=F',
    'RareEarth_REMX': 'REMX',
    'Gas_Alam': 'NG=F',
    'Minyak_Kedelai': 'ZL=F',     # Pangan: Subtitusi CPO Global
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
        df_hist = yf.download(kode_ticker, period="1y", progress=False, auto_adjust=True)

        if not df_hist.empty:
            close_data = df_hist['Close']
            if isinstance(close_data, pd.DataFrame):
                close_data = close_data.iloc[:, 0]

            close_data.index = pd.to_datetime(close_data.index).tz_localize(None).normalize()
            close_data = close_data[~close_data.index.duplicated(keep='last')]

            kumpulan_series[nama_aset] = close_data.round(4)
        else:
            print(f" -> Peringatan: Data {nama_aset} kosong.")

        time.sleep(1)

    except Exception as e:
        print(f"[!] GAGAL EKSTRAKSI {nama_aset}: {e}")

print("\nProses pemindaian selesai. Merakit Master Table...")

# ==============================================================================
# TAHAP 4: MASTER CALENDAR ALIGNMENT (SINKRONISASI & PENGHAPUSAN NaN)
# ==============================================================================
df_master = pd.DataFrame(kumpulan_series)

tanggal_mulai = df_master.index.min()
tanggal_akhir = df_master.index.max()
kalender_bursa = pd.bdate_range(start=tanggal_mulai, end=tanggal_akhir)

df_master = df_master.reindex(kalender_bursa)
df_master = df_master.ffill().bfill()

# ==============================================================================
# TAHAP 4.5: MESIN PENGHITUNG KURS SILANG (CROSS-RATES & CONVERSION)
# ==============================================================================
print("🧮 Melakukan kalkulasi Kurs Silang (Cross-Rates) ke Rupiah...")

# Menghitung JPY ke IDR secara manual (Karenya YF sering gagal menarik JPYIDR=X langsung)
if 'USD_JPY' in df_master.columns and 'USD_IDR' in df_master.columns:
    df_master['JPY_IDR'] = (df_master['USD_IDR'] / df_master['USD_JPY']).round(2)

# Mengkonversi Emas USD ke Rupiah
if 'Gold_XAU_USD' in df_master.columns and 'USD_IDR' in df_master.columns:
    df_master['Gold_XAU_IDR'] = (df_master['Gold_XAU_USD'] * df_master['USD_IDR']).round(0)

# ==============================================================================
# TAHAP 5: FINISHING, SORTING & EKSPOR CSV
# ==============================================================================
df_master.index.name = 'Tanggal_Pasar'
df_master.columns.name = None
df_master.reset_index(inplace=True)

df_master['Tanggal_Pasar'] = df_master['Tanggal_Pasar'].dt.strftime('%Y-%m-%d')
df_master['Timestamp_Mesin'] = waktu_sekarang

# Membalik urutan agar tanggal terbaru (hari ini) selalu berada di baris paling atas
df_master = df_master.sort_values('Tanggal_Pasar', ascending=False)

kolom_ekstra = []
if 'JPY_IDR' in df_master.columns: kolom_ekstra.append('JPY_IDR')
if 'Gold_XAU_IDR' in df_master.columns: kolom_ekstra.append('Gold_XAU_IDR')

kolom_urut = ['Timestamp_Mesin', 'Tanggal_Pasar'] + list(daftar_aset.keys()) + kolom_ekstra
df_master = df_master[kolom_urut]

nama_file = "pressure_6mo_history.csv"
df_master.to_csv(nama_file, index=False)

print(f"\n[SUKSES] Data Historis Makro & Kurs Silang telah disimpan menjadi: {nama_file}")

# ==============================================================================
# TAHAP 6: MENAMPILKAN HASIL DALAM 3 TABEL (SPLIT)
# ==============================================================================
print("\n" + "="*90)
print("MEMECAH TABEL MENJADI 3 KLASTER UNTUK ANALISIS...")
print("="*90)

klaster_makro = ['Tanggal_Pasar', 'US_10Y_Yield', 'US_2Y_Futures','VIX_Fear','Bitcoin', 'DXY_Index', 'USD_IDR', 'USD_SGD', 'USD_JPY', 'JPY_IDR', 'USD_CNY']
klaster_us_tech = ['Tanggal_Pasar', 'Nasdaq_IXIC', 'Semicon_SOXX', 'Software_IGV', 'CyberSec_CIBR', 'Biotech_IBB', 'Power_XLU', 'Energy_XLE']

# Memasukkan seluruh komoditas (Energi & Pangan) dengan nama yang sudah disamakan persis
klaster_em_komoditas = ['Tanggal_Pasar', 'IHSG_Indo', 'Indo_Foreign_Flow', 'Indeks_Komoditas', 'Gold_XAU_USD', 'Gold_XAU_IDR', 'Minyak_Bumi_WTI', 'Minyak_Bumi_Brent', 'Minyak_Sawit_CPO', 'Batu_Bara', 'Tembaga_Copper', 'RareEarth_REMX', 'Gas_Alam', 'Minyak_Kedelai']

df_makro = df_master[klaster_makro]
df_us_tech = df_master[klaster_us_tech]
df_em_komoditas = df_master[klaster_em_komoditas]

# Menggunakan .head(5) karena data sudah dibalik (yang terbaru di atas)
print("\n🌍 TABEL 1: MAKROEKONOMI & VALAS (Menampilkan 5 hari terakhir)")
display(df_makro.head(5)) 

print("\n💻 TABEL 2: US TECH & INFRASTRUKTUR AI (Menampilkan 5 hari terakhir)")
display(df_us_tech.head(5))

print("\n🇮🇩 TABEL 3: EMERGING MARKETS & KOMODITAS (Menampilkan 5 hari terakhir)")
display(df_em_komoditas.head(5))
