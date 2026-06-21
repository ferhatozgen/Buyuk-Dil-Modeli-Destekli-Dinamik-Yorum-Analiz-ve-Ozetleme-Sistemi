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
import requests
from fastapi.middleware.cors import CORSMiddleware

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme aşamasında tüm kökenlere izin veriyoruz
    allow_credentials=True,
    allow_methods=["*"],  # POST, GET, OPTIONS vb. tüm isteklere izin ver
    allow_headers=["*"],
)


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


#Aşama 5: Chatbot
class ChatRequest(BaseModel):
    productId: str
    user_message: str

#chati hafızada tutan sözlük
chat_histories = {}


#left join aynı kategorideki diğer ürünlerle kıyaslanabilmesi için eklendi.
#ve aynı zamanda eğer ürünün kategori tablosu boş olsa bile ürün bilgilerini alıyor ve hata vermiyor.(Inner Join verirdi)
def get_product_rag_context(product_id: str, db_manager: DatabaseManager) -> str:
    query = """
            SELECT 
                p.product_name, 
                p.platform, 
                p.avg_orj_score, 
                p.avg_model_score, 
                p.celiski_score, 
                p.guncel_ozet,
                c.category_name,
                c.category_model_avg_score,
                c.category_summary
            FROM products p
            LEFT JOIN product_category_stats c ON p.id = c.product_id
            WHERE p.id = %s;
        """
    product_data = db_manager.fetch_query(query, (product_id,))
    if not product_data:
        return "Ürün analitik verileril db de bulunamadı."

    p_name, platform, avg_orj, avg_model, celiski, guncel_ozet, cat_name, cat_avg_score = product_data[0]
    temiz_celiski = int(float(celiski) * 100) if celiski is not None else 0

    # Modele kanıt niteliğinde sunulacak en güncel 5 adet gerçek ham kullanıcı yorumu
    yorum_query = """
            SELECT original_rating, raw_text 
            FROM reviews 
            WHERE product_id = %s AND raw_text IS NOT NULL AND raw_text != '' 
            LIMIT 5;
        """

    yorumlar= db_manager.fetch_query(yorum_query, (product_id,))
    yorum_metinleri = "".join([f"- [{r[0]} Yıldız]: {r[1].strip()}\n" for r in yorumlar])

    # Modelin okuyacağı nihai bilgi havuzu şablonu
    context = f"""
        [ÜRÜN KILAVUZU]
        Ürün Adı: {p_name} | Platform: {platform}
        Müşteri Puan Ortalaması: {avg_orj}/5 | Eğitilen Modelin Memnuniyet Skoru: {avg_model}/5
        Müşteri Fikir Ayrılığı (Çelişki) Oranı: %{temiz_celiski}
        Detaylı Yapay Zeka Özeti: {guncel_ozet}

        [SEKTÖR / RAKİP ANALİZİ]
        Kategori: {cat_name} | Rakip Ortalama Puanı: {cat_avg_score}/5
        Kategori Sektör Durumu: {cat_summary}

        [SİSTEMDEKİ GERÇEK KULLANICI YORUMLARI]
        {yorum_metinleri}
        """
    return context


@app.post("/api/v1/chat")
async def chat_with_vivid_bot(request: ChatRequest):
    db = None
    try:
        db = DatabaseManager()

        # 1. Adım: Veritabanından zengin bağlamı getir (Retrieval)
        context_bilgisi = get_product_rag_context(request.productId, db)

        # 2. Adım: Hafıza (Session) Yönetimi
        if request.productId not in chat_histories:
            chat_histories[request.productId] = []

        chat_histories[request.productId].append({"role": "user", "content": request.user_message})
        aktif_gecmis = chat_histories[request.productId][-6:]  # Son 3 karşılıklı diyalog

        # 3. Adım: Kurallı ve Doğal Türkçe Sağlayan Sistem Promptu
        system_prompt = f"""
        Sen VividAI platformunun kurallı, akıcı ve profesyonel Türkçe konuşan akıllı yapay zeka asistanısın.
        Görevin, sana sağlanan [ÜRÜN KILAVUZU], [SEKTÖR / RAKİP ANALİZİ] ve [SİSTEMDEKİ GERÇEK KULLANICI YORUMLARI] alanlarındaki verilere %100 bağlı kalarak kullanıcının sorularını yanıtlamaktır.

        KATI YOL HARİTASI KURALLARI:
        1. Cümlelerin her zaman kurallı ve imla kurallarına uygun olmalıdır. Asla devrik cümle kurma, kelimeleri yarım bırakma.
        2. Sana verilen kaynakların dışına çıkıp kafandan veri uydurma (Halüsinasyon görme). Bilgilerin yetersiz olduğu teknik detaylarda uydurmak yerine kibarca bu konuda veritabanında analiz bulunmadığını belirt.
        3. Çelişki oranı sorulduğunda; bunun kelime zıtlığı olmadığını, müşterilerin yıldız puanlarındaki kutuplaşma (bazı kullanıcıların 5, bazılarının 1 yıldız vermesiyle oluşan fikir ayrılığı) varyansı olduğunu profesyonelce açıkla.

        [BİLGİ KAYNAKLARI]:
        {context_bilgisi}
        """

        # ChatML Prompt Zincirinin Kurulması
        tam_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        for mesaj in aktif_gecmis:
            tam_prompt += f"<|im_start|>{mesaj['role']}\n{mesaj['content']}<|im_end|>\n"
        tam_prompt += "<|im_start|>assistant\n"

        # 4. Adım: MacBook Pro donanımında koşan Qwen 14B modeline istek atma
        ollama_url = "http://localhost:11434/api/generate"
        istek_ayarlari = {
            "model": "qwen2.5:14b",
            "prompt": tam_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "stop": ["<|im_end|>", "<|im_start|>"]
            }
        }

        response = requests.post(ollama_url, json=istek_ayarlari, timeout=90)
        bot_cevap = response.json().get("response", "").strip()

        # Cevabı sonraki mesajlarda hatırlamak üzere hafızaya kaydet
        chat_histories[request.productId].append({"role": "assistant", "content": bot_cevap})

        return {"status": "success", "response": bot_cevap}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sistemsel Hata: {str(e)}")
    finally:
        if db:
            db.close_pool()



# Uygulamayı Ayağa Kaldırma
if __name__ == "__main__":
    uvicorn.run("api_runner:app", host="0.0.0.0", port=8000, reload=True)