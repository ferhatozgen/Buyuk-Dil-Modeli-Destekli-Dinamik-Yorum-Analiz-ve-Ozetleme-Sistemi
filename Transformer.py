from datetime import datetime
from uuid import uuid4
import os
import json
import re
import urllib.parse
from typing import Tuple, List, Dict
from logger import setup_logger





def process_airbnb_data(raw_json: dict) -> tuple[dict, list[dict]]:
    product_uuid = str(uuid4())
    orijinal_url = raw_json.get("link", "")
    platform = "airbnb"

    urun_paket = {
        "id": product_uuid,
        "platform": None,
        "platform_id": None,
        "product_name": raw_json.get("baslik"),
        "image_url": raw_json.get("gorsel_url"),
        "category": None,
        "original_url": None,
        "url_hash": None,
        "status": "active",
        "click_count": 0,
        "avg_orj_score": None, # altta hesaplamasını yapıldı(halit-fero)!
        "avg_model_score": None,
        "guncel_ozet": None,
        "created_at": datetime.now(),
        "last_updated_at": datetime.now()
    }

    ham_yorumlar = raw_json.get("yorumlar", [])
    ratings = [y.get("rating") for y in ham_yorumlar if isinstance(y.get("rating"), (int, float))]
    if ratings:
        urun_paket["avg_orj_score"] = round(sum(ratings) / len(ratings), 2)

    review_packets = []
    for raw_review in ham_yorumlar:
        metadata = {
            "rate": raw_review.get("rating"),
            "misafirin_ulkesi": raw_review.get("localizedReviewerLocation"),
            "konaklama_tipi": raw_review.get("reviewHighlight"),
        }

        review_packets.append({
            "product_id": product_uuid,
            "original_rating": raw_review.get("rating"),
            "predicted_score": None,
            "raw_text": raw_review.get("comment"),
            "clean_text": raw_review.get("temiz_metin"),
            "metadata": metadata,
            "created_at": datetime.now()
        })

    return urun_paket, review_packets


def process_ciceksepeti_data(raw_json: dict) -> tuple[dict, list[dict]]:
    product_uuid = str(uuid4())
    orijinal_url = raw_json.get("link", "")
    platform = "ciceksepeti"

    urun_paket = {
        "id": product_uuid,
        "platform": None,
        "platform_id": None,
        "product_name": raw_json.get("baslik"),
        "image_url": raw_json.get("gorsel_url"),
        "category": None,  # SetFit ile dolacak
        "original_url": None,
        "url_hash": None,
        "status": "active",
        "click_count": 0,
        "avg_orj_score": None,  # Altta hesaplanacak
        "avg_model_score": None,
        "guncel_ozet": None,
        "created_at": datetime.now(),
        "last_updated_at": datetime.now()
    }

    ham_yorumlar = raw_json.get("yorumlar", [])

    # Çiçeksepeti'nde puan "5 Yıldız" şeklinde geldiği için ilk karakteri alıp int'e çeviriyoruz
    ratings = []
    for y in ham_yorumlar:
        puan_str = y.get("puan") or y.get("rating")
        if puan_str and puan_str[0].isdigit():
            ratings.append(int(puan_str[0]))

    if ratings:
        urun_paket["avg_orj_score"] = round(sum(ratings) / len(ratings), 2)

    review_packets = []
    for raw_review in ham_yorumlar:
        # Çiçeksepeti'ne özel metadata bilgileri
        metadata = {
            "kullanici_adi": raw_review.get("isim"),
            "yorum_tarihi": raw_review.get("tarih"),
            "verilen_puan_str": raw_review.get("puan")
        }

        # Puanı sayısal olarak da review bazlı saklayalım
        current_rating = None
        if raw_review.get("puan") and raw_review.get("puan")[0].isdigit():
            current_rating = int(raw_review.get("puan")[0])

        review_packets.append({
            "product_id": product_uuid,
            "original_rating": current_rating,
            "predicted_score": None,  # NLP modelinden gelecek
            "raw_text": raw_review.get("orijinal_metin"),  # Scraper'daki ham metin
            "clean_text": raw_review.get("temiz_metin"),  # Preprocessor'dan geçmiş metin
            "metadata": metadata,
            "created_at": datetime.now()
        })

    return urun_paket, review_packets



