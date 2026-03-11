from curl_cffi import requests
import urllib.parse
import json
import re
import time
import os

# Verilerin kaydedileceği ana klasör
KLASOR_ADI = "cekilen_veriler"
os.makedirs(KLASOR_ADI, exist_ok=True)

# ==========================================
# 1. ORTAK YARDIMCI FONKSİYONLAR
# ==========================================

def trendyol_yorum_bul(json_verisi):
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict) and "comment" in json_verisi[0]:
        return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = trendyol_yorum_bul(deger)
            if sonuc: return sonuc
    return []

def hb_yorum_bul(json_verisi):
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict):
        if "review" in json_verisi[0] or "star" in json_verisi[0] or "customerName" in json_verisi[0]:
            return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = hb_yorum_bul(deger)
            if sonuc: return sonuc
    return []

def yemeksepeti_yorum_bul(json_verisi):
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict):
        if "rating" in json_verisi[0] or "customerDescription" in json_verisi[0]:
            return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = yemeksepeti_yorum_bul(deger)
            if sonuc: return sonuc
    return []

def trendyol_go_yorum_bul(json_verisi):
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict):
        if "comment" in json_verisi[0] or "rate" in json_verisi[0] or "customerName" in json_verisi[0]:
            return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = trendyol_go_yorum_bul(deger)
            if sonuc: return sonuc
    return []

def etstur_yorum_bul(json_verisi):
    # Etstur API yanıtının içindeki yorumları bulur
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict):
        if "text" in json_verisi[0] or "comment" in json_verisi[0] or "reviewText" in json_verisi[0] or "customer" in json_verisi[0]:
            return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = etstur_yorum_bul(deger)
            if sonuc: return sonuc
    return []

# ==========================================
# 2. TRENDYOL API FONKSİYONU
# ==========================================
def trendyol_api_cek(urun_linki, max_sayfa):
    match = re.search(r'-p-(\d+)', urun_linki)
    if not match: return
    urun_id = match.group(1)
    dosya_yolu = os.path.join(KLASOR_ADI, f"trendyol_veri_{urun_id}.json")
    if os.path.exists(dosya_yolu): return
    print(f"✅ Trendyol Ürün ID: {urun_id}")
    tum_yorumlar = []
    headers = {"Accept": "application/json, text/plain, */*", "Origin": "https://www.trendyol.com", "Referer": urun_linki}

    for sayfa in range(max_sayfa):
        api_url = f"https://apigw.trendyol.com/discovery-storefront-trproductgw-service/api/review-read/product-reviews/detailed?channelId=1&contentId={urun_id}&page={sayfa}"
        try:
            response = requests.get(api_url, headers=headers, impersonate="chrome120", timeout=15, verify=False)
            if response.status_code != 200: break
            yorum_listesi = trendyol_yorum_bul(response.json())
            if not yorum_listesi: break
            tum_yorumlar.extend(yorum_listesi)
            print(f"   -> Sayfa {sayfa} çekildi. (+{len(yorum_listesi)} yorum)")
            time.sleep(0.5)
        except Exception: break

    if len(tum_yorumlar) > 0:
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")

# ==========================================
# 3. HEPSİBURADA API FONKSİYONU
# ==========================================
def hepsiburada_api_cek(urun_linki, max_sayfa):
    match = re.search(r'-p[m]?-([A-Za-z0-9]+)', urun_linki)
    if not match: return
    urun_sku = match.group(1).upper()
    dosya_yolu = os.path.join(KLASOR_ADI, f"hb_veri_{urun_sku}.json")
    if os.path.exists(dosya_yolu): return
    print(f"✅ Hepsiburada Ürün SKU: {urun_sku}")
    tum_yorumlar = []
    headers = {"Accept": "application/json, text/plain, */*", "Origin": "https://www.hepsiburada.com", "Referer": urun_linki}

    for sayfa in range(max_sayfa):
        offset = sayfa * 20
        api_url = f"https://user-content-gw-hermes.hepsiburada.com/queryapi/v2/ApprovedUserContents?sku={urun_sku}&from={offset}&size=20&includeSiblingVariantContents=true&includeSummary=true"
        try:
            response = requests.get(api_url, headers=headers, impersonate="chrome120", timeout=15, verify=False)
            if response.status_code != 200: break
            yorum_listesi = response.json().get("approvedUserContents", [])
            if not yorum_listesi: yorum_listesi = hb_yorum_bul(response.json())
            if not yorum_listesi: break
            tum_yorumlar.extend(yorum_listesi)
            print(f"   -> {offset}-{offset+20} arası çekildi. (+{len(yorum_listesi)} yorum)")
            time.sleep(1)
        except Exception: break

    if len(tum_yorumlar) > 0:
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")

