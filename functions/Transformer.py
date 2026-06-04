import os
import json
import re
from datetime import datetime
from uuid import uuid4
from typing import Tuple, List, Dict
from functions.utils import kategori_grupla, ciceksepeti_kategori_hibrit


class BaseTransformer:
    def __init__(self, raw_json: dict):
        self.raw_json = raw_json
        self.product_uuid = str(uuid4())
        self.ham_yorumlar = raw_json.get("yorumlar", [])
        self.platform_name = "unknown"

    def get_category(self):
        return None

    def get_avg_orj_score(self):
        return None

    def get_individual_rating(self, raw_review):
        return None

    def get_metadata(self, raw_review):
        return {}

    def get_raw_text(self, raw_review):
        return raw_review.get("comment") or raw_review.get("metin") or raw_review.get("text") or raw_review.get(
            "orijinal_metin") or ""

    def process(self) -> tuple[dict, list[dict]]:
        gecerli_puanlar =[]
        review_packets = []
        for raw_review in self.ham_yorumlar:
            current_rating = self.get_individual_rating(raw_review)
            if current_rating is not None:
                gecerli_puanlar.append(float(current_rating))

            review_packets.append({
                "product_id": self.product_uuid,
                "original_rating": current_rating,
                "rating_int": round(current_rating) if current_rating is not None else None,
                "predicted_score": None,
                "raw_text": self.get_raw_text(raw_review),
                "clean_text": raw_review.get("temiz_metin"),
                "metadata": self.get_metadata(raw_review),
                "created_at": datetime.now()
            })

        celiski_score=0.00
        if len(gecerli_puanlar) >= 2:
            ort = sum(gecerli_puanlar) / len(gecerli_puanlar)
            varyans = sum((x - ort) ** 2) for x in gecerli_puanlar / len(gecerli_puanlar)
            celiski_score=round(varyans / 4.0, 2)   #burada 0-1 arasına normalize etmek için 4 'e böldük.(max variance)

        urun_paket = {
            "id": self.product_uuid,
            "platform": self.platform_name,
            "platform_id": None,
            "product_name": self.raw_json.get("baslik"),
            "image_url": self.raw_json.get("gorsel_url"),
            "category": self.get_category(),
            "original_url": None,
            "url_hash": None,
            "status": "active",
            "click_count": 0,
            "avg_orj_score": self.get_avg_orj_score(),
            "avg_model_score": None,
            "celiski_score": celiski_score,
            "guncel_ozet": None,
            "created_at": datetime.now(),
            "last_updated_at": datetime.now()
        }
        return urun_paket, review_packets


class TrendyolTransformer(BaseTransformer):
    def __init__(self, raw_json: dict):
        super().__init__(raw_json)
        self.platform_name = "trendyol"

    def get_category(self):
        kategori_agaci = self.raw_json.get("kategori") or []
        return kategori_grupla(kategori_agaci).lower()

    def get_avg_orj_score(self):
        ratings = [y.get("rate") for y in self.ham_yorumlar if isinstance(y.get("rate"), (int, float))]
        if ratings:
            return round(sum(ratings) / len(ratings), 2)
        return None

    def get_individual_rating(self, raw_review):
        return raw_review.get("rate")

    def get_metadata(self, raw_review):
        return {
            "media_files": raw_review.get("mediaFiles"),
            "seller_info": raw_review.get("seller"),
            "rate": raw_review.get("rate"),
            "is_trusted": raw_review.get("trusted"),
            "likesCount": raw_review.get("likesCount"),
        }

    def get_raw_text(self, raw_review):
        return raw_review.get("metin") or raw_review.get("comment") or ""


