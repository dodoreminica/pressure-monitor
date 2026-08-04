import os
import requests

def kirim_telegram(pesan):
    token = os.environ.get('TGRAM_COUNTER')
    chat_id = os.environ.get('TGRAM_TAG')
    
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={pesan}"
    requests.get(url)

# Kirim pesan tes
kirim_telegram("Robot sudah bangun dan siap tugas, Manajer!")
