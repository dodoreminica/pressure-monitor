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
# TAHAP 2:  LOGIKA MESIN ANALISIS (BOM WAKTU MAKRO)
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

pesan_bom = "✅ AMAN: Tidak ada bom waktu dalam 7 hari ke depan."
for event, tanggal in jadwal_bom_waktu.items():
    if tanggal is None:
        continue
    selisih_hari = (tanggal - hari_ini_date).days
    if 0 <= selisih_hari <= 7:
        pesan_bom = f"⚠️ H-STAY AWAY: {event} meledak dalam {selisih_hari} HARI!"
        break 

# ==============================================================================
# TAHAP 3: MESIN DASHBOARD SPLIT-SCREEN & TREND BACAAN
# ==============================================================================
df_angka = df_pivot.select_dtypes(include=np.number)

# Mengambil perbandingan harga
harga_hari_ini = df_angka.iloc[-1]
harga_1_hari   = df_angka.iloc[-2]
harga_1_minggu = df_angka.iloc[-8]
harga_1_bulan  = df_angka.iloc[-31]
harga_3_bulan  = df_angka.iloc[-91]
harga_6_bulan  = df_angka.iloc[0]

# Menghitung Persentase
pct_1d = ((harga_hari_ini - harga_1_hari) / harga_1_hari) * 100
pct_1w = ((harga_hari_ini - harga_1_minggu) / harga_1_minggu) * 100
pct_1m = ((harga_hari_ini - harga_1_bulan) / harga_1_bulan) * 100
pct_3m = ((harga_hari_ini - harga_3_bulan) / harga_3_bulan) * 100
pct_6m = ((harga_hari_ini - harga_6_bulan) / harga_6_bulan) * 100

# Merakit df_dashboard Utama
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

# Memecah Dashboard ke 3 Klaster
klaster_makro = ['US_10Y_Yield', 'US_2Y_Futures','Gold_XAU', 'VIX_Fear','Bitcoin', 'DXY_Index', 'USD_IDR', 'USD_SGD', 'USD_JPY', 'USD_CNH']
klaster_us_tech = ['Nasdaq_IXIC', 'Semicon_SOXX', 'Software_IGV', 'CyberSec_CIBR', 'Biotech_IBB', 'Power_XLU', 'Energy_XLE']
klaster_em_komoditas = ['IHSG_Indo', 'Indo_Foreign_Flow', 'Indeks_Komoditas', 'Minyak_Crude', 'Tembaga_Copper', 'RareEarth_REMX', 'Gas_Alam', 'Minyak_Kedelai']

df_makro = df_dashboard[df_dashboard['Nama_Aset'].isin(klaster_makro)].sort_values(by='1_Bulan_(%)', ascending=False).reset_index(drop=True)
df_us_tech = df_dashboard[df_dashboard['Nama_Aset'].isin(klaster_us_tech)].sort_values(by='1_Bulan_(%)', ascending=False).reset_index(drop=True)
df_em_komoditas = df_dashboard[df_dashboard['Nama_Aset'].isin(klaster_em_komoditas)].sort_values(by='1_Bulan_(%)', ascending=False).reset_index(drop=True)

# ==============================================================================
# TAHAP 4:  KIRIM PESAN AUTO KE TGRAM (VERSI FULL ANGKA & KOMPREHENSIF)
# ==============================================================================
def kirim_telegram_post(pesan):
    token = os.environ.get('TGRAM_COUNTER')
    chat_id = os.environ.get('TGRAM_TAG')
    
    if not token or not chat_id:
        print("❌ GAGAL: Token atau Chat ID Telegram tidak ditemukan!")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": pesan,
        "parse_mode": "HTML"
    }
    
    try:
        respon = requests.post(url, data=payload)
        if respon.status_code == 200:
            print("✅ SUKSES: Laporan FULL telah dikirim ke Telegram!")
        else:
            print(f"❌ GAGAL: Pesan tidak terkirim. Error dari Telegram: {respon.text}")
    except Exception as e:
        print(f"❌ ERROR SISTEM: {e}")

# Fungsi Format Baris Telegram
def format_baris_telegram(row):
    nama = row['Nama_Aset']
    harga = f"{row['Harga_Sekarang']:,.2f}"
    
    pct_1w = f"+{row['1_Minggu_(%)']:.2f}%" if row['1_Minggu_(%)'] > 0 else f"{row['1_Minggu_(%)']:.2f}%"
    pct_1m = f"+{row['1_Bulan_(%)']:.2f}%" if row['1_Bulan_(%)'] > 0 else f"{row['1_Bulan_(%)']:.2f}%"
    status = row['Status_Smart_Money']
    
    return f"🔹 <b>{nama}</b> | {harga}\n   ├ 1W: {pct_1w} | 1M: {pct_1m}\n   └ {status}\n"

# Menerapkan Fungsi
teks_makro = "\n".join([format_baris_telegram(row) for _, row in df_makro.iterrows()])
teks_tech = "\n".join([format_baris_telegram(row) for _, row in df_us_tech.iterrows()])
teks_em = "\n".join([format_baris_telegram(row) for _, row in df_em_komoditas.iterrows()])

# Merakit pesan final
pesan_final = f"""🤖 <b>LAPORAN PASAR SUBUH</b>
======================
{pesan_bom}

🌍 <b>KLASTER MAKRO & VALAS:</b>
{teks_makro}
💻 <b>US TECH & INFRASTRUKTUR AI:</b>
{teks_tech}
🇮🇩 <b>EMERGING MARKETS & KOMODITAS:</b>
{teks_em}"""

# Eksekusi
kirim_telegram_post(pesan_final)
