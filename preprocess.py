import json
import os
import re
import emoji
from pathlib import Path

# ==========================================
# AKILLI METİN ÇIKARICI (DEDEKTİF)
# ==========================================
def yorum_metnini_bul(yorum):
    """Farklı API'lerden gelen karmaşık JSON formatlarındaki asıl yorum metnini otomatik bulur."""
    if isinstance(yorum, str):  #eğer olurda bir gün ben bu fonksiyonu kullanırsam string bir değer verdiğimde çalışsın diye yazdım
        return yorum

    olasi_anahtarlar = ["metin", "comment", "review", "text", "customerDescription", "comments", "reviewText", "content"]

    if isinstance(yorum, dict):
        # 1. Aşama: Bilinen anahtarları kontrol et
        for key in olasi_anahtarlar:
            if key in yorum and isinstance(yorum[key], str):
                return yorum[key]

        # 2. Aşama: Bulunamazsa, sözlükteki en uzun metni (string) yorum olarak kabul et
        string_degerler = [v for v in yorum.values() if isinstance(v, str) and len(v) > 5]
        if string_degerler:
            return max(string_degerler, key=len)   #key=len kullanımı

    return ""

# ==========================================
# VERİ TEMİZLEME SINIFI (PREPROCESSOR)
# ==========================================
class ReviewPreprocessor:
    def __init__(self, typo_file="duzeltmeler.json", bad_words_file="bad_words.json"):
        # Sözlükleri RAM'e yüklüyoruz
        self.typo_mapping = self._load_json(typo_file, dict)
        self.bad_words = set(self._load_json(bad_words_file, list))

    def _load_json(self, filename, default_type):
        path = Path(filename)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f" {filename} okunamadı: {e}")
        return default_type()    #bu şekilde  default_type dondurme sebebimiz yüklenemez ve beklediğimiz çıktıyı vermezse boş o nitelikte döndürsünki hata almayalım

    # --- ALT TEMİZLİK MODÜLLERİ ---
    def lowercase_turkish(self, text):
        lookup = {'I': 'ı', 'İ': 'i', 'Ş': 'ş', 'Ç': 'ç', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö'}
        text = "".join([lookup.get(char, char) for char in text])
        return text.lower()

    def remove_html_and_urls(self, text):
        text = text.replace('\n', ' ').replace('\r', '')
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        text = re.sub(r'<.*?>', '', text)
        return text

    def remove_keysmash(self, text):
        vowels_pattern = r'[aeıioöuü]{3,}'  # 3 veya daha fazla ardışık sesli harf var mı
        consonants_pattern = r'[bcçdfgğhjklmnprsştvyz]{4,}' # 4 veya daha fazla ardışık sessiz harf var mı
        words = text.split()
        clean_words = [w for w in words if not (re.search(vowels_pattern, w) or re.search(consonants_pattern, w))]
        return " ".join(clean_words)

    def normalize_repeating_chars(self, text):
        return re.sub(r'([a-zçğıöşü])\1{2,}', r'\1', text)

    def correct_typos(self, text):
        words = text.split()
        return " ".join([self.typo_mapping.get(word, word) for word in words])

    def remove_profanity(self, text):
        if not self.bad_words: return text
        for bad_word in self.bad_words:
            pattern = r'\b' + re.escape(bad_word) + r'\b'
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)#re.IGNORECASE:büyük küçük harf farkını yok say
        return text

    # --- ANA PIPELINE (Boru Hattı) ---
    def clean_text(self, text, platform="general"):     #bu yapı scability(genişletilebilirlik) sağlaması için
        if not isinstance(text, str) or not text.strip():     #eğer gelen veri str yapıda değilse direkt geç(None olabilir)
            return ""

        # 1. URL, HTML ve Emojileri Sil
        text = self.remove_html_and_urls(text)
        text = emoji.replace_emoji(text, replace='')

        # 2. Türkçe Küçültme ve Noktalama Silme
        text = self.lowercase_turkish(text)
        text = re.sub(r'[^\w\s]', ' ', text) # Sadece harf ve rakamlar kalsın

        # 3. Tipografi, Yazım Yanlışları ve Küfür Temizliği (Her yorum için)
        text = self.normalize_repeating_chars(text)
        text = self.correct_typos(text)
        text = self.remove_keysmash(text)
        text = self.remove_profanity(text)

        # Fazla boşlukları temizle ve döndür
        return re.sub(r'\s+', ' ', text).strip()

# ==========================================
# DOSYA İŞLEME VE KAYDETME (ORCHESTRATOR)
# ==========================================
def process_all_data():
    ANA_KLASOR = "cekilen_veriler"
    TEMIZ_KLASOR = "temiz_veriler"
    os.makedirs(TEMIZ_KLASOR, exist_ok=True)

    preprocessor = ReviewPreprocessor(
        typo_file="duzeltmeler.json",
        bad_words_file="bad_words.json"
    )

    if not os.path.exists(ANA_KLASOR):
        print(f" '{ANA_KLASOR}' klasörü bulunamadı! Önce scraper.py'yi çalıştırın.")
        return

    # Tüm platform klasörlerini gez
    for platform_adi in os.listdir(ANA_KLASOR):
        platform_yolu = os.path.join(ANA_KLASOR, platform_adi)

        if os.path.isdir(platform_yolu):
            hedef_platform_klasoru = os.path.join(TEMIZ_KLASOR, platform_adi)
            os.makedirs(hedef_platform_klasoru, exist_ok=True)

            # Klasör içindeki JSON dosyalarını gez
            for dosya_adi in os.listdir(platform_yolu):
                if dosya_adi.endswith('.json'):
                    kaynak_dosya = os.path.join(platform_yolu, dosya_adi)
                    hedef_dosya = os.path.join(hedef_platform_klasoru, f"temiz_{dosya_adi}")

                    try:
                        with open(kaynak_dosya, "r", encoding="utf-8") as f:
                            veriler = json.load(f)

                        temizlenen_veriler = []
                        for yorum in veriler:
                            # Akıllı dedektif fonksiyonumuz metni buluyor
                            ham_metin = yorum_metnini_bul(yorum)

                            # Preprocessor metni temizliyor
                            temiz_metin = preprocessor.clean_text(ham_metin, platform=platform_adi)

                            if len(temiz_metin) > 3: # En az 3 harfli mantıklı yorumlar kalsın
                                if isinstance(yorum, dict):
                                    yorum["temiz_metin"] = temiz_metin
                                    temizlenen_veriler.append(yorum)
                                else:
                                    temizlenen_veriler.append({"orijinal_metin": yorum, "temiz_metin": temiz_metin})

                        # Temizlenmiş verileri yeni klasöre kaydet
                        if temizlenen_veriler:
                            with open(hedef_dosya, "w", encoding="utf-8") as f:
                                json.dump(temizlenen_veriler, f, ensure_ascii=False, indent=4)
                            print(f" Temizlendi: {platform_adi} -> {dosya_adi} ({len(temizlenen_veriler)} nitelikli yorum)")

                    except Exception as e:
                        print(f" Hata ({dosya_adi}): {e}")

if __name__ == "__main__":
    print("🚀 Veri Ön İşleme (Pre-processing) Başlıyor...\n")
    process_all_data()
    print("\n🎉 Tüm veriler başarıyla temizlendi ve 'temiz_veriler' klasörüne aktarıldı!")