"""
tuple[dict, list[dict]] örneği:
(
  {"id": "...", "urun_adi": "...", ...},      ===========> dict yapısı
  [ {"id": "...", "yorum_metni": "...", ...}, {"id": "...", ...} ]   ======> list[dict] yapısı
)

"""
def process_etstur_data(raw_json: dict) -> tuple[dict, list[dict]]:
    product_uuid = str(uuid4())           #her calıstırıldıgında tamamen yeni ve bagımsız üretiliyor
    orijinal_url = raw_json.get("link", "")
    platform = "etstur"

    urun_paket = {
        "id": product_uuid,
        "platform": None,
        "platform_id": None,
        "product_name": raw_json.get("baslik"),
        "image_url": raw_json.get("gorsel_url"),
        "category": None,  # SetFit ile dolacak
        "original_url": None,
        "url_hash": None,
        "status": "active",
        "click_count": 0,
        "avg_orj_score": None,  # Altta hesaplanacak
        "avg_model_score": None,
        "guncel_ozet": None,
        "created_at": datetime.now(),
        "last_updated_at": datetime.now()
    }

    ham_yorumlar = raw_json.get("yorumlar", [])

    # Etstur 100 üzerinden puan verdiği için standardımız olan 5'li sisteme çeviriyoruz (puan / 20)
    ratings = [float(y.get("score")) / 20 for y in ham_yorumlar if isinstance(y.get("score"), (int, float))
    ]

    if ratings:
        urun_paket["avg_orj_score"] = round(sum(ratings) / len(ratings), 2)

    review_packets = []
    for raw_review in ham_yorumlar:
        # Etstur'un detaylı alt puanlarını (Temizlik, Hizmet vb.) çekiyoruz
        alt_puanlar_listesi = raw_review.get("ratingTypes") or []
        alt_kategori_puanlari = {
            item.get("name"): (float(item.get("score")) / 2 if isinstance(item.get("score"), (int, float)) else None)
            for item in alt_puanlar_listesi
        }

        metadata = {
            "verilen_puan_100": raw_review.get("score"),
            "tavsiye_ediyor_mu": raw_review.get("recommendation"),
            "misafir_tipi": raw_review.get("guestType"),  # Aile, Tek, Çift vb.
            "oda_tipi": raw_review.get("roomName"),
            "detaylı_puanlar": alt_kategori_puanlari
        }

        # Bireysel yorum puanını da 5 üzerinden normalize ederek saklayalım
        current_rating = float(raw_review.get("score")) / 20 if isinstance(raw_review.get("score"),
                                                                           (int, float)) else None

        review_packets.append({
            "product_id": product_uuid,
            "original_rating": current_rating,
            "predicted_score": None,  # NLP modelinden gelecek
            "raw_text": raw_review.get("temiz_metin"),  # Etstur API genelde temiz metin döner
            "clean_text": raw_review.get("temiz_metin"),
            "metadata": metadata,
            "created_at": datetime.now()
        })

    return urun_paket, review_packets

def process_hepsiburada_data(raw_json: dict) -> tuple[dict, list[dict]]:
    product_uuid = str(uuid4())
    orijinal_url = raw_json.get("link", "")
    platform = "hepsiburada"

    urun_paket = {
        "id": product_uuid,
        "platform": None,
        "platform_id": None,
        "product_name": raw_json.get("baslik"),
        "image_url": raw_json.get("gorsel_url"),
        "category": None,
        "original_url": None,
        "url_hash": None,
        "status": "active",
        "click_count": 0,
        "avg_orj_score": None,
        "avg_model_score": None,
        "guncel_ozet": None,
        "created_at": datetime.now(),
        "last_updated_at": datetime.now()
    }

    ham_yorumlar = raw_json.get("yorumlar", [])
    ratings = [y.get("star") for y in ham_yorumlar if isinstance(y.get("star"), (int, float))]
    if ratings:
        urun_paket["avg_orj_score"] = round(sum(ratings) / len(ratings), 2)

    review_packets = []
    for raw_review in ham_yorumlar:
        order_info = raw_review.get("order") or {}
        reaction_info = raw_review.get("reactions") or {}

        metadata = {
            "satici_adi": order_info.get("merchantName"),
            "dogrulanmis_satin_alim": raw_review.get("isPurchaseVerified"),
            "beden_kalibi": raw_review.get("mould"),
            "faydali_bulma_sayisi": reaction_info.get("clap", 0),
        }

        review_packets.append({
            "product_id": product_uuid,
            "original_rating": raw_review.get("star"),
            "predicted_score": None,
            "raw_text": raw_review.get("review", {}).get("content", ""), # Scraper yapına göre
            "clean_text": raw_review.get("temiz_metin"),
            "metadata": metadata,
            "created_at": datetime.now()
        })

    return urun_paket, review_packets

