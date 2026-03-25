from scraper import linkten_veri_cek
import time

# İstediğin platformdan, istediğin kadar linki buraya alt alta ekle
link_listesi = [



]

def baslat():
    print(f"🚀 Toplam {len(link_listesi)} link sıraya alındı. Operasyon başlıyor...\n")

    for i, link in enumerate(link_listesi, 1):
        print(f"[{i}/{len(link_listesi)}] İşleniyor: {link}")

        # scraper.py'deki motorumuzu çalıştırıyoruz
        sonuc = linkten_veri_cek(link)
        print(f"Durum: {sonuc}\n")


        if i < len(link_listesi):
            print("⏳ Diğer linke geçmeden önce 3 saniye bekleniyor...\n")
            time.sleep(3)

    print("✅ TÜM GÖREVLER TAMAMLANDI!")

if __name__ == "__main__":
    baslat()