from functions.scraper import yemeksepeti_veri_cek
print("Test basliyor...")
# Test için örnek bir link ver
sonuc = yemeksepeti_veri_cek("https://www.yemeksepeti.com/restaurant/ornek-id/ornek-isim", 1)
print("Test bitti, sonuc:", sonuc)