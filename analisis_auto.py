import pandas as pd
import numpy as np
import datetime
import os
import requests

try:
    from IPython.display import display
except ImportError:
    def display(obj):
        print(obj)

# ==============================================================================
# TAHAP 1:  AMBIL DATA DARI SCRAPER_MESIN.PY
# ==============================================================================
file_csv = "pressure_6mo_history.csv"
df_pivot = pd.read_csv(file_csv)

# ==============================================================================
# TAHAP 2:  LOGIKA MESIN ANALISIS
# ==============================================================================
hari_ini_date = datetime.date.today()

list_nfp = [datetime.date(2026, 8, 7), datetime.date(2026, 9, 4), datetime.date(2026, 10, 2), datetime.date(2026, 11, 6), datetime.date(2026, 12, 4)]
list_cpi = [datetime.date(2026, 8, 12), datetime.date(2026, 9, 11), datetime.date(2026, 10, 13), datetime.date(2026, 11, 12), datetime.date(2026, 12, 10)]
list_fomc = [datetime.date(2026, 9, 16), datetime.date(2026, 11, 4), datetime.date(2026, 12, 16)]

def cari_tanggal_terdekat(daftar_tanggal):
    tanggal_mendatang = [tgl for tgl in daftar_tanggal if tgl >= hari_ini_date]
    if tanggal_mendatang:
        return min(tanggal_mendatang)
    return None

jadwal_bom_waktu = {
    "NFP (Data Tenaga Kerja AS)": cari_tanggal_terdekat(list_nfp),
    "CPI (Data Inflasi AS)": cari_tanggal_terdekat(list_cpi),
    "FOMC (Penentuan Suku Bunga)": cari_tanggal_terdekat(list_fomc)
}

# --- MESIN PERANGKUM BOM WAKTU UNTUK TELEGRAM ---
pesan_bom = "✅ AMAN: Tidak ada bom waktu dalam 7 hari ke depan."
for event, tanggal in jadwal_bom_waktu.items():
    if tanggal is None:
        continue
    selisih_hari = (tanggal - hari_ini_date).days
    if 0 <= selisih_hari <= 7:
        pesan_bom = f"⚠️ H-STAY AWAY: {event} meledak dalam {selisih_hari} HARI!"
        break # Ambil satu yang paling dekat saja untuk Telegram

# ==============================================================================
# TAHAP 3: MESIN DASHBOARD SPLIT-SCREEN
# ==============================================================================
df_angka = df_pivot.select_dtypes(include=np.number)

harga_hari_ini = df_angka.iloc[-1]
harga_1_hari   = df_angka.iloc[-2]
harga_1_minggu = df_angka.iloc[-8]
harga_1_bulan  = df_angka.iloc[-31]
harga_3_bulan  = df_angka.iloc[-91]
harga_6_bulan  = df_angka.iloc[0]

pct_1d = ((harga_hari_ini - harga_1_hari) / harga_1_hari) * 100
pct_1w = ((harga_hari_ini - harga_1_minggu) / harga_1_minggu) * 100
pct_1m = ((harga_hari_ini - harga_1_bulan) / harga_1_bulan) * 100
pct_3m = ((harga_hari_ini - harga_3_bulan) / harga_3_bulan) * 100
pct_6m = ((harga_hari_ini - harga_6_bulan) / harga_6_bulan) * 100

df_dashboard = pd.DataFrame({
    'Nama_Aset': df_angka.columns,
    'Harga_Sekarang': harga_hari_ini.values,
    '1_Hari_(%)': pct_1d.values,
    '1_Minggu_(%)': pct_1w.values,
    '1_Bulan_(%)': pct_1m.values,
    '3_Bulan_(%)': pct_3m.values,
    '6_Bulan_(%)': pct_6m.values
})

inverse_assets = ['VIX_Fear', 'US_10Y_Yield', 'DXY_Index', 'USD_IDR']

def baca_tren_utama(baris):
    nama = baris['Nama_Aset']
    persen_1m = baris['1_Bulan_(%)']
    persen_1w = baris['1_Minggu_(%)']

    if nama in inverse_assets:
        if persen_1m >= 3 and persen_1w > 0: return "🚨 BAHAYA (Risiko Meningkat)"
        elif persen_1m <= -3 and persen_1w < 0: return "🟢 AMAN (Risiko Mereda)"
        elif persen_1m > 0 and persen_1w < 0: return "⚠️ Koreksi (Napas Sebentar)"
        elif persen_1m < 0 and persen_1w > 0: return "🔥 Waspada (Mulai Naik)"
        else: return "⚖️ Sideways (Ragu-ragu)"
    else:
        if persen_1m >= 3 and persen_1w > 0: return "🚀 AKUMULASI (Strong Buy)"
        elif persen_1m <= -3 and persen_1w < 0: return "🩸 DISTRIBUSI (Strong Sell)"
        elif persen_1m > 0 and persen_1w < 0: return "⚠️ Koreksi Jangka Pendek"
        elif persen_1m < 0 and persen_1w > 0: return "🌱 Rebound / Curi Start"
        else: return "⚖️ Sideways (Ragu-ragu)"

df_dashboard['Status_Smart_Money'] = df_dashboard.apply(baca_tren_utama, axis=1)

klaster_makro = ['US_10Y_Yield', 'US_2Y_Futures','Gold_XAU', 'VIX_Fear','Bitcoin', 'DXY_Index', 'USD_IDR', 'USD_SGD', 'USD_JPY', 'USD_CNH']
klaster_us_tech = ['Nasdaq_IXIC', 'Semicon_SOXX', 'Software_IGV', 'CyberSec_CIBR', 'Biotech_IBB', 'Power_XLU', 'Energy_XLE']

df_makro = df_dashboard[df_dashboard['Nama_Aset'].isin(klaster_makro)].sort_values(by='1_Bulan_(%)', ascending=False).reset_index(drop=True)
df_us_tech = df_dashboard[df_dashboard['Nama_Aset'].isin(klaster_us_tech)].sort_values(by='1_Bulan_(%)', ascending=False).reset_index(drop=True)


# ==============================================================================
# TAHAP 4:  KIRIM PESAN AUTO KE TGRAM (SUDAH DIPERBAIKI)
# ==============================================================================

def kirim_telegram(pesan):
    token = os.environ.get('TGRAM_COUNTER')
    chat_id = os.environ.get('TGRAM_TAG')
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={pesan}"
    requests.get(url)

# Mengambil peringkat 1 dari Makro dan Tech untuk dikirim ke Telegram
top_makro = df_makro.iloc[0]['Nama_Aset']
status_makro = df_makro.iloc[0]['Status_Smart_Money']

top_tech = df_us_tech.iloc[0]['Nama_Aset']
status_tech = df_us_tech.iloc[0]['Status_Smart_Money']

# Merakit pesan final yang rapi
pesan_final = f"""
🤖 LAPORAN PASAR SUBUH
======================
{pesan_bom}

📊 HIGHLIGHT SEKTOR:
- {top_makro} : {status_makro}
- {top_tech} : {status_tech}

Silakan buka Google Colab untuk melihat 3 Layar Dashboard selengkapnya!
"""

# Menjalankan fungsi kirim
kirim_telegram(pesan_final)
