import json
import os
from collections import Counter


def kategori_dagilimini_raporla(dosya_yolu):
    """.jsonl uzantılı eğitim dosyasındaki kategori dağılımlarını hesaplar ve listeler."""
    if not os.path.exists(dosya_yolu):
        print(f"❌ Belirtilen dosya bulunamadı: {dosya_yolu}")
        return

    kategori_sayaclari = Counter()
    toplam_parca_sayisi = 0
    toplam_yorum_sayisi = 0

    print(f"🔄 '{dosya_yolu}' dosyası analiz ediliyor...")

    with open(dosya_yolu, "r", encoding="utf-8") as f:
        for satir_no, satir in enumerate(f, 1):
            if not satir.strip():
                continue
            try:
                data = json.loads(satir)
                messages = data.get("messages", [])
                toplam_yorum_sayisi += 1

                # 1. 'assistant' rolüne ait içeriği buluyoruz
                assistant_content = None
                for msg in messages:
                    if msg.get("role") == "assistant":
                        assistant_content = msg.get("content")
                        break

                if assistant_content:
                    # 2. KRİTİK ADIM: Assistant içeriği string formatında bir JSON listesidir.
                    # Bunu tekrar parse ederek Python listesine çeviriyoruz.
                    analiz_listesi = json.loads(assistant_content)

                    # 3. Parçalanmış her bir alt cümlenin kategorisini sayaca ekliyoruz
                    for analiz in analiz_listesi:
                        kategori = analiz.get("kategori", "Tanımlanmamış")
                        kategori_sayaclari[kategori] += 1
                        toplam_parca_sayisi += 1

            except Exception as e:
                print(f"⚠️ Satır {satir_no} işlenirken hata oluştu: {e}")

    if toplam_parca_sayisi == 0:
        print("❌ Dosya içinde analiz edilecek uygun veri bulunamadı.")
        return

    # Ekrana raporu basma kısmı
    print("\n" + "=" * 65)
    print(f"📊 --- VERİ SETİ SINIF DAĞILIM RAPORU ---")
    print("=" * 65)
    print(f"📁 Dosya Yolu: {dosya_yolu}")
    print(f"💬 Toplam Ana Yorum Sayısı: {toplam_yorum_sayisi}")
    print(f"🧱 Toplam Parçalanmış Etiket (Chunk): {toplam_parca_sayisi}")
    print("-" * 65)
    print(f"{'KATEGORİ ADI':<40} | {'ADET':<7} | {'YÜZDELİK DAĞILIM'}")
    print("-" * 65)

    # En yüksek frekanstan en düşüğe doğru sıralıyoruz
    for kategori, adet in kategori_sayaclari.most_common():
        yuzde = (adet / toplam_parca_sayisi) * 100
        print(f"{kategori:<40} | {adet:<7} | %{yuzde:.2f}")

    print("=" * 65)


# --- ÇALIŞTIRMA KISMI ---
if __name__ == "__main__":
    # Hangi kategoriyi analiz etmek istiyorsan dosya adını buraya yazabilirsin
    hedef_dosya = os.path.join("Datasets", "elektronik_teknoloji_train.jsonl")

    kategori_dagilimini_raporla(hedef_dosya)