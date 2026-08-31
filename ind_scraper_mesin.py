import pandas as pd
import numpy as np
import requests
import time
import random
import io
import re
from bs4 import BeautifulSoup

print("📥 TAHAP 1: EKSTRAKSI DATA MULTI-DIMENSI (CSA, TECHNICAL & DIVIDEND)")
print("-" * 130)

# =========================================================
# 1. FUNGSI NORMALISASI ANGKA & FORMAT UANG
# =========================================================
def parse_angka(val_str, is_in_millions=False):
    if pd.isna(val_str) or str(val_str).strip() in ['N/A', '-', '']: return np.nan
    val_str = str(val_str).strip()
    is_percent = '%' in val_str

    match = re.search(r'([-]?[±\d,\.]+)\s*([TBM])?', val_str, re.IGNORECASE)
    if match:
        num_str = match.group(1).replace(',', '')
        suffix = match.group(2)
        try: num = float(num_str)
        except: return np.nan

        if suffix:
            suffix = suffix.upper()
            if suffix == 'T': num *= 1e12
            elif suffix == 'B': num *= 1e9
            elif suffix == 'M': num *= 1e6

        if is_in_millions and not is_percent: num *= 1_000_000
        if is_percent: num /= 100.0
        return num
    return np.nan

def format_money(val):
    if pd.isna(val) or val == 0: return "0"
    if abs(val) >= 1e9: return f"{val/1e9:+.2f} B"
    elif abs(val) >= 1e6: return f"{val/1e6:+.2f} M"
    return f"{val:+.0f}"

