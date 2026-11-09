"""Descarga las fotos del catálogo desde Wikimedia Commons y genera data/autos.json.

Uso:  python scripts/construir_catalogo.py
Solo se aceptan imágenes alojadas en Commons (licencia libre); se guarda el crédito de cada una.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from catalogo_fuente import AUTOS  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
IMG_DIR = RAIZ / "static" / "autos"
SALIDA = RAIZ / "data" / "autos.json"
UA = {"User-Agent": "ModeloAutosEscolar/1.0 (proyecto academico de recomendacion)"}


def get(url, binario=False, intentos=5):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                datos = r.read()
            return datos if binario else json.loads(datos)
        except Exception as e:  # noqa: BLE001
            espera = 2 * (i + 1)
            print(f"   reintento {i + 1} ({e}); espero {espera}s")
            time.sleep(espera)
    return None


def limpiar(html):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", html or ""))).strip()


def imagen_de_wikipedia(titulo):
    q = urllib.parse.urlencode({
        "action": "query", "titles": titulo, "prop": "pageimages", "piprop": "thumbnail",
        "pithumbsize": 900, "redirects": 1, "format": "json",
    })
    data = get("https://en.wikipedia.org/w/api.php?" + q)
    if not data:
        return None
    for p in data["query"]["pages"].values():
        return p.get("thumbnail", {}).get("source")
    return None


def credito_commons(nombre_archivo):
    q = urllib.parse.urlencode({
        "action": "query", "titles": "File:" + nombre_archivo, "prop": "imageinfo",
        "iiprop": "extmetadata", "format": "json",
    })
    data = get("https://commons.wikimedia.org/w/api.php?" + q)
    try:
        page = next(iter(data["query"]["pages"].values()))
        meta = page["imageinfo"][0]["extmetadata"]
        return {
            "autor": limpiar(meta.get("Artist", {}).get("value", "Desconocido"))[:120],
            "licencia": limpiar(meta.get("LicenseShortName", {}).get("value", "")),
            "fuente": "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(nombre_archivo),
        }
    except Exception:  # noqa: BLE001
        return None


# Títulos alternativos de Wikipedia cuando el principal no trae foto libre o repite otra
ALTERNATIVAS = {
    "nissan-gtr-r35": ["Nissan GT-R (R35)", "Nissan GT-R Nismo"],
    "challenger-hellcat": ["Dodge Challenger SRT Hellcat", "Dodge Challenger (LC)"],
    "aston-vantage-2018": ["Aston Martin V8 Vantage (2018)", "Aston Martin Vantage"],
    "ford-gt-2017": ["Ford GT (2017)", "Ford GT"],
    "porsche-taycan": ["Porsche Taycan Turbo S"],
    "lamborghini-miura": ["Lamborghini Miura P400", "Lamborghini Miura SV"],
    "camaro-1969": ["Chevrolet Camaro Z/28", "Chevrolet Camaro (first generation)"],
    "jaguar-e-type": ["Jaguar E-type", "Jaguar E-Type Series 1"],
    "toyota-supra-a80": ["Toyota Supra (A80)", "Toyota Supra Mk IV"],
    "ford-model-t": ["Ford Model T", "Ford Model T (1927)"],
    "bmw-m3-e30": ["BMW M3 (E30)", "BMW 3 Series (E30)"],
}


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    previo = {a["id"]: a for a in json.loads(SALIDA.read_text(encoding="utf-8"))} if SALIDA.exists() else {}
    catalogo, fallos, vistos = [], [], {}
    for i, (slug, marca, modelo, anio, cat, pais, hp, titulo, desc) in enumerate(AUTOS, 1):
        if slug in previo:  # ya descargado: no se vuelve a pedir
            catalogo.append(previo[slug])
            c = previo[slug].get("credito") or {}
            vistos[urllib.parse.unquote(c.get("fuente", slug).split("File:")[-1])] = slug
            continue
        print(f"[{i}/{len(AUTOS)}] {marca} {modelo}")
        url = None
        for t in [titulo] + ALTERNATIVAS.get(slug, []):
            url = imagen_de_wikipedia(t)
            time.sleep(1.0)
            if url and "/wikipedia/commons/" in url:
                m0 = re.search(r"/commons/(?:thumb/)?\w/\w\w/([^/]+)", url)
                if m0 and urllib.parse.unquote(m0.group(1)) in vistos:
                    url = None
                    continue
                break
        if not url or "/wikipedia/commons/" not in url:
            print("   SIN imagen libre en Commons:", url)
            fallos.append((slug, titulo, "sin imagen libre"))
            continue
        m = re.search(r"/commons/(?:thumb/)?\w/\w\w/([^/]+)", url)
        nombre = urllib.parse.unquote(m.group(1)) if m else None
        if nombre in vistos:
            print(f"   imagen repetida con {vistos[nombre]}")
            fallos.append((slug, titulo, f"repetida con {vistos[nombre]}"))
            continue
        ext = ".png" if nombre and nombre.lower().endswith(".png") else ".jpg"
        destino = IMG_DIR / (slug + ext)
        if not destino.exists():
            datos = get(url, binario=True)
            if not datos:
                fallos.append((slug, titulo, "descarga fallida"))
                continue
            destino.write_bytes(datos)
        vistos[nombre] = slug
        cred = credito_commons(nombre) if nombre else None
        catalogo.append({
            "id": slug, "marca": marca, "modelo": modelo, "nombre": f"{marca} {modelo}",
            "anio": anio, "categoria": cat, "pais": pais, "hp": hp,
            "epoca": "Moderno" if anio >= 2005 else "Clásico",
            "descripcion": desc, "imagen": f"/static/autos/{destino.name}",
            "credito": cred,
        })
        time.sleep(1.0)
    SALIDA.write_text(json.dumps(catalogo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nListo: {len(catalogo)} autos guardados en {SALIDA}")
    if fallos:
        print("Fallos:")
        for f in fallos:
            print("  ", f)


if __name__ == "__main__":
    main()