class HepsiburadaTransformer(BaseTransformer):
    def __init__(self, raw_json: dict):
        super().__init__(raw_json)
        self.platform_name = "hepsiburada"

    def get_category(self):
        kategori_agaci = self.raw_json.get("kategori") or []
        return kategori_grupla(kategori_agaci).lower()

    def get_avg_orj_score(self):
        ratings = [y.get("star") for y in self.ham_yorumlar if isinstance(y.get("star"), (int, float))]
        if ratings:
            return round(sum(ratings) / len(ratings), 2)
        return None

    def get_individual_rating(self, raw_review):
        return raw_review.get("star")

    def get_metadata(self, raw_review):
        order_info = raw_review.get("order") or {}
        reaction_info = raw_review.get("reactions") or {}
        return {
            "satici_adi": order_info.get("merchantName"),
            "dogrulanmis_satin_alim": raw_review.get("isPurchaseVerified"),
            "beden_kalibi": raw_review.get("mould"),
            "faydali_bulma_sayisi": reaction_info.get("clap", 0),
        }

    def get_raw_text(self, raw_review):
        return raw_review.get("review", {}).get("content", "")


class CiceksepetiTransformer(BaseTransformer):
    def __init__(self, raw_json: dict):
        super().__init__(raw_json)
        self.platform_name = "ciceksepeti"

    def get_category(self):
        return ciceksepeti_kategori_hibrit(self.raw_json.get("baslik"))

    def get_avg_orj_score(self):
        ratings = []
        for y in self.ham_yorumlar:
            puan_str = y.get("puan") or y.get("rating")
            if puan_str and puan_str[0].isdigit():
                ratings.append(int(puan_str[0]))
        if ratings:
            return round(sum(ratings) / len(ratings), 2)
        return None

    def get_individual_rating(self, raw_review):
        puan_str = raw_review.get("puan") or raw_review.get("rating")
        if puan_str and puan_str[0].isdigit():
            return int(puan_str[0])
        return None

    def get_metadata(self, raw_review):
        return {
            "kullanici_adi": raw_review.get("isim"),
            "yorum_tarihi": raw_review.get("tarih"),
            "verilen_puan_str": raw_review.get("puan")
        }

    def get_raw_text(self, raw_review):
        return raw_review.get("orijinal_metin") or ""


class EtsturTransformer(BaseTransformer):
    def __init__(self, raw_json: dict):
        super().__init__(raw_json)
        self.platform_name = "etstur"

    def get_category(self):
        return "otel"

    def get_avg_orj_score(self):
        ratings = [float(y.get("score")) / 20 for y in self.ham_yorumlar if isinstance(y.get("score"), (int, float))]
        if ratings:
            return round(sum(ratings) / len(ratings), 2)
        return None

    def get_individual_rating(self, raw_review):
        score = raw_review.get("score")
        if isinstance(score, (int, float)):
            return float(score) / 20
        return None

    def get_metadata(self, raw_review):
        alt_puanlar_listesi = raw_review.get("ratingTypes") or []
        alt_kategori_puanlari = {
            item.get("name"): (float(item.get("score")) / 2 if isinstance(item.get("score"), (int, float)) else None)
            for item in alt_puanlar_listesi
        }
        return {
            "verilen_puan_100": raw_review.get("score"),
            "tavsiye_ediyor_mu": raw_review.get("recommendation"),
            "misafir_tipi": raw_review.get("guestType"),
            "oda_tipi": raw_review.get("roomName"),
            "detaylı_puanlar": alt_kategori_puanlari
        }

    def get_raw_text(self, raw_review):
        return raw_review.get("temiz_metin") or ""


class MapsTransformer(BaseTransformer):
    def __init__(self, raw_json: dict):
        super().__init__(raw_json)
        self.platform_name = "maps"

    def get_category(self):
        return self.raw_json.get("kategori")

    def get_avg_orj_score(self):
        ratings = []
        for y in self.ham_yorumlar:
            puan_str = y.get("puan", "")
            if puan_str and puan_str[0].isdigit():
                ratings.append(int(puan_str[0]))
        if ratings:
            return round(sum(ratings) / len(ratings), 2)
        return None

    def get_individual_rating(self, raw_review):
        puan_raw = str(raw_review.get("puan") or "0")
        match = re.search(r"[\d,.]+", puan_raw)
        if match:
            return float(match.group().replace(',', '.'))
        return None

    def get_metadata(self, raw_review):
        return {
            "isim": raw_review.get("isim"),
            "tarih_metni": raw_review.get("tarih"),
            "ham_puan_metni": raw_review.get("puan")
        }

    def get_raw_text(self, raw_review):
        return raw_review.get("orijinal_metin") or ""


