import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import time
from IPython.display import display # Tambahkan ini untuk memunculkan tabel cantik di Colab

# ==============================================================================
# TAHAP 1: MESIN PENYEDOT DATA (SCRAPER) - VERSI FULL 20 ASET (1 TAHUN)
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
    'USD_CNH': 'CNH=X',
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

hasil_tarikan = []
waktu_jakarta = pytz.timezone('Asia/Jakarta')
waktu_sekarang = datetime.now(waktu_jakarta).strftime('%Y-%m-%d %H:%M:%S')

print(f"Memulai pemindaian DISI-TY-VBS-JCX pada: {waktu_sekarang}\n")

for nama_aset, kode_ticker in daftar_aset.items():
    print(f"Menyedot rekam jejak 1 TAHUN dari: {nama_aset} ({kode_ticker})...")
    
    try:
        aset = yf.Ticker(kode_ticker)
        # LEVEL UP: Diubah menjadi 1y agar mesin bisa menghitung MA-200 (kalau perlu)
        data_historis = aset.history(period="1y") 
        
        if not data_historis.empty:
            for tanggal, baris_data in data_historis.iterrows():
                harga_penutupan = baris_data['Close']
                hasil_tarikan.append({
                    'Timestamp_Mesin': waktu_sekarang,
                    'Tanggal_Pasar': tanggal.strftime('%Y-%m-%d'),
                    'sensor1_money_move': nama_aset,
                    'Value': round(harga_penutupan, 4)
                })
        else:
            print(f" -> Peringatan: Data {nama_aset} kosong.")
            
        time.sleep(1) # Jeda aman anti-blokir
            
    except Exception as e:
        print(f" -> Error pada {nama_aset}: {e}")

print("\nProses pemindaian selesai. Merakit laporan historis...")
df_log = pd.DataFrame(hasil_tarikan)

df_pivot = df_log.pivot_table(
    index='Tanggal_Pasar', 
    columns='sensor1_money_move', 
    values='Value'
).reset_index()

df_pivot = df_pivot.ffill().bfill()

# UBAH JUDUL POJOK KIRI ATAS
df_pivot.columns.name = None 
df_pivot.index.name = 'baris' 

# NAMA FILE DIUBAH AGAR SESUAI DENGAN ISINYA (1 TAHUN)
nama_file = "pressure_6mo_history.csv"
df_pivot.to_csv(nama_file, index=False)

print(f"\n[SUKSES] Data 20 Aset historis (1 Tahun) telah disimpan menjadi: {nama_file}")

# ==============================================================================
# TAHAP 2: MENAMPILKAN HASIL DALAM 3 TABEL (SPLIT)
# ==============================================================================
print("\n" + "="*90)
print("MEMECAH TABEL MENJADI 3 KLASTER UNTUK ANALISIS...")
print("="*90)

klaster_makro = ['Tanggal_Pasar', 'US_10Y_Yield', 'US_2Y_Futures','Gold_XAU', 'VIX_Fear','Bitcoin', 'DXY_Index', 'USD_IDR', 'USD_SGD', 'USD_JPY', 'USD_CNH']
klaster_us_tech = ['Tanggal_Pasar', 'Nasdaq_IXIC', 'Semicon_SOXX', 'Software_IGV', 'CyberSec_CIBR', 'Biotech_IBB', 'Power_XLU', 'Energy_XLE']
klaster_em_komoditas = ['Tanggal_Pasar', 'IHSG_Indo', 'Indo_Foreign_Flow', 'Indeks_Komoditas', 'Minyak_Crude', 'Tembaga_Copper', 'RareEarth_REMX', 'Gas_Alam', 'Minyak_Kedelai']

# Memisahkan DataFrame berdasarkan list klaster di atas
df_makro = df_pivot[klaster_makro]
df_us_tech = df_pivot[klaster_us_tech]
df_em_komoditas = df_pivot[klaster_em_komoditas]

print("\n🌍 TABEL 1: MAKROEKONOMI & VALAS (Menampilkan 5 hari terakhir)")
display(df_makro.tail(5)) # Memakai tail(5) agar tidak terlalu panjang ke bawah

print("\n💻 TABEL 2: US TECH & INFRASTRUKTUR AI (Menampilkan 5 hari terakhir)")
display(df_us_tech.tail(5))

print("\n🇮🇩 TABEL 3: EMERGING MARKETS & KOMODITAS (Menampilkan 5 hari terakhir)")
display(df_em_komoditas.tail(5))