# ==========================================
# 4. STEAM API FONKSİYONU
# ==========================================
def steam_api_cek(oyun_linki, max_sayfa):
    match = re.search(r'/app/(\d+)', oyun_linki)
    if not match: return
    app_id = match.group(1)
    dosya_yolu = os.path.join(KLASOR_ADI, f"steam_veri_{app_id}.json")
    if os.path.exists(dosya_yolu): return
    print(f"✅ Steam Oyun ID (App ID): {app_id}")
    tum_yorumlar = []
    cursor = "*"

    for sayfa in range(max_sayfa):
        encoded_cursor = urllib.parse.quote(cursor)
        api_url = f"https://store.steampowered.com/appreviews/{app_id}?json=1&language=turkish&filter=recent&num_per_page=100&cursor={encoded_cursor}"
        try:
            response = requests.get(api_url, impersonate="chrome120", timeout=15, verify=False)
            if response.status_code != 200: break
            data = response.json()
            yorum_listesi = data.get("reviews", [])
            if not yorum_listesi: break
            tum_yorumlar.extend(yorum_listesi)
            print(f"   -> Sayfa {sayfa} çekildi. (+{len(yorum_listesi)} yorum)")
            yeni_cursor = data.get("cursor")
            if not yeni_cursor or yeni_cursor == cursor: break
            cursor = yeni_cursor
            time.sleep(0.5)
        except Exception: break

    if len(tum_yorumlar) > 0:
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")

# ==========================================
# 5. YEMEKSEPETİ API FONKSİYONU
# ==========================================
def yemeksepeti_api_cek(restoran_linki, max_sayfa):
    match = re.search(r'/restaurant/([a-zA-Z0-9]+)', restoran_linki)
    if not match: return
    vendor_id = match.group(1)
    dosya_yolu = os.path.join(KLASOR_ADI, f"yemeksepeti_veri_{vendor_id}.json")
    if os.path.exists(dosya_yolu): return
    print(f"✅ Yemeksepeti Restoran ID: {vendor_id}")
    tum_yorumlar = []
    headers = {"Accept": "application/json, text/plain, */*", "Origin": "https://www.yemeksepeti.com", "Referer": restoran_linki}
    next_page_key = ""

    for sayfa in range(max_sayfa):
        api_url = f"https://reviews-api-tr.fd-api.com/reviews/vendor/{vendor_id}?global_entity_id=YS_TR&limit=50&has_dish=true"
        if next_page_key: api_url += f"&nextPageKey={urllib.parse.quote(next_page_key)}"
        try:
            response = requests.get(api_url, headers=headers, impersonate="chrome120", timeout=15, verify=False)
            if response.status_code != 200: break
            data = response.json()
            yorum_listesi = data.get("data", [])
            if not yorum_listesi: yorum_listesi = yemeksepeti_yorum_bul(data)
            if not yorum_listesi: break
            tum_yorumlar.extend(yorum_listesi)
            print(f"   -> Sayfa {sayfa} çekildi. (+{len(yorum_listesi)} yorum)")
            yeni_next_page_key = data.get("pageKey")
            if not yeni_next_page_key or yeni_next_page_key == next_page_key: break
            next_page_key = yeni_next_page_key
            time.sleep(0.5)
        except Exception: break

    if len(tum_yorumlar) > 0:
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")

# ==========================================
# 6. TRENDYOL GO API FONKSİYONU
# ==========================================
def trendyol_go_api_cek(restoran_linki, max_sayfa):
    match = re.search(r'(?:-|/)(\d+)(?:/|\?|$)', restoran_linki)
    if not match: return
    vendor_id = match.group(1)
    dosya_yolu = os.path.join(KLASOR_ADI, f"trendyol_go_veri_{vendor_id}.json")
    if os.path.exists(dosya_yolu): return
    print(f"✅ Trendyol Go Restoran ID: {vendor_id}")
    tum_yorumlar = []
    headers = {"Accept": "application/json, text/plain, */*", "Origin": "https://www.trendyol.com", "Referer": restoran_linki}

    for sayfa in range(1, max_sayfa + 1):
        api_url = f"https://api.tgoapis.com/web-restaurant-apirestaurant-santral/restaurants/{vendor_id}/comments?page={sayfa}&pageSize=20&latitude=41.07087&longitude=28.996586&tagVersion=2"
        try:
            response = requests.get(api_url, headers=headers, impersonate="chrome120", timeout=15, verify=False)
            if response.status_code != 200: break
            yorum_listesi = trendyol_go_yorum_bul(response.json())
            if not yorum_listesi: break
            tum_yorumlar.extend(yorum_listesi)
            print(f"   -> Sayfa {sayfa} çekildi. (+{len(yorum_listesi)} yorum)")
            time.sleep(0.5)
        except Exception: break

    if len(tum_yorumlar) > 0:
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")

