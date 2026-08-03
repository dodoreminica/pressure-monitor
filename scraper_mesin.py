import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import time

# ==============================================================================
# TAHAP 1: MESIN PENYEDOT DATA (SCRAPER) - VERSI FULL 20 ASET
# ==============================================================================

# KAMUS SANDI LENGKAP (Termasuk Rotasi Sektor & Rantai Pasok AI)
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

# PROSES PENYEDOTAN
for nama_aset, kode_ticker in daftar_aset.items():
    print(f"Menyedot rekam jejak 6 bulan dari: {nama_aset} ({kode_ticker})...")

    try:
        aset = yf.Ticker(kode_ticker)
        data_historis = aset.history(period="6mo")

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

        time.sleep(1)

    except Exception as e:
        print(f" -> Error pada {nama_aset}: {e}")

# MENGUBAH KE DATAFRAME & MEMBERSIHKAN NaN
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

# SIMPAN FILE
nama_file = "pressure_6mo_history.csv"
df_pivot.to_csv(nama_file, index=False)

print(f"\n[SUKSES] Data 20 Aset historis telah disimpan menjadi: {nama_file}")

# Tampilkan di layar Colab
print("\n--- Preview Log Pergerakan Uang (6 Bulan) ---")
display(df_pivot)
