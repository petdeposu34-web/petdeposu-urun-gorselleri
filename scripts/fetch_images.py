import io, os, re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from PIL import Image

S=requests.Session()
S.headers.update({
    "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
    "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.7"
})
os.makedirs("images",exist_ok=True)

# Exact Dilmaçlar image paths for poster size variants.
DIRECT = {
"8690000130177":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/80078008-30.jpg&Watermark=true",
"8690000130184":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/80078008-40.jpg&Watermark=true",
"8690000130191":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/80078008-50.jpg&Watermark=true",
"8690000130207":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/80078008-60.jpg&Watermark=true",
"8690000130375":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/80759024-30.jpg&Watermark=true",
"8690000130382":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/80759024-40.jpg&Watermark=true",
"8690000130399":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/80759024-50.jpg&Watermark=true",
"8690000130405":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/80759024-60.jpg&Watermark=true",
"8690000130290":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/90999091-30.jpg&Watermark=true",
"8690000130306":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/90999091-40.jpg&Watermark=true",
"8690000130313":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/90999091-50.jpg&Watermark=true",
"8690000130320":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/90999091-60.jpg&Watermark=true",
"8690000130498":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/fg107-30.jpg&Watermark=true",
"8690000130511":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/fg107-50.jpg&Watermark=true",
"8690000130528":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/fg107-60.jpg&Watermark=true",
"8690000130450":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/fg108-30.jpg&Watermark=true",
"8690000130467":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/fg108-40.jpg&Watermark=true",
"8690000130474":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/fg108-50.jpg&Watermark=true",
"8690000130481":"https://dilmaclar.com.tr/thumb.ashx?width=500&height=500&Resim=/Resim/fg108-60.jpg&Watermark=true",
}

def save_jpg(barcode, content):
    im=Image.open(io.BytesIO(content))
    if im.width<120 or im.height<120:
        raise ValueError("too small")
    if im.mode!="RGB": im=im.convert("RGB")
    im.thumbnail((1600,1600))
    im.save(f"images/{barcode}.jpg","JPEG",quality=92,optimize=True)
    print("SAVED",barcode,im.size)

def fetch(url, referer=None):
    h={"Accept":"image/avif,image/webp,image/apng,image/*,*/*;q=0.8"}
    if referer: h["Referer"]=referer
    r=S.get(url,timeout=25,allow_redirects=True,headers=h)
    r.raise_for_status()
    return r

# Correct every poster variant to the exact size-specific Dilmaçlar image.
for bc,url in DIRECT.items():
    try:
        r=fetch(url,"https://dilmaclar.com.tr/")
        save_jpg(bc,r.content)
    except Exception as e:
        print("DIRECT_FAIL",bc,url,e)

# Find the missing 250 ML hamster bottle from Bonisa's official site.
HAMSTER="8690000094646"
search_pages=[
 "https://bonisapet.com/urun-kategori/kemirgen/kemirgen-aksesuarlari/kemirgen-suluklari/",
 "https://bonisapet.com/?s=8690000094646&post_type=product",
 "https://bonisapet.com/?s=Bonisa+Hamster+Sulu%C4%9Fu+B%C3%BCy%C3%BCk+Boy+250+ML&post_type=product",
]
found=False
for page in search_pages:
    if found: break
    try:
        r=S.get(page,timeout=25,allow_redirects=True)
        r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        links=[]
        for a in soup.find_all("a",href=True):
            txt=(a.get_text(" ",strip=True)+" "+(a.get("title") or "")).lower()
            href=a["href"]
            if ("250" in txt and ("hamster" in txt or "sulu" in txt)) or "8690000094646" in txt:
                links.append(urljoin(page,href))
        # Also inspect cards/images on the listing page itself.
        for img in soup.find_all("img"):
            alt=(img.get("alt") or "").lower()
            if "250" in alt and ("hamster" in alt or "sulu" in alt):
                for key in ("data-large_image","data-src","data-lazy-src","src"):
                    u=img.get(key)
                    if u:
                        try:
                            rr=fetch(urljoin(page,u),page); save_jpg(HAMSTER,rr.content); found=True; break
                        except Exception: pass
            if found: break
        for product in links[:8]:
            if found: break
            try:
                pr=S.get(product,timeout=25,allow_redirects=True); pr.raise_for_status()
                ps=BeautifulSoup(pr.text,"html.parser")
                cands=[]
                for m in ps.find_all("meta"):
                    if m.get("property")=="og:image" or m.get("name")=="twitter:image":
                        if m.get("content"): cands.append(m["content"])
                for img in ps.find_all("img"):
                    for key in ("data-large_image","data-src","data-lazy-src","src"):
                        if img.get(key): cands.append(img.get(key))
                for u in cands:
                    low=u.lower()
                    if any(x in low for x in ("logo","icon","placeholder","loading")): continue
                    try:
                        rr=fetch(urljoin(product,u),product); save_jpg(HAMSTER,rr.content); found=True; print("HAMSTER_SOURCE",product,u); break
                    except Exception: pass
            except Exception as e:
                print("PRODUCT_FAIL",product,e)
    except Exception as e:
        print("SEARCH_FAIL",page,e)

if not found:
    print("HAMSTER_MISSING")
else:
    print("HAMSTER_OK")
