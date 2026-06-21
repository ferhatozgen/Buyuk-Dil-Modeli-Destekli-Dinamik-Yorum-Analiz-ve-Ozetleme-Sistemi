from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import pipeline, AutoTokenizer
from functions.scraper import linkten_veri_cek
from functions.Transformer import donustur_ve_kaydet
from functions.db_manager import DatabaseManager
from functions.utils import url_cleaning, url_hashing, url_cozumle, yorumlara_puan_ver

class ExtractRequest(BaseModel):
    url: str

class ProductIdRequest(BaseModel):
    productId: str

ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[INFO] ONNX BerTurk modeli yükleniyor...")
    MODEL_ID = "Halitbkts/berturk-review-score-predicter-model-onnx"
    try:
        model = ORTModelForSequenceClassification.from_pretrained(MODEL_ID)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        ml_models["classifier"] = pipeline("text-classification", model=model, tokenizer=tokenizer)
        print("INFO - [STARTUP] Model başarıyla yüklendi ve FastAPI sunucusu hazır!")
    except Exception as e:
        print(f"[ERROR] Model yüklenirken bir hata oluştu: {e}")

    yield

    print("[INFO] FastAPI sunucusu kapanıyor. Temizlik işlemleri yapılıyor...")
    ml_models.clear()

    try:
        DatabaseManager.close_pool()
    except Exception as e:
        print(f"[ERROR] Havuz kapatılırken bir sorun oluştu: {e}")


app = FastAPI(title="LLM Destekli Yorum Analiz API", lifespan=lifespan)


@app.post("/api/v1/extract")
def extract_and_save(request: ExtractRequest):
    try:
        db = DatabaseManager()
        temiz_url = url_cleaning(request.url)
        url_hash = url_hashing(temiz_url)
        platform, platform_id = url_cozumle(temiz_url)

        if not platform:
            raise HTTPException(status_code=400, detail="Platform tanımlanamadı.")

        mevcut_urun_id = db.fetch_query("SELECT id FROM products WHERE url_hash = %s", (url_hash,))
        if mevcut_urun_id:
            return {
                "status": "success",
                "message": "Ürün zaten veritabanında mevcut.",
                "productId": str(mevcut_urun_id[0][0])
            }

        kazima_mesaji, ham_dosya_yolu = linkten_veri_cek(temiz_url, platform)
        if not ham_dosya_yolu or not os.path.exists(ham_dosya_yolu):
            raise HTTPException(status_code=500, detail=f"Veri çekilemedi: {kazima_mesaji}")

        urun_paketi, yorum_paketleri = donustur_ve_kaydet(
            ham_dosya_yolu,
            platform=platform,
            platform_id=platform_id,
            temiz_url=temiz_url,
            url_hash=url_hash
        )

        urun_paketi['avg_model_score'] = None
        if yorum_paketleri:
            for yrm in yorum_paketleri:
                yrm['predicted_score'] = None

        product_id = db.save_product_and_reviews(urun_paketi, yorum_paketleri)

        return {
            "status": "success",
            "message": "Veriler başarıyla işlendi ve kaydedildi.",
            "productId": str(product_id)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kazıma hatası: {str(e)}")


# Aşama 2: Puanlama (Score)
@app.post("/api/v1/score")
async def score_reviews(request: ProductIdRequest):
    try:
        db = DatabaseManager()
        yorum_paketleri = db.get_unscored_data_by_produc_id(request.productId)

        if not yorum_paketleri:
            raise HTTPException(status_code=404, detail="Bu ürüne ait puanlanacak yorum bulunamadı.")

        classifier = ml_models.get("classifier")
        if not classifier:
            raise HTTPException(status_code=503, detail="BERTurk modeli RAM'de bulunamadı.")

        yorum_paketleri = yorumlara_puan_ver(classifier, yorum_paketleri)

        gecerli_puanlar = [y['predicted_score'] for y in yorum_paketleri if y.get('predicted_score') is not None]
        avg_model_score = None
        if gecerli_puanlar:
            avg_model_score = round(sum(gecerli_puanlar) / len(gecerli_puanlar), 2)

        db.update_scores(request.productId, avg_model_score, yorum_paketleri)

        return {
            "status": "success",
            "message": f"Yorumlar puanlandı. Ortalama: {avg_model_score}",
            "productId": request.productId
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Puanlama hatası: {str(e)}")


# Aşama 3: Kategorizasyon (Categorize)
@app.post("/api/v1/categorize")
async def categorize_aspects(request: ProductIdRequest):
    return {
        "status": "success",
        "message": "Yorumlar başarıyla niteliklerine (aspects) ayrıldı.",
        "productId": request.productId
    }


# Aşama 4: Özetleme (Summarize)
@app.post("/api/v1/summarize")
async def summarize_reviews(request: ProductIdRequest):
    return {
        "status": "success",
        "message": "Yapay zeka özeti başarıyla oluşturuldu.",
        "productId": request.productId,
        "summary": "Bu alan Llama/mT5 modelinden gelecek olan özet metnidir."
    }


# Uygulamayı Ayağa Kaldırma
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api_runner:app", host="0.0.0.0", port=port)