def process_maps_data(raw_json: dict) -> tuple[dict, list[dict]]:
    product_uuid = str(uuid4())
    orijinal_url = raw_json.get("link", "")
    platform = "maps"

    urun_paket = {
        "id": product_uuid,
        "platform": None,
        "platform_id": None,
        "product_name": raw_json.get("baslik"),
        "image_url": raw_json.get("gorsel_url"),
        "category": None,
        "original_url": None,
        "url_hash": None,
        "status": "active",
        "click_count": 0,
        "avg_orj_score": None,
        "avg_model_score": None,
        "guncel_ozet": None,
        "created_at": datetime.now(),
        "last_updated_at": datetime.now()
    }

    ham_yorumlar = raw_json.get("yorumlar", [])
    ratings = []
    for y in ham_yorumlar:
        puan_str = y.get("puan", "")
        if puan_str and puan_str[0].isdigit():
            ratings.append(int(puan_str[0]))

    if ratings:
        urun_paket["avg_orj_score"] = round(sum(ratings) / len(ratings), 2)

    review_packets = []
    for raw_review in ham_yorumlar:
        # Maps metadata'sı bazen boş olabilir ama yapıyı bozmamak için tutuyoruz
        metadata = {
            "isim": raw_review.get("isim"),
            "tarih_metni": raw_review.get("tarih"),
            "ham_puan_metni": raw_review.get("puan")
        }

        current_rating = None
        if raw_review.get("puan") and raw_review.get("puan")[0].isdigit():
            current_rating = int(raw_review.get("puan")[0])

        review_packets.append({
            "product_id": product_uuid,
            "original_rating": current_rating,
            "predicted_score": None,
            "raw_text": raw_review.get("orijinal_metin"),
            "clean_text": raw_review.get("temiz_metin"),
            "metadata": metadata,
            "created_at": datetime.now()
        })

    return urun_paket, review_packets


def process_steam_data(raw_json: dict) -> tuple[dict, list[dict]]:
    product_uuid = str(uuid4())
    orijinal_url = raw_json.get("link", "")
    platform = "steam"

    urun_paket = {
        "id": product_uuid,
        "platform": None,
        "platform_id": None,
        "product_name": raw_json.get("baslik"),
        "image_url": raw_json.get("gorsel_url"),
        "category": "Oyun",  # Steam her zaman oyun olduğu için statik verebiliriz
        "original_url": None,
        "url_hash": None,
        "status": "active",
        "click_count": 0,
        "avg_orj_score": None,
        "avg_model_score": None,
        "guncel_ozet": None,
        "created_at": datetime.now(),
        "last_updated_at": datetime.now()
    }

    ham_yorumlar = raw_json.get("yorumlar", [])

    # Senin zekice kurguladığın oranlama mantığı:
    if ham_yorumlar:
        olumlu_sayisi = sum(1 for y in ham_yorumlar if y.get("voted_up") is True)
        oran = olumlu_sayisi / len(ham_yorumlar)
        # Oranı 5'lik sisteme çekip 0.5 katlarına yuvarlıyoruz
        urun_paket["avg_orj_score"] = round((oran * 5) * 2) / 2
    else:
        urun_paket["avg_orj_score"] = None

    review_packets = []
    for raw_review in ham_yorumlar:
        author_info = raw_review.get("author") or {}

        metadata = {
            "voted_up": raw_review.get("voted_up"),  # True/False
            "oynanma_suresi_dakika": author_info.get("playtime_forever"),
            "faydali_bulma_sayisi": raw_review.get("votes_up", 0)
        }

        # Bireysel yorum puanı Steam'de 5 veya 1 olarak (T/F) tutulabilir
        individual_rating = 5 if raw_review.get("voted_up") else 1

        review_packets.append({
            "product_id": product_uuid,
            "original_rating": individual_rating,
            "predicted_score": None,
            "raw_text": raw_review.get("review"),  # Steam API'de yorum genelde 'review' anahtarındadır
            "clean_text": raw_review.get("temiz_metin"),
            "metadata": metadata,
            "created_at": datetime.now()
        })

    return urun_paket, review_packets

