import io, os, re, time, xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from PIL import Image

BASE="https://dilmaclar.com.tr/"
TARGETS={
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
"8690000130207":"BONISA PLASTIK POSTER 8007 8008 BITKI DENIZ 15 METRE 60 CM",
"8690000130191":"BONISA PLASTIK POSTER 8007 8008 BITKI DENIZ 15 METRE 50 CM",
"8690000130184":"BONISA PLASTIK POSTER 8007 8008 BITKI DENIZ 15 METRE 40 CM",
"8690000130177":"BONISA PLASTIK POSTER 8007 8008 BITKI DENIZ 15 METRE 30 CM",
"8690000130405":"BONISA PLASTIK POSTER 8075 9024 SIYAH BITKI MERCAN 15 METRE 60 CM",
"8690000130399":"BONISA PLASTIK POSTER 8075 9024 SIYAH BITKI MERCAN 15 METRE 50 CM",
"8690000130382":"BONISA PLASTIK POSTER 8075 9024 SIYAH BITKI MERCAN 15 METRE 40 CM",
"8690000130375":"BONISA PLASTIK POSTER 8075 9024 SIYAH BITKI MERCAN 15 METRE 30 CM",
"8690000130320":"BONISA PLASTIK POSTER 9099 9091 MERCAN TAS 15 METRE 60 CM",
"8690000130306":"BONISA PLASTIK POSTER 9099 9091 MERCAN TAS 15 METRE 40 CM",
"8690000130313":"BONISA PLASTIK POSTER 9099 9091 MERCAN TAS 15 METRE 50 CM",
"8690000130290":"BONISA PLASTIK POSTER 9099 9091 MERCAN TAS 15 METRE 30 CM",
"8288147578527":"SOBO L-28C-RED AKVARYUM LAMBASI MINI LED KIRMIZI",
"8690000094646":"BONISA HAMSTER SULUGU BUYUK 250 ML",
"8690000130528":"BONISA PLASTIK POSTER 3x3 SIYAH 15 METRE 60 CM",
"8690000130511":"BONISA PLASTIK POSTER 3x3 SIYAH 15 METRE 50 CM",
"8690000130498":"BONISA PLASTIK POSTER 3x3 SIYAH 15 METRE 30 CM",
"8690000130481":"BONISA PLASTIK POSTER 3x3 MAVI 15 METRE 60 CM",
"8690000130474":"BONISA PLASTIK POSTER 3x3 MAVI 15 METRE 50 CM",
"8690000130467":"BONISA PLASTIK POSTER 3x3 MAVI 15 METRE 40 CM",
"8690000130450":"BONISA PLASTIK POSTER 3x3 MAVI 15 METRE 30 CM",
}

S=requests.Session()
S.headers.update({"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36","Accept-Language":"tr-TR,tr;q=0.9,en;q=0.7"})

def get(url, **kw):
    try:
        r=S.get(url,timeout=15,allow_redirects=True,**kw)
        if r.status_code<400:return r
    except Exception as e:
        print("GET_FAIL",url,e)
    return None

def norm(s):
    table=str.maketrans("ÇĞİÖŞÜçğıöşüÂâ","CGIOSUcgiosuAa")
    return re.sub(r"[^A-Z0-9]+"," ",s.translate(table).upper()).strip()

def sitemap_urls():
    q=[urljoin(BASE,"sitemap.xml"),urljoin(BASE,"sitemap_index.xml"),"https://ipv4.dilmaclar.com.tr/sitemap.xml"]
    seen=set(); out=[]
    while q and len(seen)<80:
        u=q.pop(0)
        if u in seen:continue
        seen.add(u)
        r=get(u)
        if not r:continue
        try:root=ET.fromstring(r.text)
        except:continue
        locs=[e.text.strip() for e in root.iter() if e.tag.lower().endswith("loc") and e.text]
        if root.tag.lower().endswith("sitemapindex"):q.extend(locs)
        else:out.extend(x for x in locs if "/prd-" in x)
    return list(dict.fromkeys(x.replace("https://ipv4.dilmaclar.com.tr/","https://dilmaclar.com.tr/") for x in out))

