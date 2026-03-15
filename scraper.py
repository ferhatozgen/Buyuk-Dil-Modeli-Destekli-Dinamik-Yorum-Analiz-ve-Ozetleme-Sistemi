from curl_cffi import requests
from playwright.sync_api import sync_playwright
import urllib.request
import urllib.parse
import subprocess
import base64
import json
import time
import os
import re

# ==========================================
# 1. KLASÖRLEME VE PROFİL AYARLARI
# ==========================================
ANA_KLASOR = "cekilen_veriler"
os.makedirs(ANA_KLASOR, exist_ok=True)

# Google Maps Playwright için özel oturum profili
PROFIL_KLASORU = os.path.join(os.getcwd(), "google_otomasyon_profili")

# ==========================================
# 2. ORTAK YARDIMCI FONKSİYONLAR (CURL_CFFI)
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
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict):
        if "text" in json_verisi[0] or "comment" in json_verisi[0] or "reviewText" in json_verisi[0] or "customer" in json_verisi[0]:
            return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = etstur_yorum_bul(deger)
            if sonuc: return sonuc
    return []

def airbnb_yorum_bul(json_verisi):
    try:
        reviews_data = json_verisi.get("data", {}).get("presentation", {}).get("stayProductDetailPage", {}).get("reviews", {}).get("reviews", [])
        if reviews_data: return reviews_data
    except Exception: pass
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict):
        if "comments" in json_verisi[0] or "commentV2" in json_verisi[0]: return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = airbnb_yorum_bul(deger)
            if sonuc: return sonuc
    return []

# ==========================================
# 3. PLATFORM FONKSİYONLARI (CURL_CFFI)
# ==========================================
def trendyol_api_cek(urun_linki, max_sayfa):
    match = re.search(r'-p-(\d+)', urun_linki)
    if not match: return
    urun_id = match.group(1)
    klasor = os.path.join(ANA_KLASOR, "trendyol")
    os.makedirs(klasor, exist_ok=True)
    dosya_yolu = os.path.join(klasor, f"trendyol_veri_{urun_id}.json")
    if os.path.exists(dosya_yolu):
        print(f"⚠️ Atlandı: {urun_id} zaten mevcut.")
        return
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
            print(f"   -> Sayfa {sayfa} çekildi.")
            time.sleep(0.5)
        except Exception: break
    if tum_yorumlar:
        with open(dosya_yolu, "w", encoding="utf-8") as f: json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")

def hepsiburada_api_cek(urun_linki, max_sayfa):
    match = re.search(r'-p[m]?-([A-Za-z0-9]+)', urun_linki)
    if not match: return
    urun_sku = match.group(1).upper()
    klasor = os.path.join(ANA_KLASOR, "hepsiburada")
    os.makedirs(klasor, exist_ok=True)
    dosya_yolu = os.path.join(klasor, f"hb_veri_{urun_sku}.json")
    if os.path.exists(dosya_yolu):
        print(f"⚠️ Atlandı: {urun_sku} zaten mevcut.")
        return
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
            print(f"   -> Offset {offset} çekildi.")
            time.sleep(1)
        except Exception: break
    if tum_yorumlar:
        with open(dosya_yolu, "w", encoding="utf-8") as f: json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")

def steam_api_cek(oyun_linki, max_sayfa):
    match = re.search(r'/app/(\d+)', oyun_linki)
    if not match: return
    app_id = match.group(1)
    klasor = os.path.join(ANA_KLASOR, "steam")
    os.makedirs(klasor, exist_ok=True)
    dosya_yolu = os.path.join(klasor, f"steam_veri_{app_id}.json")
    if os.path.exists(dosya_yolu):
        print(f"⚠️ Atlandı: {app_id} zaten mevcut.")
        return
    print(f"✅ Steam App ID: {app_id}")
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
            print(f"   -> Sayfa {sayfa} çekildi.")
            yeni_cursor = data.get("cursor")
            if not yeni_cursor or yeni_cursor == cursor: break
            cursor = yeni_cursor
            time.sleep(0.5)
        except Exception: break
    if tum_yorumlar:
        with open(dosya_yolu, "w", encoding="utf-8") as f: json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")