class SteamTransformer(BaseTransformer):
    def __init__(self, raw_json: dict):
        super().__init__(raw_json)
        self.platform_name = "steam"

    def get_category(self):
        return "oyun"

    def get_avg_orj_score(self):
        if not self.ham_yorumlar:
            return None
        olumlu_sayisi = sum(1 for y in self.ham_yorumlar if y.get("voted_up") is True)
        oran = olumlu_sayisi / len(self.ham_yorumlar)
        return round((oran * 5) * 2) / 2

    def get_individual_rating(self, raw_review):
        return 5 if raw_review.get("voted_up") else 1

    def get_metadata(self, raw_review):
        author_info = raw_review.get("author") or {}
        return {
            "voted_up": raw_review.get("voted_up"),
            "oynanma_suresi_dakika": author_info.get("playtime_forever"),
            "faydali_bulma_sayisi": raw_review.get("votes_up", 0)
        }

    def get_raw_text(self, raw_review):
        return raw_review.get("review") or ""


class TygoTransformer(BaseTransformer):
    def __init__(self, raw_json: dict):
        super().__init__(raw_json)
        self.platform_name = "trendyol-go"

    def get_category(self):
        return "yemek"

    def get_avg_orj_score(self):
        tum_yorum_puanlari = []
        for y in self.ham_yorumlar:
            score_dict = y.get("score") or {}
            sub_puanlar = [v for k, v in score_dict.items() if isinstance(v, (int, float))]
            if sub_puanlar:
                tum_yorum_puanlari.append(sum(sub_puanlar) / len(sub_puanlar))
        if tum_yorum_puanlari:
            return round(sum(tum_yorum_puanlari) / len(tum_yorum_puanlari), 2)
        return None

    def get_individual_rating(self, raw_review):
        score_dict = raw_review.get("score") or {}
        puanlar = [v for v in score_dict.values() if isinstance(v, (int, float))]
        if puanlar:
            return sum(puanlar) / len(puanlar)
        return None

    def get_metadata(self, raw_review):
        order_items = raw_review.get("orderItems") or []
        alinan_urunler = [item.get("name") for item in order_items if item.get("name")]
        sepet_tutari = sum(
            item.get("unitPrice", 0) for item in order_items if isinstance(item.get("unitPrice"), (int, float)))
        return {
            "siparis_edilen_urunler": alinan_urunler,
            "teslimat_tipi": raw_review.get("deliveryType"),
            "detayli_puanlar": raw_review.get("score"),
            "tahmini_sepet_tutari": sepet_tutari
        }

    def get_raw_text(self, raw_review):
        return raw_review.get("comment") or ""