# ==========================================
# 7. ETSTUR API FONKSİYONU (GÜNCEL YENİ)
# ==========================================
def etstur_api_cek(otel_linki, max_sayfa):
    print("🔍 Etstur sayfası analiz ediliyor, gizli ID'ler aranıyor...")

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        html_res = requests.get(otel_linki, headers=headers, impersonate="chrome120", timeout=15, verify=False)

        if html_res.status_code != 200:
            print(f"❌ Hata: Sayfa açılamadı (Durum Kodu: {html_res.status_code})")
            return

        html_text = html_res.text

        # 1. PLAN: span etiketi içindeki data-* özelliklerinden çekmek (En temiz yol)
        hotel_id_match = re.search(r'data-hotel-id=["\']([^"\']+)["\']', html_text)
        hotel_code_match = re.search(r'data-vendor-code=["\']([^"\']+)["\']', html_text)

        # 2. PLAN: Eğer span yoksa, NEXT_DATA JSON yapısının içinden çekmek (Yedek)
        if not hotel_id_match:
            hotel_id_match = re.search(r'"hotelId"\s*:\s*["\']([^"\']+)["\']', html_text)
        if not hotel_code_match:
            hotel_code_match = re.search(r'"vndCode"\s*:\s*["\']([^"\']+)["\']', html_text)

        if not hotel_code_match or not hotel_id_match:
            print("❌ Hata: Otel ID'leri sitenin HTML kodlarından çıkarılamadı.")
            return

        hotel_code = hotel_code_match.group(1)
        hotel_id = hotel_id_match.group(1)
        print(f"✅ Etstur Otel Kod: {hotel_code} | Otel ID: {hotel_id}")

    except Exception as e:
        print(f"❌ Sayfa analizinde hata: {e}")
        return

    dosya_yolu = os.path.join(KLASOR_ADI, f"etstur_veri_{hotel_code}.json")
    if os.path.exists(dosya_yolu):
        print(f"⚠️ DİKKAT: Bu otel ({hotel_code}) daha önceden çekilmiş! İşlem atlanıyor.")
        return

    tum_yorumlar = []
    api_url = "https://www.etstur.com/services/api/review"
    api_headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.etstur.com",
        "Referer": otel_linki
    }

    for sayfa in range(max_sayfa):
        payload = {
            "hotelCode": hotel_code,
            "hotelId": hotel_id,
            "offset": sayfa,
            "sort": "BOOKING_DESC",
            "period": "",
            "categoryType": "OVERALL",
            "searchText": ""
        }

        try:
            response = requests.post(api_url, headers=api_headers, json=payload, impersonate="chrome120", timeout=15, verify=False)
            if response.status_code != 200:
                print(f"⚠️ API Hatası (Kod: {response.status_code})")
                break

            data = response.json()
            yorum_listesi = data.get("reviews", [])
            if not yorum_listesi: yorum_listesi = etstur_yorum_bul(data)
            if not yorum_listesi:
                print("ℹ️ Bu sayfada başka yorum bulunamadı. (Sayfa sonu)")
                break

            tum_yorumlar.extend(yorum_listesi)
            print(f"   -> Sayfa {sayfa} çekildi. (+{len(yorum_listesi)} yorum)")
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ İstek sırasında hata oluştu: {e}")
            break

    if len(tum_yorumlar) > 0:
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")
    else:
        print(f"⚠️ Yorum bulunamadığı (veya ağ engeline takıldığı) için dosya oluşturulmadı.\n")
# ==========================================
# 8. ANA YÖNLENDİRİCİ (ROUTER) FONKSİYON
# ==========================================

def link_analiz_et_ve_cek(url, max_sayfa=5):
    print(f"🔗 Link inceleniyor: {url}")
    url_lower = url.lower()

    if "trendyol-yemek" in url_lower or "hizli-market" in url_lower or "tgoapis" in url_lower or "tgoyemek.com" in url_lower:
        print("🛵 Platform: TRENDYOL GO (YEMEK/MARKET)")
        trendyol_go_api_cek(url, max_sayfa)

    elif "trendyol.com" in url_lower:
        print("🛍️ Platform: TRENDYOL (E-TİCARET)")
        trendyol_api_cek(url, max_sayfa)

    elif "hepsiburada.com" in url_lower:
        print("🛍️ Platform: HEPSİBURADA")
        hepsiburada_api_cek(url, max_sayfa)

    elif "steampowered.com" in url_lower:
        print("🎮 Platform: STEAM")
        steam_api_cek(url, max_sayfa)

    elif "yemeksepeti.com" in url_lower:
        print("🍔 Platform: YEMEKSEPETİ")
        yemeksepeti_api_cek(url, max_sayfa)

    elif "etstur.com" in url_lower:
        print("🏨 Platform: ETSTUR")
        etstur_api_cek(url, max_sayfa)

    else:
        print("❌ Hata: Tanınmayan platform! Lütfen desteklenen bir link giriniz.\n")

# ==========================================
# TEST BÖLÜMÜ
# ==========================================
if __name__ == "__main__":
    test_linkleri = [
        "https://www.etstur.com/Vikingen-Infinity-Resort-Spa"
    ]

    for link in test_linkleri:
        link_analiz_et_ve_cek(link, max_sayfa=20)