def score_url(name,u):
    n=norm(name); s=norm(urlparse(u).path)
    toks=[x for x in n.split() if len(x)>=3]
    # strong identifiers
    strong=[x for x in toks if x.startswith("BNS") or re.match(r"\d{4}$",x) or "L-28C" in x]
    score=sum(8 for x in strong if x in s)
    score+=sum(1 for x in toks if x in s)
    return score

def extract_barcode(soup):
    txt=soup.get_text(" ",strip=True)
    m=re.search(r"Barkodu\s*:?\s*(\d{8,14})",txt,re.I)
    return m.group(1) if m else None

def candidates(soup,page):
    vals=[]
    for tag in soup.find_all(["meta","link"]):
        if tag.get("property")=="og:image" or tag.get("name")=="twitter:image" or tag.get("itemprop")=="image":
            v=tag.get("content") or tag.get("href")
            if v:vals.append(v)
    for img in soup.find_all("img"):
        for k in ("data-zoom-image","data-large","data-src","data-original","src"):
            v=img.get(k)
            if v:vals.append(v)
    out=[]
    for v in vals:
        v=urljoin(page,v)
        low=v.lower()
        if any(x in low for x in ("loading","logo","spinner","icon","taksit","payment","banner","blank","noimage")):continue
        if v not in out:out.append(v)
    return out

def save_image(bc,page,urls):
    os.makedirs("images",exist_ok=True)
    for u in urls:
        r=get(u,headers={"Referer":page,"Accept":"image/avif,image/webp,image/apng,image/*,*/*;q=0.8"})
        if not r or len(r.content)<2000:continue
        try:
            im=Image.open(io.BytesIO(r.content))
            if im.width<150 or im.height<150:continue
            if im.mode!="RGB":im=im.convert("RGB")
            im.thumbnail((1600,1600))
            im.save(f"images/{bc}.jpg","JPEG",quality=90,optimize=True)
            print("SAVED",bc,im.size,u)
            return True
        except Exception:pass
    return False

def main():
    urls=sitemap_urls()
    print("SITEMAP_PRODUCTS",len(urls))
    found=set()
    # Only fetch top-scoring URL candidates per target; avoids crawling the entire catalog.
    for bc,name in TARGETS.items():
        ranked=sorted(((score_url(name,u),u) for u in urls),reverse=True)
        best=[u for sc,u in ranked[:8] if sc>0]
        print("TARGET",bc,name,"CANDIDATES",[(score_url(name,u),u) for u in best[:3]])
        for u in best:
            r=get(u)
            if not r:continue
            soup=BeautifulSoup(r.text,"html.parser")
            pagebc=extract_barcode(soup)
            title=norm((soup.find("h1").get_text(" ",strip=True) if soup.find("h1") else soup.title.get_text(" ",strip=True) if soup.title else ""))
            # exact barcode wins; otherwise require a strong title match.
            name_toks=[x for x in norm(name).split() if len(x)>=4]
            title_hits=sum(1 for x in name_toks if x in title)
            if pagebc==bc or title_hits>=max(3,min(6,len(name_toks)//2)):
                if save_image(bc,u,candidates(soup,u)):
                    found.add(bc);break
        if bc not in found:print("MISS",bc,name)
    with open("manifest.tsv","w",encoding="utf-8") as f:
        f.write("barcode\tname\tstatus\n")
        for bc,n in TARGETS.items():
            f.write(f"{bc}\t{n}\t{'ok' if os.path.exists('images/'+bc+'.jpg') else 'missing'}\n")
    with open("missing.txt","w",encoding="utf-8") as f:
        for bc,n in TARGETS.items():
            if not os.path.exists(f"images/{bc}.jpg"):f.write(bc+"\t"+n+"\n")
    print("FOUND",sum(os.path.exists(f"images/{bc}.jpg") for bc in TARGETS),"OF",len(TARGETS))

if __name__=="__main__":main()