def process_trendyol_data(raw_json:dict) -> tuple[dict, list[dict]]:
    product_uuid = str(uuid4())
    orijinal_url = raw_json.get("link","")
    platform="trendyol"

    urun_paket = {
        "id": product_uuid,
        "platform": None,
        "platform_id": None,
        "product_name": raw_json.get("baslik"),
        "image_url": raw_json.get("gorsel_url"),
        "category": None, #setfit ile dolacak
        "original_url": None,
        "url_hash": None,
        "status":"active",
        "click_count": 0,
        "avg_orj_score": None,   #aşagıda hesaplanacak
        "avg_model_score": None, #modelimizin skoru
        "guncel_ozet": None,
        "created_at": datetime.now(),
        "last_updated_at": datetime.now()
    }

    ham_yorumlar = raw_json.get("yorumlar", [])
    ratings = [y.get("rate") for y in ham_yorumlar if isinstance(y.get("rate"), (int, float))]
    if ratings:
        urun_paket["avg_orj_score"] = round(sum(ratings) / len(ratings), 2) #vt de decimal(3,2) olarak bekliyoruz.

    review_packets = []
    for raw_review in ham_yorumlar:
        metadata = {
            "media_files": raw_review.get("mediaFiles"),   #yorum yapan kişinin fotoğraf paylaşıp paylaşmadığı
            "seller_info": raw_review.get("seller"),
            "rate": raw_review.get("rate"),
            "is_trusted": raw_review.get("trusted"),
            "likesCount": raw_review.get("likesCount"),
        }

        review_packets.append({
            "product_id": product_uuid,
            "original_rating": raw_review.get("rate"),
            "predicted_score": None,  # NLP modelinden gelecek
            "raw_text": raw_review.get("metin") or raw_review.get("comment"),  # Scraper'daki ham alan
            "clean_text": raw_review.get("temiz_metin"),
            "metadata": metadata,
            "created_at": datetime.now()
        })

    return urun_paket, review_packets

def process_tygo_data(raw_json: dict) -> tuple[dict, list[dict]]:
    product_uuid = str(uuid4())
    orijinal_url = raw_json.get("link", "")
    platform = "trendyol-go"

    urun_paket = {
        "id": product_uuid,
        "platform": None,
        "platform_id": None,
        "product_name": raw_json.get("baslik"),
        "image_url": raw_json.get("gorsel_url"),
        "category": "Restoran", # TyGo genelde yemek odaklıdır
        "original_url": None,
        "url_hash": None,
        "status": "active",
        "click_count": 0,
        "avg_orj_score": None, # Altta hesaplanacak
        "avg_model_score": None,
        "guncel_ozet": None,
        "created_at": datetime.now(),
        "last_updated_at": datetime.now()
    }

    ham_yorumlar = raw_json.get("yorumlar", [])
    tum_yorum_puanlari = []

    for y in ham_yorumlar:
        score_dict = y.get("score") or {}
        # Hız, Lezzet, Servis puanlarının ortalamasını alıyoruz
        sub_puanlar = [v for k, v in score_dict.items() if isinstance(v, (int, float))]
        if sub_puanlar:
            tum_yorum_puanlari.append(sum(sub_puanlar) / len(sub_puanlar))

    if tum_yorum_puanlari:
        urun_paket["avg_orj_score"] = round(sum(tum_yorum_puanlari) / len(tum_yorum_puanlari), 2)

    review_packets = []
    for raw_review in ham_yorumlar:
        order_items = raw_review.get("orderItems") or []
        alinan_urunler = [item.get("name") for item in order_items if item.get("name")]

        metadata = {
            "siparis_edilen_urunler": alinan_urunler,
            "teslimat_tipi": raw_review.get("deliveryType"),
            "detayli_puanlar": raw_review.get("score") # Hız:5, Lezzet:4 gibi
        }

        # Bireysel yorum puanı olarak genel ortalamasını alalım
        score_dict = raw_review.get("score") or {}
        puanlar = [v for v in score_dict.values() if isinstance(v, (int, float))]
        individual_rating = sum(puanlar) / len(puanlar) if puanlar else None

        review_packets.append({
            "product_id": product_uuid,
            "original_rating": individual_rating,
            "predicted_score": None,
            "raw_text": raw_review.get("comment"),
            "clean_text": raw_review.get("temiz_metin"),
            "metadata": metadata,
            "created_at": datetime.now()
        })

    return urun_paket, review_packets