def yemeksepeti_api_cek(restoran_linki, max_sayfa):
    match = re.search(r'/restaurant/([a-zA-Z0-9]+)', restoran_linki)
    if not match: return
    vendor_id = match.group(1)
    klasor = os.path.join(ANA_KLASOR, "yemeksepeti")
    os.makedirs(klasor, exist_ok=True)
    dosya_yolu = os.path.join(klasor, f"yemeksepeti_veri_{vendor_id}.json")
    if os.path.exists(dosya_yolu):
        print(f"⚠️ Atlandı: {vendor_id} zaten mevcut.")
        return
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
            print(f"   -> Sayfa {sayfa} çekildi.")
            yeni_next_page_key = data.get("pageKey")
            if not yeni_next_page_key or yeni_next_page_key == next_page_key: break
            next_page_key = yeni_next_page_key
            time.sleep(0.5)
        except Exception: break
    if tum_yorumlar:
        with open(dosya_yolu, "w", encoding="utf-8") as f: json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")

def trendyol_go_api_cek(restoran_linki, max_sayfa):
    match = re.search(r'(?:-|/)(\d+)(?:/|\?|$)', restoran_linki)
    if not match: return
    vendor_id = match.group(1)
    klasor = os.path.join(ANA_KLASOR, "trendyol_go")
    os.makedirs(klasor, exist_ok=True)
    dosya_yolu = os.path.join(klasor, f"trendyol_go_veri_{vendor_id}.json")
    if os.path.exists(dosya_yolu):
        print(f"⚠️ Atlandı: {vendor_id} zaten mevcut.")
        return
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
            print(f"   -> Sayfa {sayfa} çekildi.")
            time.sleep(0.5)
        except Exception: break
    if tum_yorumlar:
        with open(dosya_yolu, "w", encoding="utf-8") as f: json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")

