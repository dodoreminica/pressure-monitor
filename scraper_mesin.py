import os
import pandas as pd
from datetime import datetime
import pytz
import time
import warnings
from tvDatafeed import TvDatafeed, Interval
from IPython.display import display 

warnings.filterwarnings('ignore')

# ==============================================================================
# TAHAP 1: AUTENTIKASI AMAN TRADINGVIEW DARI GITHUB SECRETS
# ==============================================================================
tv_username = os.environ.get("TDV_TAG")
tv_password = os.environ.get("TDV_COUNTER")

print(f"🔍 [AUDIT] TV Username Terbaca: {bool(tv_username)}")
print(f"🔍 [AUDIT] TV Password Terbaca: {bool(tv_password)}")

if not tv_username or not tv_password:
    print("❌ [FATAL ERROR] Kredensial TradingView (TDV_TAG / TDV_COUNTER) kosong atau tidak diinjeksikan!")
    exit(1)

# Inisialisasi koneksi TradingView
try:
    tv = TvDatafeed(tv_username, tv_password)
    print("✅ [SUKSES] Terhubung ke server TradingView.")
except Exception as e:
    print(f"❌ [FATAL ERROR] Gagal login ke TradingView: {e}")
    exit(1)

# ==============================================================================
# TAHAP 2: DAFTAR ASET & BHARATA EXCHANGE TRADINGVIEW
# Format: 'Nama_Aset': ('KODE_TICKER', 'BURSA_EXCHANGE')
# ==============================================================================
daftar_aset = {
    # --- KLASTER MAKRO & MATA UANG ---
    'DXY_Index': ('DXY', 'CAPITALCOM'),
    'US_10Y_Yield': ('US10Y', 'TVC'),
    'US_2Y_Futures': ('ZT1!', 'CBOT'),
    'VIX_Fear': ('VIX', 'CBOE'),
    'USD_SGD': ('USDSGD', 'FX_IDC'),
    'USD_IDR': ('USDIDR', 'FX_IDC'),
    'USD_JPY': ('USDJPY', 'FX_IDC'),
    'USD_CNY': ('USDCNY', 'FX_IDC'),
    'IHSG_Indo': ('JKSE', 'IDX'),
    'Indo_Foreign_Flow': ('EIDO', 'AMEX'),

    # --- KLASTER KOMODITAS & BAHAN BAKU AI ---
    'Gold_XAU_USD': ('GOLD', 'TVC'), 
    'Minyak_Bumi_WTI': ('CL1!', 'NYMEX'),    
    'Minyak_Bumi_Brent': ('BZ1!', 'NYMEX'),  
    'Minyak_Sawit_CPO': ('FCPO1!', 'BMD'),   
    'Batu_Bara': ('MTF1!', 'NYMEX'),         
    'Tembaga_Copper': ('HG1!', 'COMEX'),
    'RareEarth_REMX': ('REMX', 'AMEX'),
    'Gas_Alam': ('NG1!', 'NYMEX'),
    'Minyak_Kedelai': ('ZL1!', 'CBOT'),      
    'Indeks_Komoditas': ('DBC', 'AMEX'),

    # --- KLASTER TEKNOLOGI & INFRASTRUKTUR ---
    'Nasdaq_IXIC': ('IXIC', 'NASDAQ'),
    'Semicon_SOXX': ('SOXX', 'NASDAQ'),
    'Software_IGV': ('IGV', 'BATS'),
    'CyberSec_CIBR': ('CIBR', 'BATS'),
    'Biotech_IBB': ('IBB', 'NASDAQ'),
    'Power_XLU': ('XLU', 'AMEX'),
    'Energy_XLE': ('XLE', 'AMEX'),
    'Bitcoin': ('BTCUSD', 'BINANCE')
}

waktu_jakarta = pytz.timezone('Asia/Jakarta')
waktu_sekarang = datetime.now(waktu_jakarta).strftime('%Y-%m-%d %H:%M:%S')

print(f"\nMemulai pemindaian Makro-Ekonomi via TradingView pada: {waktu_sekarang}\n")

kumpulan_series = {}

# ==============================================================================
# TAHAP 3: MESIN PENYEDOT DATA TRADINGVIEW (TV DATAFEED)
# ==============================================================================
for nama_aset, (kode_ticker, bursa) in daftar_aset.items():
    print(f"Menyedot rekam jejak dari TradingView: {nama_aset} ({kode_ticker} di {bursa})...")
    try:
        # Mengambil data timeframe harian (n_bars=365 untuk data 1 tahun)
        df_hist = tv.get_hist(symbol=kode_ticker, exchange=bursa, interval=Interval.in_daily, n_bars=365)

        if df_hist is not None and not df_hist.empty:
            # Kolom harga penutupan di TradingView bernama 'close' (huruf kecil)
            close_data = df_hist['close']
            if isinstance(close_data, pd.DataFrame):
                close_data = close_data.iloc[:, 0]

            close_data.index = pd.to_datetime(close_data.index).tz_localize(None).normalize()
            close_data = close_data[~close_data.index.duplicated(keep='last')]

            kumpulan_series[nama_aset] = close_data.round(4)
        else:
            print(f" -> Peringatan: Data TradingView untuk {nama_aset} kosong.")

        # Jeda sejenak agar aman dari pembatasan rate-limit server TradingView
        time.sleep(1.5)

    except Exception as e:
        print(f"[!] GAGAL EKSTRAKSI {nama_aset}: {e}")