class YemeksepetiTransformer(BaseTransformer):
    def __init__(self, raw_json: dict):
        super().__init__(raw_json)
        self.platform_name = "yemeksepeti"

    def get_category(self):
        return "yemek"

    def get_avg_orj_score(self):
        tum_yorum_puanlari = []
        for y in self.ham_yorumlar:
            ratings = y.get("ratings", [])
            overall = next((r.get("score") for r in ratings if r.get("topic") == "overall"), None)
            if isinstance(overall, (int, float)):
                tum_yorum_puanlari.append(overall)
        if tum_yorum_puanlari:
            return round(sum(tum_yorum_puanlari) / len(tum_yorum_puanlari), 2)
        return None

    def get_individual_rating(self, raw_review):
        ratings = raw_review.get("ratings", [])
        overall_score = next((r.get("score") for r in ratings if r.get("topic") == "overall"), None)
        return overall_score

    def get_metadata(self, raw_review):
        ratings = raw_review.get("ratings", [])
        food_score = next((r.get("score") for r in ratings if r.get("topic") == "restaurant_food"), None)
        rider_score = next((r.get("score") for r in ratings if r.get("topic") == "rider"), None)
        product_variations = raw_review.get("productVariations", [])
        alinan_urunler = [item.get("defaultTitle") for item in product_variations if item.get("defaultTitle")]
        sepet_tutari = sum(
            item.get("unitPrice", 0) for item in product_variations if isinstance(item.get("unitPrice"), (int, float)))
        return {
            "lezzet_puani": food_score,
            "kurye_puani": rider_score,
            "siparis_edilen_urunler": alinan_urunler,
            "tahmini_sepet_tutari": sepet_tutari,
            "faydali_bulan_sayisi": raw_review.get("likeCount", 0),
            "anonim_mi": raw_review.get("isAnonymous")
        }

    def get_raw_text(self, raw_review):
        return raw_review.get("text") or ""


class AirbnbTransformer(BaseTransformer):
    def __init__(self, raw_json: dict):
        super().__init__(raw_json)
        self.platform_name = "airbnb"

    def get_category(self):
        return "gunluk_ev"

    def get_avg_orj_score(self):
        ratings = [float(y.get("score")) / 20 for y in self.ham_yorumlar if isinstance(y.get("score"), (int, float))]
        if ratings:
            return round(sum(ratings) / len(ratings), 2)
        return None

    def get_individual_rating(self, raw_review):
        score = raw_review.get("score")
        if isinstance(score, (int, float)):
            return float(score) / 20
        return None

    def get_metadata(self, raw_review):
        return {
            "rate": raw_review.get("rating"),
            "misafirin_ulkesi": raw_review.get("localizedReviewerLocation"),
            "konaklama_tipi": raw_review.get("reviewHighlight"),
        }

    def get_raw_text(self, raw_review):
        return raw_review.get("comment") or ""


TRANSFORMER_REGISTRY = {
    "trendyol": TrendyolTransformer,
    "hepsiburada": HepsiburadaTransformer,
    "ciceksepeti": CiceksepetiTransformer,
    "etstur": EtsturTransformer,
    "maps": MapsTransformer,
    "steam": SteamTransformer,
    "trendyol-go": TygoTransformer,
    "yemeksepeti": YemeksepetiTransformer,
    "airbnb": AirbnbTransformer
}


def donustur_ve_kaydet(ham_json_yolu: str, platform: str, platform_id: str, temiz_url: str, url_hash: str) -> tuple[
    dict, list[dict]]:
    try:
        with open(ham_json_yolu, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except Exception as e:
        raise Exception(f"JSON okuma hatası ({ham_json_yolu}): {e}")

    if not platform or platform not in TRANSFORMER_REGISTRY:
        raise ValueError(f"Dönüştürücü Hatası: Bilinmeyen platform '{platform}'")

    hedef_klasor = os.path.join("../Transformed_datas", platform)
    os.makedirs(hedef_klasor, exist_ok=True)

    transformer_class = TRANSFORMER_REGISTRY[platform]
    transformer_instance = transformer_class(raw_data)

    urun_paket, yorumlar_paket = transformer_instance.process()

    urun_paket["platform_id"] = platform_id
    urun_paket["original_url"] = temiz_url
    urun_paket["url_hash"] = url_hash

    temiz_veri = {
        "urun_paketi": urun_paket,
        "yorum_paketi": yorumlar_paket
    }

    dosya_adi = os.path.basename(ham_json_yolu)
    yeni_dosya_yolu = os.path.join(hedef_klasor, f"clean_{dosya_adi}")

    with open(yeni_dosya_yolu, "w", encoding='utf-8') as f:
        json.dump(temiz_veri, f, ensure_ascii=False, indent=4, default=str)

    return urun_paket, yorumlar_paket
