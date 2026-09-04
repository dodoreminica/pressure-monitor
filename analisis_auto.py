import pandas as pd
import numpy as np
import datetime
import os
import requests
import warnings
import pandas_datareader.data as web

warnings.filterwarnings('ignore')

# Trik agar display tabel lokal tidak error di GitHub Actions terminal
try:
    from IPython.display import display
except ImportError:
    def display(obj):
        if hasattr(obj, 'data'):
            print(obj.data.to_string(index=False))
        else:
            print(obj)

# ==============================================================================
# TAHAP 1: AMBIL DATA DARI SCRAPER_MESIN.PY
# ==============================================================================
file_csv = "pressure_6mo_history.csv"

if not os.path.exists(file_csv):
    print(f"❌ [ERROR FATAL] File {file_csv} tidak ditemukan! Pastikan scraper berjalan.")
    exit(1)

df_master = pd.read_csv(file_csv)
df_pivot = df_master.copy()

# ==============================================================================
# TAHAP 2: LOGIKA MESIN ANALISIS & RADAR BOM WAKTU
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

pesan_bom_list = []
print("\n" + "★"*90)
print("🚨 RADAR BOM WAKTU (KATALIS MAKRO AS) 🚨")
print("★"*90)

for event, tanggal in jadwal_bom_waktu.items():
    if tanggal is None:
        continue
    
    selisih_hari = (tanggal - hari_ini_date).days
    tgl_str = tanggal.strftime('%d %B %Y')
    
    if 0 <= selisih_hari <= 7:
        pesan = f"⚠️ <b>H-STAY AWAY:</b> {event} meledak dalam {selisih_hari} HARI (Tanggal {tgl_str})!"
        pesan_bom_list.append(pesan)
        print(pesan.replace("<b>", "").replace("</b>", ""))
    else:
        pesan = f"🟢 <b>AMAN:</b> {event} terdekat masih {selisih_hari} hari lagi (Tanggal {tgl_str})."
        pesan_bom_list.append(pesan)
        print(pesan.replace("<b>", "").replace("</b>", ""))

if not pesan_bom_list:
    pesan_bom_list.append("✅ <b>JALUR BERSIH:</b> Tidak ada bom waktu terdeteksi.")
teks_bom_waktu = "\n".join(pesan_bom_list)
print("="*90)

# ==============================================================================
# TAHAP 2.5: RUANG KONFIGURASI DATA MAKRO (AUTO-UPDATE FRED API & MANUAL ID)
# ==============================================================================
print("\nMenarik data Makroekonomi AS terbaru dari server Federal Reserve (FRED)...")
try:
    start_d = hari_ini_date - datetime.timedelta(days=730)
    
    df_fed = web.DataReader('FEDFUNDS', 'fred', start_d, hari_ini_date)
    fed_sekarang = df_fed.iloc[-1, 0]
    tgl_fed_sekarang = df_fed.index[-1].strftime('%d %b %Y')
    fed_sebelumnya = df_fed.iloc[-2, 0]
    tgl_fed_sebelumnya = df_fed.index[-2].strftime('%d %b %Y')

    df_unemp = web.DataReader('UNRATE', 'fred', start_d, hari_ini_date)
    unemp_sekarang = df_unemp.iloc[-1, 0]
    tgl_unemp_sekarang = df_unemp.index[-1].strftime('%d %b %Y')
    unemp_sebelumnya = df_unemp.iloc[-2, 0]
    tgl_unemp_sebelumnya = df_unemp.index[-2].strftime('%d %b %Y')

    cpi_data = web.DataReader('CPIAUCSL', 'fred', start_d, hari_ini_date)
    cpi_sekarang = cpi_data.iloc[-1, 0]
    tgl_cpi_sekarang = cpi_data.index[-1].strftime('%d %b %Y')
    
    cpi_bln_lalu = cpi_data.iloc[-2, 0]
    tgl_cpi_sebelumnya = cpi_data.index[-2].strftime('%d %b %Y')
    
    cpi_thn_lalu = cpi_data.iloc[-13, 0]
    
    cpi_yoy_sekarang = ((cpi_sekarang - cpi_thn_lalu) / cpi_thn_lalu) * 100
    cpi_yoy_sebelumnya = ((cpi_bln_lalu - cpi_data.iloc[-14, 0]) / cpi_data.iloc[-14, 0]) * 100

    makro_us = {
        "Suku Bunga The Fed": f"{fed_sekarang:.2f}% (Rilis: {tgl_fed_sekarang} | Sebelumnya: {fed_sebelumnya:.2f}% per {tgl_fed_sebelumnya} | Target: 2.00%)",
        "Inflasi Tahunan (CPI YoY)": f"{cpi_yoy_sekarang:.2f}% (Rilis: {tgl_cpi_sekarang} | Sebelumnya: {cpi_yoy_sebelumnya:.2f}% per {tgl_cpi_sebelumnya} | Target The Fed: 2.00%)",
        "Pengangguran AS (Unemployment)": f"{unemp_sekarang:.2f}% (Rilis: {tgl_unemp_sekarang} | Sebelumnya: {unemp_sebelumnya:.2f}% per {tgl_unemp_sebelumnya})"
    }

    print("✅ SUKSES Tarik Data FRED secara Transparan:")
    for k, v in makro_us.items():
        print(f"   📌 {k} : {v}")

