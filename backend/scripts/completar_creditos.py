"""Completa los créditos de foto que faltan (por límites de velocidad de la API de Wikipedia)."""
import json, re, sys, time, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogo_fuente import AUTOS
from construir_catalogo import ALTERNATIVAS, SALIDA, RAIZ, get, imagen_de_wikipedia, credito_commons

catalogo = json.loads(SALIDA.read_text(encoding="utf-8"))
titulos = {a[0]: a[7] for a in AUTOS}
for auto in catalogo:
    if auto.get("credito"):
        continue
    local = (RAIZ / auto["imagen"].lstrip("/")).read_bytes()
    for t in [titulos[auto["id"]]] + ALTERNATIVAS.get(auto["id"], []):
        url = imagen_de_wikipedia(t); time.sleep(1.2)
        if not url or "/wikipedia/commons/" not in url:
            continue
        if get(url, binario=True) != local:
            continue
        nombre = urllib.parse.unquote(re.search(r"/commons/(?:thumb/)?\w/\w\w/([^/]+)", url).group(1))
        auto["credito"] = credito_commons(nombre); time.sleep(1.2)
        print(auto["id"], "->", nombre, auto["credito"] and auto["credito"]["licencia"])
        break
    else:
        print("sin crédito:", auto["id"])
SALIDA.write_text(json.dumps(catalogo, ensure_ascii=False, indent=1), encoding="utf-8")