print("\nProses pemindaian selesai. Merakit Master Table...")

# ==============================================================================
# TAHAP 4: MASTER CALENDAR ALIGNMENT (SINKRONISASI & PENGHAPUSAN NaN)
# ==============================================================================
if not kumpulan_series:
    print("❌ [FATAL ERROR] Tidak ada data yang berhasil ditarik dari TradingView!")
    exit(1)

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

# Menghitung JPY ke IDR secara presisi dari TradingView
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

# Membalik urutan agar tanggal terbaru selalu berada di baris paling atas
df_master = df_master.sort_values('Tanggal_Pasar', ascending=False)

kolom_ekstra = []
if 'JPY_IDR' in df_master.columns: kolom_ekstra.append('JPY_IDR')
if 'Gold_XAU_IDR' in df_master.columns: kolom_ekstra.append('Gold_XAU_IDR')

kolom_urut_target = ['Timestamp_Mesin', 'Tanggal_Pasar'] + list(daftar_aset.keys()) + kolom_ekstra
kolom_urut_aman = [col for col in kolom_urut_target if col in df_master.columns]
df_master = df_master[kolom_urut_aman]

nama_file = "pressure_6mo_history.csv"
df_master.to_csv(nama_file, index=False)

print(f"\n[SUKSES] Data Historis TradingView & Kurs Silang telah disimpan menjadi: {nama_file}")

# ==============================================================================
# AUDIT FORENSIK: DETEKSI DATA BASI (ANTI-STALE DATA)
# ==============================================================================
tanggal_paling_atas = df_master['Tanggal_Pasar'].iloc[0]
tanggal_hari_ini = datetime.now(waktu_jakarta).strftime('%Y-%m-%d')

print(f"\n🔍 [AUDIT] Tanggal Sistem: {tanggal_hari_ini}")
print(f"🔍 [AUDIT] Tanggal Baris Puncak Data: {tanggal_paling_atas}")

if tanggal_paling_atas != tanggal_hari_ini:
    print(f"🚨 [PERINGATAN] Data TradingView terakhir tanggal: {tanggal_paling_atas} (Kemungkinan hari libur bursa).")
else:
    print("✅ [VALIDASI] Data TradingView terkonfirmasi *up-to-date* hari ini.")

# ==============================================================================
# TAHAP 6: MENAMPILKAN HASIL DALAM 3 TABEL (SPLIT)
# ==============================================================================
print("\n" + "="*90)
print("MEMECAH TABEL MENJADI 3 KLASTER UNTUK ANALISIS...")
print("="*90)

klaster_makro = ['Tanggal_Pasar', 'US_10Y_Yield', 'US_2Y_Futures','VIX_Fear','Bitcoin', 'DXY_Index', 'USD_IDR', 'USD_SGD', 'USD_JPY', 'JPY_IDR', 'USD_CNY']
klaster_us_tech = ['Tanggal_Pasar', 'Nasdaq_IXIC', 'Semicon_SOXX', 'Software_IGV', 'CyberSec_CIBR', 'Biotech_IBB', 'Power_XLU', 'Energy_XLE']
klaster_em_komoditas = ['Tanggal_Pasar', 'IHSG_Indo', 'Indo_Foreign_Flow', 'Indeks_Komoditas', 'Gold_XAU_USD', 'Gold_XAU_IDR', 'Minyak_Bumi_WTI', 'Minyak_Bumi_Brent', 'Minyak_Sawit_CPO', 'Batu_Bara', 'Tembaga_Copper', 'RareEarth_REMX', 'Gas_Alam', 'Minyak_Kedelai']

klaster_makro_aman = [c for c in klaster_makro if c in df_master.columns]
klaster_us_tech_aman = [c for c in klaster_us_tech if c in df_master.columns]
klaster_em_komoditas_aman = [c for c in klaster_em_komoditas if c in df_master.columns]

df_makro = df_master[klaster_makro_aman]
df_us_tech = df_master[klaster_us_tech_aman]
df_em_komoditas = df_master[klaster_em_komoditas_aman]

print("\n🌍 TABEL 1: MAKROEKONOMI & VALAS (Menampilkan 5 hari terakhir)")
display(df_makro.head(5)) 

print("\n💻 TABEL 2: US TECH & INFRASTRUKTUR AI (Menampilkan 5 hari terakhir)")
display(df_us_tech.head(5))

print("\n🇮🇩 TABEL 3: EMERGING MARKETS & KOMODITAS (Menampilkan 5 hari terakhir)")
display(df_em_komoditas.head(5))