except Exception as e:
    print(f"⚠️ GAGAL menarik data FRED: {e}. Menggunakan data cadangan.")
    makro_us = {
        "Suku Bunga The Fed (FOMC Rate)": "5.25% - 5.50% (Fallback)",
        "Inflasi Tahunan AS (CPI YoY)": "3.0% (Fallback | Target: 2.0%)",
        "Pengangguran AS (Unemployment)": "4.1% (Fallback)"
    }

catatan_manual_id = "Catatan: Data Indonesia diupdate secara manual (cek berkala ke website resmi BI/BPS)."
makro_id = {
    "Suku Bunga Acuan (BI Rate)": "5.75% (Rilis RDG Agustus 2026 | Sebelumnya: 6.25% | Target Inflasi BI: 1.5% - 3.5%)",
    "Inflasi Tahunan (BPS)": "2.88% (Rilis BPS Agustus 2026 untuk data Juli | Sebelumnya: 3.34%)",
    "Pengangguran Terbuka (BPS)": "4.65% (Rilis BPS Mei 2026 | Sebelumnya: 4.68%)"
}

print(f"\n🇮🇩 UPDATE DATA MAKRO INDONESIA (Pencarian Manual):")
print(f"   ⚠️ {catatan_manual_id}")
for k, v in makro_id.items():
    print(f"   📌 {k} : {v}")

teks_makro_us = "\n".join([f"📌 <b>{k}</b> :\n   └ {v}" for k, v in makro_us.items()])
teks_makro_id = f"⚠️ <i>{catatan_manual_id}</i>\n" + "\n".join([f"📌 <b>{k}</b> :\n   └ {v}" for k, v in makro_id.items()])


# ==============================================================================
# TAHAP 3: MESIN DASHBOARD SPLIT-SCREEN & TREND BACAAN
# ==============================================================================
print("\nMenghitung kalkulasi momentum Smart Money (1D, 1W, 1M, 3M, 6M)...")
df_angka = df_pivot.select_dtypes(include=np.number)
total_baris = len(df_angka)

# PERBAIKAN LOGIKA INDEXING (Karena data sudah dibalik: Hari ini = Baris 0)
harga_hari_ini = df_angka.iloc[0]
harga_1_hari   = df_angka.iloc[1]   if total_baris > 1   else df_angka.iloc[-1]
harga_1_minggu = df_angka.iloc[7]   if total_baris > 7   else df_angka.iloc[-1]   
harga_1_bulan  = df_angka.iloc[30]  if total_baris > 30  else df_angka.iloc[-1]   
harga_3_bulan  = df_angka.iloc[90]  if total_baris > 90  else df_angka.iloc[-1]   
harga_6_bulan  = df_angka.iloc[180] if total_baris > 180 else df_angka.iloc[-1]   

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

