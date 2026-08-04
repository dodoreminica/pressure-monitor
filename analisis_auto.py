import pandas as pd
import numpy as np
import datetime

# ==============================================================================
# TAHAP 1:  AMBIL DATA DARI SCRAPER_MESIN.PY
# ==============================================================================
file_csv = "pressure_6mo_history.csv"
df_pivot = pd.read_csv(file_csv)

# ==============================================================================
# TAHAP 2:  LOGIKA MESIN ANALISIS
# ==============================================================================
hari_ini_date = datetime.date.today()

# ------------------------------------------------------------------------------
# UPGRADE: MASTER LIST KALENDER MAKRO 2026 (Set and Forget)
# ------------------------------------------------------------------------------
list_nfp = [datetime.date(2026, 8, 7), datetime.date(2026, 9, 4), datetime.date(2026, 10, 2), datetime.date(2026, 11, 6), datetime.date(2026, 12, 4)]
list_cpi = [datetime.date(2026, 8, 12), datetime.date(2026, 9, 11), datetime.date(2026, 10, 13), datetime.date(2026, 11, 12), datetime.date(2026, 12, 10)]
list_fomc = [datetime.date(2026, 9, 16), datetime.date(2026, 11, 4), datetime.date(2026, 12, 16)]

def cari_tanggal_terdekat(daftar_tanggal):
    # Menyaring tanggal yang MASA DEPAN atau HARI INI
    tanggal_mendatang = [tgl for tgl in daftar_tanggal if tgl >= hari_ini_date]
    if tanggal_mendatang:
        return min(tanggal_mendatang) # Ambil tanggal yang paling dekat (terkecil)
    return None # Jika sudah habis tahun 2026

jadwal_bom_waktu = {
    "NFP (Data Tenaga Kerja AS)": cari_tanggal_terdekat(list_nfp),
    "CPI (Data Inflasi AS)": cari_tanggal_terdekat(list_cpi),
    "FOMC (Penentuan Suku Bunga)": cari_tanggal_terdekat(list_fomc)
}

print("\n" + "★"*90)
print("🚨 RADAR BOM WAKTU (KATALIS MAKRO AS) 🚨")
print("★"*90)
ada_bahaya = False
for event, tanggal in jadwal_bom_waktu.items():
    if tanggal is None:
        continue

    selisih_hari = (tanggal - hari_ini_date).days
    if 0 <= selisih_hari <= 7:
        print(f"⚠️ H-STAY AWAY: {event} meledak dalam {selisih_hari} HARI (Tanggal {tanggal.strftime('%d %B %Y')})!")
        ada_bahaya = True
    elif selisih_hari > 7:
        print(f"🟢 AMAN: {event} terdekat masih {selisih_hari} hari lagi (Tanggal {tanggal.strftime('%d %B %Y')}).")

if not ada_bahaya:
    print("\n✅ JALUR BERSIH: Tidak ada bom waktu dalam 7 hari ke depan. Aman untuk *Swing Trade*.")
print("="*90)

# ==============================================================================
# TAMBAHAN BARU: ANGKA FUNDAMENTAL AMERIKA SERIKAT
# ==============================================================================
print("\n" + "🇺🇸 UPDATE DATA MAKRO AMERIKA SERIKAT TERBARU 🇺🇸")
print("-" * 90)
print("📌 Suku Bunga The Fed (FOMC Rate) : 5.25% - 5.50% (Posisi saat ini, ditahan tinggi)")
print("📌 Inflasi Tahunan AS (CPI YoY)   : 3.0% (Rilis data terakhir, target The Fed 2.0%)")
print("📌 Pengangguran AS (Unemployment) : 4.1% (Rilis data terakhir, mulai merangkak naik)")
print("="*90)

print("\n" + "🇮🇩 UPDATE DATA MAKRO INDONESIA TERBARU 🇮🇩")
print("-" * 90)
print("📌 Suku Bunga Acuan (BI Rate) : 5.75% (Dipertahankan pada RDG Juli 2026)")
print("📌 Inflasi Tahunan (BPS)      : 2.88% (Rilis Agustus 2026 untuk data Juli)")
print("📌 Pengangguran Terbuka (BPS) : 4.68% atau 7,24 Juta Orang (Data BPS Februari 2026)")
print("="*90 + "\n")


# ==============================================================================
# MESIN DASHBOARD SPLIT-SCREEN (V4.0)
# ==============================================================================

print("Menghitung kalkulasi momentum Smart Money (1D, 1W, 1M, 3M, 6M)...")

df_angka = df_pivot.select_dtypes(include=np.number)

# MESIN WAKTU (Kalender 30 Hari)
harga_hari_ini = df_angka.iloc[-1]
harga_1_hari   = df_angka.iloc[-2]
harga_1_minggu = df_angka.iloc[-8]
harga_1_bulan  = df_angka.iloc[-31]
harga_3_bulan  = df_angka.iloc[-91]
harga_6_bulan  = df_angka.iloc[0]

# MENGHITUNG PERSENTASE
pct_1d = ((harga_hari_ini - harga_1_hari) / harga_1_hari) * 100
pct_1w = ((harga_hari_ini - harga_1_minggu) / harga_1_minggu) * 100
pct_1m = ((harga_hari_ini - harga_1_bulan) / harga_1_bulan) * 100
pct_3m = ((harga_hari_ini - harga_3_bulan) / harga_3_bulan) * 100
pct_6m = ((harga_hari_ini - harga_6_bulan) / harga_6_bulan) * 100

