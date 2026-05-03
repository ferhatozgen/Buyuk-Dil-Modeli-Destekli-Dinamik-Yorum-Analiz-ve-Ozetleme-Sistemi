from urllib.parse import urlparse, urlunparse
import urllib.parse
import hashlib
import re

def url_cleaning(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    cleaned_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', '')) # Sadece temel URL'yi alır, query ve fragment'ı atar
    return cleaned_url

# stringi utf-8 formatında byte dizisine çeviriyor çünkü hex fonksiyonları string değil byte dizileriyle çalışır.
def url_hashing(clean_url: str) -> str:
    return hashlib.sha256(clean_url.encode('utf-8')).hexdigest()

def url_cozumle(url : str) -> tuple[str, str]  :
    url_lower = url.lower()
    platform = None

    if "tgo" in url_lower or "trendyol-yemek" in url_lower or "/go/" in url_lower:
        platform = "trendyol-go"
    elif "trendyol.com" in url_lower:
        platform = "trendyol"
    elif "hepsiburada.com" in url_lower:
        platform = "hepsiburada"
    elif "ciceksepeti.com" in url_lower:
        platform = "ciceksepeti"
    elif "steampowered.com" in url_lower:
        platform = "steam"
    elif "airbnb.com" in url_lower:
        platform = "airbnb"
    elif "yemeksepeti.com" in url_lower:
        platform = "yemeksepeti"
    elif "etstur.com" in url_lower:
        platform = "etstur"
    elif "googleusercontent.com/maps" in url_lower or "/maps/" in url_lower:
        platform = "maps"
    else:
        raise ValueError("Platform bulunamadı")

    if platform == "maps":
        # regex yöntemiyle id yakalama işlemi (ilk deneme)
        match = re.search(r'/place/([^/?]+)', url)
        if match:
            return platform, urllib.parse.unquote(match.group(1))

        # string parçalama yöntemiyle urlnin sonundan id yakalama işlemi (ikinci deneme)
        path_segment = url.strip('/').split('/')  #strip / işaretlerinden temizler,  splitte / işaretlerinden ayırır liste yapar urlyi
        if path_segment:
            last_segment = path_segment[-1]
            clean_id = last_segment.split('?')[0]     #linkin sonunda bazen idden sonra ?authuser=0 gibi uzun parametreler olur bu yazımdan urlyi temizlemek için
            return platform, (clean_id if clean_id else "unknown")

    patterns = {
        "trendyol": r"-p-(\d+)",
        "hepsiburada": r"-p[m]?-([A-Za-z0-9]+)",
        "ciceksepeti": r"-([a-zA-Z0-9]+)(?:\?|/|$)",
        "steam": r"/app/(\d+)",
        "airbnb": r"/rooms/(\d+)",
        "yemeksepeti": r"/restaurant/([a-zA-Z0-9]+)",
        "trendyol-go": r"(?:-|/)(\d+)(?:/|\?|$)",
        "etstur": r"etstur\.com/([^/?]+)"  # Etstur'da genelde otel adı ID yerine geçer
    }

    if platform in patterns:
        match = re.search(patterns[platform], url)
        if match:
            return platform, match.group(1)

    return platform, "Unknown"