# UPDATE KLASTER DENGAN NAMA ASET TERBARU
klaster_makro = ['US_10Y_Yield', 'US_2Y_Futures','VIX_Fear','Bitcoin', 'DXY_Index', 'USD_IDR', 'USD_SGD', 'USD_JPY', 'JPY_IDR', 'USD_CNY']
klaster_us_tech = ['Nasdaq_IXIC', 'Semicon_SOXX', 'Software_IGV', 'CyberSec_CIBR', 'Biotech_IBB', 'Power_XLU', 'Energy_XLE']
klaster_em_komoditas = ['IHSG_Indo', 'Indo_Foreign_Flow', 'Indeks_Komoditas', 'Gold_XAU_USD', 'Gold_XAU_IDR', 'Minyak_Bumi_WTI', 'Minyak_Bumi_Brent', 'Minyak_Sawit_CPO', 'Batu_Bara', 'Tembaga_Copper', 'RareEarth_REMX', 'Gas_Alam', 'Minyak_Kedelai']

df_makro = df_dashboard[df_dashboard['Nama_Aset'].isin(klaster_makro)].sort_values(by='1_Bulan_(%)', ascending=False).reset_index(drop=True)
df_us_tech = df_dashboard[df_dashboard['Nama_Aset'].isin(klaster_us_tech)].sort_values(by='1_Bulan_(%)', ascending=False).reset_index(drop=True)
df_em_komoditas = df_dashboard[df_dashboard['Nama_Aset'].isin(klaster_em_komoditas)].sort_values(by='1_Bulan_(%)', ascending=False).reset_index(drop=True)

# ==============================================================================
# TAHAP 4: ENGINE PEWARNAAN TABEL LOKAL (TERMINAL/JUPYTER)
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
# TAHAP 5: KIRIM PESAN AUTO KE TELEGRAM (FORMAT TEKS BARIS AMAN)
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

def format_baris_telegram(row):
    nama = row['Nama_Aset']
    harga = f"{row['Harga_Sekarang']:,.2f}"
    
    pct_1w = f"+{row['1_Minggu_(%)']:.2f}%" if row['1_Minggu_(%)'] > 0 else f"{row['1_Minggu_(%)']:.2f}%"
    pct_1m = f"+{row['1_Bulan_(%)']:.2f}%" if row['1_Bulan_(%)'] > 0 else f"{row['1_Bulan_(%)']:.2f}%"
    pct_3m = f"+{row['3_Bulan_(%)']:.2f}%" if row['3_Bulan_(%)'] > 0 else f"{row['3_Bulan_(%)']:.2f}%"
    pct_6m = f"+{row['6_Bulan_(%)']:.2f}%" if row['6_Bulan_(%)'] > 0 else f"{row['6_Bulan_(%)']:.2f}%"
    status = row['Status_Smart_Money']
    
    return f"🔹 <b>{nama}</b> | {harga}\n   ├ 1W: {pct_1w} | 1M: {pct_1m}\n   ├ 3M: {pct_3m} | 6M: {pct_6m}\n   └ {status}\n"

teks_makro = "\n".join([format_baris_telegram(row) for _, row in df_makro.iterrows()])
teks_tech = "\n".join([format_baris_telegram(row) for _, row in df_us_tech.iterrows()])
teks_em = "\n".join([format_baris_telegram(row) for _, row in df_em_komoditas.iterrows()])

pesan_final = f"""🤖 <b>LAPORAN PASAR SUBUH</b>
======================

🚨 <b>RADAR BOM WAKTU (KATALIS AS):</b>
{teks_bom_waktu}

🇺🇸 <b>UPDATE DATA MAKRO AS:</b>
{teks_makro_us}

🇮🇩 <b>UPDATE DATA MAKRO INDONESIA:</b>
{teks_makro_id}
======================

🌍 <b>KLASTER MAKRO & VALAS:</b>
{teks_makro}
💻 <b>US TECH & INFRASTRUKTUR AI:</b>
{teks_tech}
🇮🇩 <b>EMERGING MARKETS & KOMODITAS:</b>
{teks_em}"""

kirim_telegram_post(pesan_final)