# MERAKIT TABEL MASTER
df_dashboard = pd.DataFrame({
    'Nama_Aset': df_angka.columns,
    'Harga_Sekarang': harga_hari_ini.values,
    '1_Hari_(%)': pct_1d.values,
    '1_Minggu_(%)': pct_1w.values,
    '1_Bulan_(%)': pct_1m.values,
    '3_Bulan_(%)': pct_3m.values,
    '6_Bulan_(%)': pct_6m.values
})

# INDIKATOR TERBALIK
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

# ==============================================================================
# PEMBAGIAN KLASTER (REVISI TATA LETAK: LOGIKA NEGARA BERKEMBANG & PASAR UANG)
# ==============================================================================
klaster_makro = ['US_10Y_Yield', 'US_2Y_Futures','Gold_XAU', 'VIX_Fear','Bitcoin', 'DXY_Index', 'USD_IDR', 'USD_SGD', 'USD_JPY', 'USD_CNH']
klaster_us_tech = ['Nasdaq_IXIC', 'Semicon_SOXX', 'Software_IGV', 'CyberSec_CIBR', 'Biotech_IBB', 'Power_XLU', 'Energy_XLE']
klaster_em_komoditas = ['IHSG_Indo', 'Indo_Foreign_Flow', 'Indeks_Komoditas', 'Minyak_Crude', 'Tembaga_Copper', 'RareEarth_REMX', 'Gas_Alam', 'Minyak_Kedelai', ]

# Memecah dan Mengurutkan Tabel (Berdasarkan Tren 1 Bulan)
df_makro = df_dashboard[df_dashboard['Nama_Aset'].isin(klaster_makro)].sort_values(by='1_Bulan_(%)', ascending=False).reset_index(drop=True)
df_us_tech = df_dashboard[df_dashboard['Nama_Aset'].isin(klaster_us_tech)].sort_values(by='1_Bulan_(%)', ascending=False).reset_index(drop=True)
df_em_komoditas = df_dashboard[df_dashboard['Nama_Aset'].isin(klaster_em_komoditas)].sort_values(by='1_Bulan_(%)', ascending=False).reset_index(drop=True)

# ==============================================================================
# ENGINE PEWARNAAN
# ==============================================================================
def warnai_baris(row):
    styles = []
    nama_aset = row['Nama_Aset']

    for col, val in row.items():
        if col in ['1_Hari_(%)', '1_Minggu_(%)', '1_Bulan_(%)', '3_Bulan_(%)', '6_Bulan_(%)']:
            if nama_aset in inverse_assets:
                if val >= 3: styles.append('color: #FF0000; font-weight: bold; background-color: rgba(255, 0, 0, 0.1)')
                elif val > 0: styles.append('color: #FF6347')
                elif val <= -3: styles.append('color: #00FF00; font-weight: bold; background-color: rgba(0, 255, 0, 0.1)')
                elif val < 0: styles.append('color: #7CFC00')
                else: styles.append('')
            else:
                if val >= 3: styles.append('color: #00FF00; font-weight: bold; background-color: rgba(0, 255, 0, 0.1)')
                elif val > 0: styles.append('color: #7CFC00')
                elif val <= -3: styles.append('color: #FF0000; font-weight: bold; background-color: rgba(255, 0, 0, 0.1)')
                elif val < 0: styles.append('color: #FF6347')
                else: styles.append('')
        else:
            styles.append('')
    return styles

def percantik_tabel(df):
    return (df.style.apply(warnai_baris, axis=1).format({
        'Harga_Sekarang': '{:,.2f}', '1_Hari_(%)': '{:,.2f}%', '1_Minggu_(%)': '{:,.2f}%',
        '1_Bulan_(%)': '{:,.2f}%', '3_Bulan_(%)': '{:,.2f}%', '6_Bulan_(%)': '{:,.2f}%'
    }))

# ==============================================================================
# TAMPILKAN 3 TABEL KE LAYAR (URUTAN BARU)
# ==============================================================================
print("\n" + "="*90)
print("🌍 LAYAR 2: MAKROEKONOMI GLOBAL & PASAR UANG (Suku Bunga & Valas)")
print("==========================================================================================")
display(percantik_tabel(df_makro))

print("\n" + "="*90)
print("💻 LAYAR 1: WALL STREET & RANTAI PASOK AI (The Pick and Shovel Play)")
print("==========================================================================================")
display(percantik_tabel(df_us_tech))

print("\n" + "="*90)
print("🇮🇩 LAYAR 3: EMERGING MARKETS & KOMODITAS (Bahan Baku & Sentimen Asia)")
print("==========================================================================================")
display(percantik_tabel(df_em_komoditas))

# ==============================================================================
# TAHAP 4:  KIRIM PESAN AUTO KE TGRAM
# ==============================================================================
import os
import requests

def kirim_telegram(pesan):
    token = os.environ.get('TGRAM_COUNTER')
    chat_id = os.environ.get('TGRAM_TAG')
    
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={pesan}"
    requests.get(url)
    
    pesan_ringkasan = f"🚨 RADAR BOM WAKTU: {ada_bahaya_event}\n🚀 Status Pasar: {tren_singkat}"
kirim_telegram(pesan_ringkasan)

