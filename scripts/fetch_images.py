import io, os, re, sys, time, xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from PIL import Image

BASE = "https://dilmaclar.com.tr/"
TARGETS = {
"8690000036813":"BONISA PLASTIK BITKI 5 LI PAKET BNS-3681",
"8690000127801":"DAWCAT YUSUFCUK KEDI OLTASI",
"8690000010752":"BONISA PLASTIK BITKI BNS-1075",
"8690000038541":"BONISA PLASTIK BITKI 2 LI PAKET BNS-3854",
"8690000036714":"BONISA PLASTIK BITKI BNS-3671",
"8690000036851":"BONISA PLASTIK BITKI 5 LI PAKET BNS-3685",
"8690000038022":"BONISA PLASTIK BITKI BNS-3802",
"8690000036844":"BONISA PLASTIK BITKI 5 LI PAKET BNS-3684",
"8690000010714":"BONISA PLASTIK BITKI BNS-1071",
"8690000036875":"BONISA PLASTIK BITKI 5 LI PAKET BNS-3687",
"6975886010396":"CHONG HENG TERMOMETRE SIVI DOLGULU YUVARLAK",
"6975886010617":"CHONG HENG DIJITAL TERMOMETRE CS-703A",
"6979166870083":"CHONG HENG TERMOMETRE",
"8690000130207":"BONISA PLASTIK POSTER 8007 8008 BITKI DENIZ 60 CM",
"8690000130191":"BONISA PLASTIK POSTER 8007 8008 BITKI DENIZ 50 CM",
"8690000130184":"BONISA PLASTIK POSTER 8007 8008 BITKI DENIZ 40 CM",
"8690000130177":"BONISA PLASTIK POSTER 8007 8008 BITKI DENIZ 30 CM",
"8690000130405":"BONISA PLASTIK POSTER 8075 9024 SIYAH BITKI MERCAN 60 CM",
"8690000130399":"BONISA PLASTIK POSTER 8075 9024 SIYAH BITKI MERCAN 50 CM",
"8690000130382":"BONISA PLASTIK POSTER 8075 9024 SIYAH BITKI MERCAN 40 CM",
"8690000130375":"BONISA PLASTIK POSTER 8075 9024 SIYAH BITKI MERCAN 30 CM",
"8690000130320":"BONISA PLASTIK POSTER 9099 9091 MERCAN TAS 60 CM",
"8690000130306":"BONISA PLASTIK POSTER 9099 9091 MERCAN TAS 40 CM",
"8690000130313":"BONISA PLASTIK POSTER 9099 9091 MERCAN TAS 50 CM",
"8690000130290":"BONISA PLASTIK POSTER 9099 9091 MERCAN TAS 30 CM",
"8288147578527":"SOBO L-28C-RED AKVARYUM LAMBASI MINI LED KIRMIZI",
"8690000094646":"BONISA HAMSTER SULUGU BUYUK 250 ML",
"8690000130528":"BONISA PLASTIK POSTER 3x3 SIYAH 60 CM",
"8690000130511":"BONISA PLASTIK POSTER 3x3 SIYAH 50 CM",
"8690000130498":"BONISA PLASTIK POSTER 3x3 SIYAH 30 CM",
"8690000130481":"BONISA PLASTIK POSTER 3x3 MAVI 60 CM",
"8690000130474":"BONISA PLASTIK POSTER 3x3 MAVI 50 CM",
"8690000130467":"BONISA PLASTIK POSTER 3x3 MAVI 40 CM",
"8690000130450":"BONISA PLASTIK POSTER 3x3 MAVI 30 CM",
}

S = requests.Session()
S.headers.update({
    "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
    "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.7",
})

def get(url, **kw):
    for attempt in range(3):
        try:
            r=S.get(url, timeout=30, allow_redirects=True, **kw)
            if r.status_code < 400:
                return r
        except Exception as e:
            if attempt == 2: print("GET FAIL", url, e)
        time.sleep(1.5*(attempt+1))
    return None

def collect_sitemap_urls():
    roots=[
        urljoin(BASE,"sitemap.xml"),
        urljoin(BASE,"sitemap_index.xml"),
        "https://ipv4.dilmaclar.com.tr/sitemap.xml",
    ]
    seen=set(); product_urls=[]
    queue=roots[:]
    while queue and len(seen)<200:
        u=queue.pop(0)
        if u in seen: continue
        seen.add(u)
        r=get(u)
        if not r: continue
        text=r.text.strip()
        if not text.startswith("<"): continue
        try: root=ET.fromstring(text)
        except Exception: continue
        locs=[x.text.strip() for x in root.iter() if x.tag.lower().endswith("loc") and x.text]
        if root.tag.lower().endswith("sitemapindex"):
            queue.extend([x for x in locs if x not in seen])
        else:
            for x in locs:
                if "/prd-" in x:
                    product_urls.append(x.replace("https://ipv4.dilmaclar.com.tr/","https://dilmaclar.com.tr/"))
    return list(dict.fromkeys(product_urls))