# =========================================================
# 2. MESIN PENYEDOT MULTI-HALAMAN & API
# =========================================================
def scrape_full_data(ticker, div_time_manual):
    print(f"🔄 Menyedot Web & API untuk: {ticker}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    kamus_ov, kamus_stat, kamus_comp = {}, {}, {}
    kamus_bs, kamus_is, kamus_cf, kamus_rat = {}, {}, {}, {}

    try:
        # Scrape Overview
        res_ov = requests.get(f"https://stockanalysis.com/quote/idx/{ticker}/", headers=headers)
        for tb in pd.read_html(io.StringIO(res_ov.text)):
            if len(tb.columns) == 2:
                for _, row in tb.iterrows(): kamus_ov[str(row.iloc[0]).strip()] = str(row.iloc[1]).strip()

        # Scrape Fundamental Tables
        urls = ['statistics', 'financials/ratios', 'financials/cash-flow-statement', 'financials/income-statement', 'financials/balance-sheet', 'company']
        dicts = [kamus_stat, kamus_rat, kamus_cf, kamus_is, kamus_bs, kamus_comp]

        for url, kamus in zip(urls, dicts):
            res = requests.get(f"https://stockanalysis.com/quote/idx/{ticker}/{url}/", headers=headers)
            try:
                for tb in pd.read_html(io.StringIO(res.text)):
                    if len(tb.columns) >= 2:
                        for _, row in tb.iterrows():
                            key, val = str(row.iloc[0]).strip(), str(row.iloc[1]).strip()
                            if key and key != 'nan': kamus[key] = val
            except ValueError:
                pass

    except Exception as e:
        print(f"   ⚠️ Gagal menyedot fundamental {ticker}")

    # =================================================================
    # MESIN PEMBEDAH DIVIDEN (HANYA PAYOUT FREQUENCY)
    # =================================================================
    payout_frequency = np.nan
    try:
        res_div = requests.get(f"https://stockanalysis.com/quote/idx/{ticker}/dividend/", headers=headers)
        if res_div.status_code == 200:
            soup = BeautifulSoup(res_div.text, 'html.parser')
            teks_div = soup.get_text(separator='|', strip=True).split('|')

            for i in range(len(teks_div)):
                if teks_div[i].strip() == 'Payout Frequency' and i + 1 < len(teks_div):
                    pf_val = teks_div[i+1].strip()
                    # Filter validasi: Pastikan teks yang diambil memang frekuensi
                    if pf_val.lower() in ['annual', 'semi-annual', 'semi annual', 'quarterly', 'monthly']:
                        payout_frequency = pf_val
                        break
    except Exception as e:
        pass

    # =================================================================
    # MESIN TECHNICAL & FLOW
    # =================================================================
    flow_1d, flow_2d, flow_3d, flow_4d, flow_1w, flow_1m, flow_3m, flow_6m = ["N/A"] * 8
    flow_1m_raw = 0
    rsi_14, macd_line, macd_signal = np.nan, np.nan, np.nan
    close_price = parse_angka(kamus_ov.get('Previous Close'))
    trend_ma, sinyal_tech = 'N/A', 'N/A'

    try:
        url_yf = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.JK?range=1y&interval=1d"
        res_yf = requests.get(url_yf, headers=headers).json()

        if res_yf.get('chart', {}).get('result') is not None:
            result = res_yf['chart']['result'][0]
            closes = result['indicators']['quote'][0].get('close', [])
            volumes = result['indicators']['quote'][0].get('volume', [])

            df_tech = pd.DataFrame({'close': closes, 'volume': volumes}).dropna()

            if len(df_tech) > 120:
                close_price = df_tech['close'].iloc[-1]
                delta = df_tech['close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                df_tech['RSI'] = 100 - (100 / (1 + (gain / loss)))
                rsi_14 = round(df_tech['RSI'].iloc[-1], 2)

                exp1 = df_tech['close'].ewm(span=12, adjust=False).mean()
                exp2 = df_tech['close'].ewm(span=26, adjust=False).mean()
                df_tech['MACD'] = exp1 - exp2
                df_tech['Signal'] = df_tech['MACD'].ewm(span=9, adjust=False).mean()
                macd_line = round(df_tech['MACD'].iloc[-1], 2)
                macd_signal = round(df_tech['Signal'].iloc[-1], 2)

                df_tech['MA20'] = df_tech['close'].rolling(20).mean()
                df_tech['MA60'] = df_tech['close'].rolling(60).mean()
                h0, h1 = df_tech.iloc[-1], df_tech.iloc[-2]

                trend_ma = "UPTREND" if h0['MA20'] > h0['MA60'] else "DOWNTREND"
                if h1['MA20'] <= h1['MA60'] and h0['MA20'] > h0['MA60']: sinyal_tech = "GOLDEN CROSS 🚀"
                elif h1['MA20'] >= h1['MA60'] and h0['MA20'] < h0['MA60']: sinyal_tech = "DEATH CROSS 🩸"
                else: sinyal_tech = "TERKONFIRMASI"

                df_tech['money_flow'] = df_tech['close'].diff().fillna(0) * df_tech['volume']
                flow_1m_raw = df_tech['money_flow'].iloc[-20:].sum()

                flow_1d = format_money(df_tech['money_flow'].iloc[-1:].sum())
                flow_2d = format_money(df_tech['money_flow'].iloc[-2:].sum())
                flow_3d = format_money(df_tech['money_flow'].iloc[-3:].sum())
                flow_4d = format_money(df_tech['money_flow'].iloc[-4:].sum())
                flow_1w = format_money(df_tech['money_flow'].iloc[-5:].sum())
                flow_1m = format_money(flow_1m_raw)
                flow_3m = format_money(df_tech['money_flow'].iloc[-60:].sum())
                flow_6m = format_money(df_tech['money_flow'].iloc[-120:].sum())

    except Exception as e:
        print(f"   ⚠️ Gagal memproses data Yahoo {ticker}")

    sector = kamus_comp.get('Sector', 'N/A')
    industry = kamus_comp.get('Industry', 'N/A')

    # --- DATASET A ---
    data_A = {
        'Ticker': ticker,
        'Cash & Equivalents': parse_angka(kamus_bs.get('Cash & Equivalents', kamus_bs.get('Cash & Cash Equivalents')), True),
        'Account Receivable': parse_angka(kamus_bs.get('Accounts Receivable', kamus_bs.get('Net Receivables')), True),
        'Inventory': parse_angka(kamus_bs.get('Inventory'), True),
        'Total Current Asset': parse_angka(kamus_bs.get('Total Current Assets'), True),
        'Total Current Liabilities': parse_angka(kamus_bs.get('Total Current Liabilities'), True),
        'Revenue': parse_angka(kamus_stat.get('Revenue')),
        'Cost of Revenue': parse_angka(kamus_is.get('Cost of Revenue'), True),
        'Gross Profit': parse_angka(kamus_stat.get('Gross Profit')),
        'EBIT': parse_angka(kamus_stat.get('EBIT')),
        'Net Income': parse_angka(kamus_stat.get('Net Income')),
        'Total Liabilities': parse_angka(kamus_bs.get('Total Liabilities'), True),
        'Long Term Liabilities': parse_angka(kamus_bs.get('Long-Term Debt', kamus_bs.get('Total Long-Term Liabilities')), True),
        'Shareholders Equity': parse_angka(kamus_bs.get("Shareholders' Equity", kamus_bs.get('Total Equity')), True),
        'Interest Expense': parse_angka(kamus_is.get('Interest Expense', kamus_is.get('Interest Expense / Income')), True),
        'Operating Cash Flow': parse_angka(kamus_cf.get('Operating Cash Flow'), True),
        'Investing Cash Flow': parse_angka(kamus_cf.get('Investing Cash Flow', kamus_cf.get('Cash Flow from Investing')), True),
        'Financing Cash Flow': parse_angka(kamus_cf.get('Financing Cash Flow', kamus_cf.get('Cash Flow from Financing')), True)
    }

    # --- DATASET B ---
    payout_ratio = parse_angka(kamus_stat.get('Payout Ratio'))
    roe = parse_angka(kamus_rat.get('Return on Equity (ROE)', kamus_stat.get('Return on Equity (ROE)')))
    retention_rate = 1 - payout_ratio if pd.notna(payout_ratio) else np.nan
    expected_div_growth = (retention_rate * roe) if pd.notna(retention_rate) and pd.notna(roe) else np.nan

    data_B = {
        'Ticker': ticker, 'Sector': sector, 'Industry': industry, 'Close': close_price,
        'PE Ratio': parse_angka(kamus_rat.get('PE Ratio', kamus_stat.get('PE Ratio'))),
        'PB Ratio': parse_angka(kamus_rat.get('PB Ratio', kamus_rat.get('P/B Ratio'))),
        'ROE': roe,
        'EV/EBITDA': parse_angka(kamus_rat.get('EV/EBITDA', kamus_rat.get('EV/EBITDA Ratio'))),
        'Capital Expenditure': parse_angka(kamus_stat.get('Capital Expenditures')),
        'Working Capital': parse_angka(kamus_stat.get('Working Capital')),
        'Depreciation & Amortization': parse_angka(kamus_stat.get('Depreciation & Amortization')),
        'SUN 10 Year': 0.0715, 'Beta': parse_angka(kamus_stat.get('Beta (5Y)', kamus_stat.get('Beta'))),
        'Market Risk Premium': 0.10, 'Dividend Per Share': parse_angka(kamus_stat.get('Dividend Per Share')),
        'Dividend Yield': parse_angka(kamus_stat.get('Dividend Yield')), 'Dividend Time': div_time_manual,

        # INI KOLOM PAYOUT FREQUENCY SAJA (Annual Dividend sudah dihapus)
        'Payout Frequency': payout_frequency,

        'Expected Dividend Growth': expected_div_growth
    }

    # --- DATASET C ---
    data_C = {
        'Ticker': ticker,
        'Altman Z-Score': parse_angka(kamus_stat.get('Altman Z-Score')),
        'Total Assets': parse_angka(kamus_bs.get('Total Assets'), True),
        'Retained Earnings': parse_angka(kamus_bs.get('Retained Earnings'), True),
        'Market Cap': parse_angka(kamus_stat.get('Market Cap'))
    }

    # --- DATASET D ---
    data_D = {
        'Ticker': ticker, 'Trend (MA)': trend_ma, 'Sinyal Teknikal': sinyal_tech,
        'RSI (14)': rsi_14, 'MACD Line': macd_line, 'MACD Signal': macd_signal,
        'Flow 1D': flow_1d, 'Flow 2D': flow_2d, 'Flow 3D': flow_3d, 'Flow 4D': flow_4d,
        'Flow 1W': flow_1w, 'Flow 1M': flow_1m, 'Flow 3M': flow_3m, 'Flow 6M': flow_6m,
        'Flow 1M Raw': flow_1m_raw
    }

    return data_A, data_B, data_C, data_D

# =========================================================
# 3. EKSEKUSI PIPELINE
# =========================================================
daftar_saham = {
    # -----------------------------------------------------
    # 1. SEKTOR ENERGI (Minyak, Gas, Batu Bara & Jasa Pendukung)
    # -----------------------------------------------------
    "AADI": "JUN & NOV", "ADRO": "MAY & DEC", "AKRA": "MAY & AUG", "BSSR": "JAN & JUN & NOV",
    "BUMI": "-", "BYAN": "JUN / DEC", "ELSA": "JUN", "ENRG": "-", "GEMS": "JUN",
    "INDY": "JUN / MAY", "ITMG": "APR & NOV", "KKGI": "JUN & DEC", "MCOL": "MAY & NOV",
    "MEDC": "JUN & NOV", "MYOH": "JUN", "PTBA": "JUN", "SICO": "APR & NOV /DEC", "TOBA": "MAY",

    # -----------------------------------------------------
    # 2. SEKTOR BARANG BAKU (Logam, Kimia, Kayu, Kertas, Plastik, Semen)
    # -----------------------------------------------------
    "AMMN": "-", "ANTM": "JUN", "AVIA": "APR & NOV", "BRMS": "-", "BRPT": "JUN",
    "CITA": "JUL", "CLPI": "JUN / JUL", "DKFT": "JUN & OCT", "ESSA": "APR", "FWCT": "JUN & NOV",
    "GDST": "JUN & DEC LAST 2024", "GGRP": "JUN", "INCO": "MAY", "INKP": "JUN", "INTP": "MAY",
    "ISSP": "JUL", "MBMA": "-", "MDKA": "-", "MINE": "-", "NCKL": "JUN",
    "NICL": "MAY / JUN & AUG & NOV /DEC", "PBID": "MAY / JUN", "PSAB": "JUN/JUL",
    "SAMF": "JUN", "SMGR": "MAY", "SRSN": "JUN / JUL", "TINS": "JUN", "TKIM": "JUN", "TPIA": "JUN", 
    "BLES": "JUN / JUL", "DGWG": "-", "FPNI": "-", "PART": "-", "SMGA": "-",

    # -----------------------------------------------------
    # 3. SEKTOR PERINDUSTRIAN (Alat Berat, Mesin, Jasa Industri)
    # -----------------------------------------------------
    "ABMM": "MAY", "ASII": "MAY & OCT", "HEXA": "SEP / OCT", "JTPE": "JUN & NOV",
    "KBLI": "MAY & AUG", "KUAS": "JUN / MAY", "MSJA": "JUN", "PBSA": "JUN",
    "SCCO": "JUN", "SKRN": "MAY / JUN & NOV", "TOTL": "MAY", "UNTR": "MAY & OCT",
    "CARS": "-", "GJTL": "JUN / JUL", "MPPA": "-",

    # -----------------------------------------------------
    # 4. KONSUMEN PRIMER (FMCG, Rokok, Sawit, Makanan)
    # -----------------------------------------------------
    "AALI": "MAY & OCT", "AMRT": "MAY", "BUDI": "JUN & NOV", "CLEO": "JUN", "CMRY": "JUN",
    "CPIN": "MAY", "DSNG": "JUN", "GGRM": "JUL", "HMSP": "MAY", "ICBP": "JUL", "INDF": "JUL",
    "JPFA": "APR", "LSIP": "JUL", "MIDI": "MAY", "MLBI": "MAY / JUN & NOV", "MYOR": "MAY",
    "NSSS": "NOV", "PNGO": "JUN & NOV", "ROTI": "APR", "TAPG": "MAY & NOV",
    "TBLA": "JUN", "TLDN": "MAY & OCT", "WIIM": "JUN", "YUPI": "JUL & DEC",
    "BWPT": "-", "GZCO": "-", "SIMP": "JUL", "STAA": "MAY & OCT",

    # -----------------------------------------------------
    # 5. KONSUMEN NON-PRIMER (Ritel, Otomotif, Perabot, Media, Hotel)
    # -----------------------------------------------------
    "ACES": "JUN", "AUTO": "MAY & OCT", "EAST": "APR / JUN & DEC / JAN", "ERAA": "JUN",
    "KDSI": "JUN", "LPIN": "MAY / JUN", "MAPI": "JUN", "MNCN": "JUL", "MPMX": "JUN",
    "PANR": "MAY", "RALS": "MAY", "SCMA": "JUN & NOV", "SMSM": "MAY & AUG",
    "SPTO": "JUN & NOV", "TOTO": "JUN & NOV",

    # -----------------------------------------------------
    # 6. SEKTOR KESEHATAN (Rumah Sakit, Farmasi, Alkes)
    # -----------------------------------------------------
    "DVLA": "JUN & OCT / NOV", "EPMT": "MAY / JUN", "HEAL": "JUN", "KLBF": "JUN",
    "MARK": "MAY & AUG", "MIKA": "MAY", "PRDA": "MAY / APR", "SIDO": "MAY & NOV",
    "SILO": "MAY", "TSPC": "JUN & NOV",

    # -----------------------------------------------------
    # 7. SEKTOR KEUANGAN (Bank, Multifinance, Asuransi, Sekuritas)
    # -----------------------------------------------------
    "ADMF": "MAY", "AMAG": "MAY", "ASDM": "JUL", "BBCA": "MAR & DEC", "BBNI": "MAR",
    "BBRI": "MAR", "BBTN": "MAR", "BDMN": "APR", "BFIN": "MAY & NOV", "BMRI": "MAR",
    "BRIS": "MAY", "DNAR": "-", "NISP": "APR", "PANS": "JUL", "BBYB": "-", "SRTG": "MAY",

    # -----------------------------------------------------
    # 8. PROPERTI & REAL ESTAT (Pengembang Properti & Kawasan)
    # -----------------------------------------------------
    "BKSL": "-", "BSDE": "-", "CTRA": "JUN", "DMAS": "MAY / JUN", "DUTI": "GA NENTU",
    "PWON": "JUL", "RDTX": "JUN / JUL & DEC", "SMRA": "JUN", "SSIA": "JUN",

    # -----------------------------------------------------
    # 9. SEKTOR TEKNOLOGI (E-Commerce, IT, Perangkat Keras)
    # -----------------------------------------------------
    "BUKA": "-", "EMTK": "NOV", "GOTO": "-", "MSTI": "JUN", "MTDL": "MAY", "PTSN": "JUN", "WIRG": "-",

    # -----------------------------------------------------
    # 10. INFRASTRUKTUR (Telekomunikasi, Tol, Menara, Konstruksi)
    # -----------------------------------------------------
    "CBDK": "MAY", "EXCL": "MAY", "ISAT": "MAY", "JKON": "JUN", "JSMR": "MAY",
    "PGAS": "JUN", "PGEO": "JUN", "POWR": "MAY & DEC", "TBIG": "MAY & DEC",
    "TLKM": "JUN", "TOWR": "MAY & DEC", "NRCA": "MAY", "CDIA": "MAY",

    # -----------------------------------------------------
    # 11. TRANSPORTASI & LOGISTIK (Pengiriman & Maritim)
    # -----------------------------------------------------
    "ASSA": "JUN", "HAIS": "APR", "IPCC": "JUN & DEC", "IPCM": "JUN & DEC",
    "MAHA": "MAY", "NELY": "JUN & DEC", "SMDR": "JUL", "TEBE": "-", "TMAS": "MAY", "TPMA": "MAY",
    "BBRM": "-", "BOAT": "-", "BULL": "-",
}

list_A, list_B, list_C, list_D = [], [], [], []
for ticker, div_time in daftar_saham.items():
    dA, dB, dC, dD = scrape_full_data(ticker, div_time)
    list_A.append(dA); list_B.append(dB); list_C.append(dC); list_D.append(dD)
    time.sleep(random.uniform(1.5, 2.5))

df_A = pd.DataFrame(list_A)
df_B = pd.DataFrame(list_B)
df_C = pd.DataFrame(list_C)
df_D = pd.DataFrame(list_D)

df_C_clean = df_C[['Ticker', 'Altman Z-Score', 'Total Assets', 'Retained Earnings', 'Market Cap']]
df_mentah_utama = df_B.merge(df_C_clean, on='Ticker', how='left').merge(df_A, on='Ticker', how='left').merge(df_D, on='Ticker', how='left')


# =========================================================
# 4. EXPORT DATA (WAJIB UNTUK GITHUB ACTIONS)
# =========================================================
print("💾 Menyimpan seluruh data ke CSV...")

df_A.to_csv("Dataset_A_Laporan_Keuangan.csv", index=False)
df_B.to_csv("Dataset_B_Harga_Wajar.csv", index=False)
df_C.to_csv("Dataset_C_Risk_Scoring.csv", index=False)
df_D.drop(columns=['Flow 1M Raw']).to_csv("Dataset_D_Technical_Flow.csv", index=False)
df_mentah_utama.to_csv("df_mentah_utama.csv", index=False)

print("\n✅ TAHAP 1 SELESAI! Seluruh data mentah gabungan telah sukses diekspor.")