def etstur_api_cek(otel_linki, max_sayfa):
    print("🔍 Etstur gizli ID'leri aranıyor...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    try:
        html_res = requests.get(otel_linki, headers=headers, impersonate="chrome120", timeout=15, verify=False)
        if html_res.status_code != 200: return
        hotel_id_match = re.search(r'data-hotel-id=["\']([^"\']+)["\']', html_res.text) or re.search(r'"hotelId"\s*:\s*["\']([^"\']+)["\']', html_res.text)
        hotel_code_match = re.search(r'data-vendor-code=["\']([^"\']+)["\']', html_res.text) or re.search(r'"vndCode"\s*:\s*["\']([^"\']+)["\']', html_res.text)
        if not hotel_code_match or not hotel_id_match: return
        hotel_code = hotel_code_match.group(1)
        hotel_id = hotel_id_match.group(1)
    except Exception: return

    klasor = os.path.join(ANA_KLASOR, "etstur")
    os.makedirs(klasor, exist_ok=True)
    dosya_yolu = os.path.join(klasor, f"etstur_veri_{hotel_code}.json")
    if os.path.exists(dosya_yolu):
        print(f"⚠️ Atlandı: {hotel_code} zaten mevcut.")
        return
    print(f"✅ Etstur Otel Kod: {hotel_code}")

    tum_yorumlar = []
    api_url = "https://www.etstur.com/services/api/review"
    api_headers = {"Content-Type": "application/json", "Origin": "https://www.etstur.com", "Referer": otel_linki}
    for sayfa in range(max_sayfa):
        payload = {"hotelCode": hotel_code, "hotelId": hotel_id, "offset": sayfa, "sort": "BOOKING_DESC", "period": "", "categoryType": "OVERALL", "searchText": ""}
        try:
            response = requests.post(api_url, headers=api_headers, json=payload, impersonate="chrome120", timeout=15, verify=False)
            if response.status_code != 200: break
            data = response.json()
            yorum_listesi = data.get("reviews", [])
            if not yorum_listesi: yorum_listesi = etstur_yorum_bul(data)
            if not yorum_listesi: break
            tum_yorumlar.extend(yorum_listesi)
            print(f"   -> Sayfa {sayfa} çekildi.")
            time.sleep(0.5)
        except Exception: break
    if tum_yorumlar:
        with open(dosya_yolu, "w", encoding="utf-8") as f: json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")

def airbnb_api_cek(oda_linki, max_sayfa):
    match = re.search(r'/rooms/(\d+)', oda_linki)
    if not match: return
    oda_id = match.group(1)
    klasor = os.path.join(ANA_KLASOR, "airbnb")
    os.makedirs(klasor, exist_ok=True)
    dosya_yolu = os.path.join(klasor, f"airbnb_veri_{oda_id}.json")
    if os.path.exists(dosya_yolu):
        print(f"⚠️ Atlandı: {oda_id} zaten mevcut.")
        return

    print(f"✅ Airbnb Oda ID: {oda_id}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36", "Accept-Language": "tr-TR,tr;q=0.9"}
    try:
        html_res = requests.get(oda_linki, headers=headers, impersonate="chrome120", timeout=15, verify=False)
        api_key_match = re.search(r'"api_config"\s*:\s*{[^}]*"key"\s*:\s*"([^"]+)"', html_res.text)
        if not api_key_match: return
        api_key = api_key_match.group(1)
    except Exception: return

    tum_yorumlar = []
    base64_id = base64.b64encode(f"StayListing:{oda_id}".encode('utf-8')).decode('utf-8')
    sha256Hash = "2ed951bfedf71b87d9d30e24a419e15517af9fbed7ac560a8d1cc7feadfa22e6"
    api_headers = {"Accept": "application/json", "x-airbnb-api-key": api_key, "User-Agent": headers["User-Agent"], "Origin": "https://www.airbnb.com.tr", "Referer": oda_linki}

    for sayfa in range(max_sayfa):
        limit = 24 if sayfa == 0 else 10
        offset = 0 if sayfa == 0 else 24 + ((sayfa - 1) * 10)
        variables = {"id": base64_id, "pdpReviewsRequest": {"fieldSelector": "for_p3_translation_only", "forPreview": False, "limit": limit, "offset": str(offset), "showingTranslationButton": False, "first": limit, "sortingPreference": "BEST_QUALITY"}}
        extensions = {"persistedQuery": {"version": 1, "sha256Hash": sha256Hash}}
        params = {"operationName": "StaysPdpReviewsQuery", "locale": "tr", "currency": "TRY", "variables": json.dumps(variables, separators=(',', ':')), "extensions": json.dumps(extensions, separators=(',', ':'))}

        full_url = f"https://www.airbnb.com.tr/api/v3/StaysPdpReviewsQuery/{sha256Hash}?{urllib.parse.urlencode(params)}"
        try:
            response = requests.get(full_url, headers=api_headers, impersonate="chrome120", timeout=15, verify=False)
            if response.status_code != 200: break
            yorum_listesi = airbnb_yorum_bul(response.json())
            if not yorum_listesi: break
            tum_yorumlar.extend(yorum_listesi)
            print(f"   -> Sayfa {sayfa} (Offset: {offset}) çekildi.")
            time.sleep(1.5)
        except Exception: break

    if tum_yorumlar:
        with open(dosya_yolu, "w", encoding="utf-8") as f: json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")

# ==========================================
# 4. GOOGLE MAPS FONKSİYONLARI (PLAYWRIGHT)
# ==========================================
def chrome_hazirla():
    try:
        urllib.request.urlopen("http://localhost:9222/json/version", timeout=1)
    except Exception:
        print("⚙️ Chrome kapalı. CDP Hijacking için otomatik başlatılıyor...")
        chrome_yolu = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        komut = f'"{chrome_yolu}" --remote-debugging-port=9222 --user-data-dir="{PROFIL_KLASORU}"'
        subprocess.Popen(komut, shell=True)
        time.sleep(4)

def maps_playwright_cek(mekan_linki, hedef_kaydirma_sayisi=10):
    match = re.search(r'(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)', mekan_linki)
    if not match: return
    mekan_id = match.group(1).replace(":", "_")
    klasor = os.path.join(ANA_KLASOR, "google_maps")
    os.makedirs(klasor, exist_ok=True)
    dosya_yolu = os.path.join(klasor, f"maps_veri_{mekan_id}.json")

    if os.path.exists(dosya_yolu):
        print(f"⚠️ Atlandı: {mekan_id} zaten mevcut.")
        return

    chrome_hazirla()
    print(f"🚀 CDP Hijacking Başlıyor (Google Maps): {mekan_id}")
    tum_yorumlar = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
        except Exception:
            print("❌ Chrome'a bağlanılamadı. Kapatıp tekrar deneyin.")
            return

        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        page.goto(mekan_linki, wait_until="domcontentloaded")
        time.sleep(3)

        try:
            page.locator("button:has-text('Yorumlar'), button:has-text('Reviews')").first.click(timeout=8000)
            time.sleep(2)
            page.wait_for_selector('.wiI7pd', timeout=8000)
        except Exception:
            print("⚠️ Yorum sekmesi/metinleri bulunamadı.")
            return

        try: page.locator('.wiI7pd').first.hover(timeout=5000)
        except Exception: pass

        for i in range(hedef_kaydirma_sayisi):
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(1500)
            print(f"   -> Kaydırma işlemi: {i+1}/{hedef_kaydirma_sayisi}")

        yorum_kutulari = page.locator('.jftiEf').all()
        for kutu in yorum_kutulari:
            try:
                metin = kutu.locator('.wiI7pd').inner_text().replace('\n', ' ').strip() if kutu.locator('.wiI7pd').count() > 0 else ""
                if len(metin) < 15: continue
                isim = kutu.locator('.d4r55').inner_text().strip() if kutu.locator('.d4r55').count() > 0 else "Bilinmiyor"
                puan = kutu.locator('.kvMYJc').get_attribute('aria-label') if kutu.locator('.kvMYJc').count() > 0 else "Bilinmiyor"
                tarih = kutu.locator('.rsqaWe').inner_text().strip() if kutu.locator('.rsqaWe').count() > 0 else "Bilinmiyor"
                tum_yorumlar.append({"isim": isim, "puan": puan, "tarih": tarih, "metin": metin})
            except Exception: pass

    if tum_yorumlar:
        with open(dosya_yolu, "w", encoding="utf-8") as f: json.dump(tum_yorumlar, f, ensure_ascii=False, indent=4)
        print(f"🎉 Kaydedildi: '{dosya_yolu}' ({len(tum_yorumlar)} yorum)\n")

# ==========================================
# 5. ANA YÖNLENDİRİCİ (ROUTER)
# ==========================================
def link_analiz_et_ve_cek(url, sayfa_veya_kaydirma_sayisi=5):
    print(f"🔗 Link inceleniyor: {url}")
    url_lower = url.lower()

    if "trendyol-yemek" in url_lower or "hizli-market" in url_lower or "tgoapis" in url_lower or "tgoyemek.com" in url_lower:
        print("🛵 Platform: TRENDYOL GO")
        trendyol_go_api_cek(url, sayfa_veya_kaydirma_sayisi)

    elif "trendyol.com" in url_lower:
        print("🛍️ Platform: TRENDYOL")
        trendyol_api_cek(url, sayfa_veya_kaydirma_sayisi)

    elif "hepsiburada.com" in url_lower:
        print("🛍️ Platform: HEPSİBURADA")
        hepsiburada_api_cek(url, sayfa_veya_kaydirma_sayisi)

    elif "steampowered.com" in url_lower:
        print("🎮 Platform: STEAM")
        steam_api_cek(url, sayfa_veya_kaydirma_sayisi)

    elif "yemeksepeti.com" in url_lower:
        print("🍔 Platform: YEMEKSEPETİ")
        yemeksepeti_api_cek(url, sayfa_veya_kaydirma_sayisi)

    elif "etstur.com" in url_lower:
        print("🏨 Platform: ETSTUR")
        etstur_api_cek(url, sayfa_veya_kaydirma_sayisi)

    elif "airbnb.com" in url_lower:
        print("🏠 Platform: AIRBNB")
        airbnb_api_cek(url, sayfa_veya_kaydirma_sayisi)

    elif "google" in url_lower and ("maps" in url_lower or "place" in url_lower):
        print("📍 Platform: GOOGLE MAPS")
        # Google Maps için sayfa sayısını scroll sayısına dönüştürüyoruz (Örn: 5 sayfa = 5 kaydırma)
        maps_playwright_cek(url, hedef_kaydirma_sayisi=sayfa_veya_kaydirma_sayisi)

    else:
        print("❌ Hata: Tanınmayan platform! Lütfen desteklenen bir link giriniz.\n")

# ==========================================
# TEST BÖLÜMÜ
# ==========================================
if __name__ == "__main__":
    test_linkleri = [
        "https://store.steampowered.com/app/3764200/Resident_Evil_Requiem/"




    ]
    for link in test_linkleri:
        # Tüm platformlar için ortak olarak 5 sayfalık (veya 5 kaydırmalık) veri çeker.
        # İstersen bu sayıyı 10, 20 gibi artırarak veri setini devasa boyutlara ulaştırabilirsin.
        link_analiz_et_ve_cek(link, sayfa_veya_kaydirma_sayisi=10)