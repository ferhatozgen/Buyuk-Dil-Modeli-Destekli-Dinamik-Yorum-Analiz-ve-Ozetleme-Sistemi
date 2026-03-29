from scraper import linkten_veri_cek
from Transformer import donustur_ve_kaydet
import time

link_listesi = [
"https://www.hepsiburada.com/ergoflex-nb-f80-ekran-tutucu-kol-amortisorlu-monitor-standi-p-HBCV000007IXC9?magaza=Bizbiz-e"


]

def baslat():
    print(f"🚀 Toplam {len(link_listesi)} link sıraya alındı. ETL Operasyonu başlıyor...\n")

    for i, link in enumerate(link_listesi, 1):
        print(f"[{i}/{len(link_listesi)}] İŞLENİYOR: {link}")
        try:
            kazima_mesaji, ham_dosya_yolu = linkten_veri_cek(link)
            print(f"   [Scraper] {kazima_mesaji}")

            # 2. AŞAMA: DÖNÜŞTÜRME (Transform)
            if ham_dosya_yolu:
                transform_mesaji = donustur_ve_kaydet(ham_dosya_yolu)
                print(f"   [Transformer] {transform_mesaji}")
            else:
                print("   [Transformer] ⚠️ Dosya yolu gelmediği için dönüştürme işlemi atlandı.")

        except Exception as e:
            print(f"   ❌ Ana operasyon sırasında beklenmeyen hata: {e}")

        print("-" * 60)

        if i < len(link_listesi):
            print("⏳ Diğer linke geçmeden önce 3 saniye bekleniyor...\n")
            time.sleep(3)

    print("✅ BÜTÜN GÖREVLER KUSURSUZ ŞEKİLDE TAMAMLANDI!")

if __name__ == "__main__":
    baslat()