from functions.scraper import yemeksepeti_veri_cek
print("Test basliyor...")
sonuc = yemeksepeti_veri_cek("https://www.yemeksepeti.com/restaurant/rvjp/kuzey-kokorec", 1)
print("Test bitti, sonuc:", sonuc)