def normalize(s):
    table=str.maketrans("ÇĞİÖŞÜçğıöşüÂâ","CGIOSUcgiosuAa")
    return re.sub(r"[^A-Z0-9]+"," ",s.translate(table).upper()).strip()

def page_barcode(soup):
    txt=soup.get_text(" ", strip=True)
    m=re.search(r"Barkodu\s*:?\s*(\d{8,14})",txt,re.I)
    if m: return m.group(1)
    for bc in TARGETS:
        if bc in txt: return bc
    return None

def image_candidates(soup, page_url):
    cands=[]
    for attrs in [
        {"property":"og:image"},{"name":"twitter:image"},{"itemprop":"image"}
    ]:
        for tag in soup.find_all(["meta","link"],attrs=attrs):
            v=tag.get("content") or tag.get("href")
            if v: cands.append(v)
    for img in soup.find_all("img"):
        for key in ("data-zoom-image","data-large","data-src","data-original","src"):
            v=img.get(key)
            if v: cands.append(v)
    out=[]
    for v in cands:
        v=urljoin(page_url,v)
        low=v.lower()
        if any(b in low for b in ["loading","logo","icon","spinner","taksit","payment","banner","avatar","blank"]):
            continue
        if v not in out: out.append(v)
    return out

def save_image(bc, page_url, candidates):
    os.makedirs("images",exist_ok=True)
    for u in candidates:
        r=get(u, headers={"Referer":page_url,"Accept":"image/avif,image/webp,image/apng,image/*,*/*;q=0.8"})
        if not r or not r.content or len(r.content)<1500: continue
        ctype=(r.headers.get("content-type") or "").lower()
        if "image" not in ctype and not re.search(r"\.(jpe?g|png|webp)(\?|$)",u,re.I):
            continue
        try:
            im=Image.open(io.BytesIO(r.content))
            if im.width<120 or im.height<120: continue
            if im.mode not in ("RGB","L"): im=im.convert("RGB")
            elif im.mode=="L": im=im.convert("RGB")
            # Keep a BizimHesap-friendly JPEG, reasonably sized.
            im.thumbnail((1600,1600))
            out=f"images/{bc}.jpg"
            im.save(out,"JPEG",quality=90,optimize=True)
            print("SAVED",bc,im.size,u)
            return True
        except Exception:
            continue
    return False

def main():
    urls=collect_sitemap_urls()
    print("PRODUCT URL COUNT",len(urls))
    found=set()
    # First pass: exact barcode from product page.
    for i,u in enumerate(urls,1):
        if len(found)==len(TARGETS): break
        r=get(u)
        if not r: continue
        soup=BeautifulSoup(r.text,"html.parser")
        bc=page_barcode(soup)
        if bc in TARGETS and bc not in found:
            if save_image(bc,u,image_candidates(soup,u)):
                found.add(bc)
                print("MATCH",bc,TARGETS[bc],u)
        if i%100==0: print("SCANNED",i,"FOUND",len(found))
    # Second pass: known product pages may not expose barcode clearly; match code/name tokens.
    missing=set(TARGETS)-found
    if missing:
        for u in urls:
            if not missing: break
            slug=normalize(urlparse(u).path)
            for bc in list(missing):
                name=normalize(TARGETS[bc])
                tokens=[t for t in name.split() if len(t)>=4]
                score=sum(1 for t in tokens if t in slug)
                if score>=max(2,min(5,len(tokens)//2)):
                    r=get(u)
                    if not r: continue
                    soup=BeautifulSoup(r.text,"html.parser")
                    txt=normalize(soup.get_text(" ",strip=True))
                    if bc in soup.get_text(" ",strip=True) or sum(1 for t in tokens if t in txt)>=max(3,min(6,len(tokens)//2)):
                        if save_image(bc,u,image_candidates(soup,u)):
                            found.add(bc); missing.remove(bc)
                            print("FUZZY MATCH",bc,u)
                            break
    print("FOUND",len(found),"OF",len(TARGETS))
    if missing:
        print("MISSING",",".join(sorted(missing)))
        with open("missing.txt","w",encoding="utf-8") as f:
            for bc in sorted(missing): f.write(bc+"\t"+TARGETS[bc]+"\n")
    with open("manifest.tsv","w",encoding="utf-8") as f:
        f.write("barcode\tname\tstatus\n")
        for bc,n in TARGETS.items():
            f.write(f"{bc}\t{n}\t{'ok' if os.path.exists('images/'+bc+'.jpg') else 'missing'}\n")

if __name__=="__main__":
    main()