def process_yemeksepeti_data(raw_json: dict) -> tuple[dict, list[dict]]:
    product_uuid = str(uuid4())
    orijinal_url = raw_json.get("link", "")

    urun_paket = {
        "id": product_uuid,
        "platform": None,
        "platform_id": None,
        "product_name": raw_json.get("baslik"),
        "image_url": raw_json.get("gorsel_url"),
        "category": "Restoran",
        "original_url": None,
        "url_hash": None,
        "status": "active",
        "click_count": 0,
        "avg_orj_score": None,
        "avg_model_score": None,
        "guncel_ozet": None,
        "created_at": datetime.now(),
        "last_updated_at": datetime.now()
    }

    ham_yorumlar = raw_json.get("yorumlar", [])
    tum_yorum_puanlari = []

    for y in ham_yorumlar:
        ratings = y.get("ratings", [])
        overall = next((r.get("score") for r in ratings if r.get("topic") == "overall"), None)
        if isinstance(overall, (int, float)):
            tum_yorum_puanlari.append(overall)

    if tum_yorum_puanlari:
        urun_paket["avg_orj_score"] = round(sum(tum_yorum_puanlari) / len(tum_yorum_puanlari), 2)

    review_packets = []
    for raw_review in ham_yorumlar:
        ratings = raw_review.get("ratings", [])

        # Detaylı Puanlar
        overall_score = next((r.get("score") for r in ratings if r.get("topic") == "overall"), None)
        food_score = next((r.get("score") for r in ratings if r.get("topic") == "restaurant_food"), None)
        rider_score = next((r.get("score") for r in ratings if r.get("topic") == "rider"), None)

        # Sepet Analizi
        product_variations = raw_review.get("productVariations", [])
        alinan_urunler = [item.get("defaultTitle") for item in product_variations if item.get("defaultTitle")]
        sepet_tutari = sum(
            item.get("unitPrice", 0) for item in product_variations if isinstance(item.get("unitPrice"), (int, float)))

        metadata = {
            "lezzet_puani": food_score,
            "kurye_puani": rider_score,  # Lojistik analizi için
            "siparis_edilen_urunler": alinan_urunler,
            "tahmini_sepet_tutari": sepet_tutari,
            "faydali_bulan_sayisi": raw_review.get("likeCount", 0),
            "anonim_mi": raw_review.get("isAnonymous")
        }

        review_packets.append({
            "product_id": product_uuid,
            "original_rating": overall_score,
            "predicted_score": None,
            "raw_text": raw_review.get("text"),  # Scraper'da 'text' olarak geliyor
            "clean_text": raw_review.get("temiz_metin"),
            "metadata": metadata,
            "created_at": datetime.now()
        })

    return urun_paket, review_packets


def donustur_ve_kaydet(ham_json_yolu: str, platform: str, platform_id: str, temiz_url: str, url_hash: str) -> tuple[dict, list[dict]]:
    try:
        with open(ham_json_yolu, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except Exception as e:
        raise Exception(f"JSON okuma hatası ({ham_json_yolu}): {e}")

    if not platform:
        raise ValueError("Dönüştürücü Hatası: Platform bilgisi eksik.")
    hedef_klasor = os.path.join("Transformed_datas",platform)
    os.makedirs(hedef_klasor, exist_ok=True)

    if platform == "trendyol":
        urun_paket, yorumlar_paket = process_trendyol_data(raw_data)
    elif platform == "hepsiburada":
        urun_paket, yorumlar_paket = process_hepsiburada_data(raw_data)
    elif platform == "ciceksepeti":
        urun_paket, yorumlar_paket = process_ciceksepeti_data(raw_data)
    elif platform == "steam":
        urun_paket, yorumlar_paket = process_steam_data(raw_data)
    elif platform == "yemeksepeti":
        urun_paket, yorumlar_paket = process_yemeksepeti_data(raw_data)
    elif platform == "trendyol-go":
        urun_paket, yorumlar_paket = process_tygo_data(raw_data)
    elif platform == "etstur":
        urun_paket, yorumlar_paket = process_etstur_data(raw_data)
    elif platform == "airbnb":
        urun_paket, yorumlar_paket = process_airbnb_data(raw_data)
    elif platform == "maps":
        urun_paket, yorumlar_paket = process_maps_data(raw_data)
    else:
        raise ValueError(f"Dönüştürücü Hatası: Bilinmeyen platform '{platform}'")

    urun_paket["platform"] = platform
    urun_paket["platform_id"] = platform_id
    urun_paket["original_url"] = temiz_url
    urun_paket["url_hash"] = url_hash


    temiz_veri = {
        "urun_paketi":urun_paket,
        "yorum_paketi":yorumlar_paket
    }

    dosya_adi = os.path.basename(ham_json_yolu)
    yeni_dosya_yolu = os.path.join(hedef_klasor, f"clean_{dosya_adi}")

    with open(yeni_dosya_yolu, "w", encoding='utf-8') as f:
        json.dump(temiz_veri, f, ensure_ascii=False, indent=4, default=str)

    return urun_paket, yorumlar_paket







