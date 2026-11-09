"""Evalúa los métodos con calificaciones apartadas (validación repetida) y guarda data/evaluacion.json.

Métricas:
  RMSE        error al predecir la nota de autos que el usuario sí calificó pero ocultamos (menor es mejor)
  cobertura   % de esas notas que el método pudo predecir por sí mismo (sin recurrir al promedio del auto)
  acierto@10  % de usuarios para los que el top 10 contiene al menos un auto que les gustó (nota >= 4) y estaba oculto
  precision@10  de los 10 recomendados, cuántos eran autos que les gustaron y estaban ocultos

Uso:  python evaluar.py
"""
import json
import random
from pathlib import Path

import numpy as np

from recomendador import (Motor, ModeloSVD, predecir_items, predecir_usuarios, METODOS)

RAIZ = Path(__file__).resolve().parent
DATA = RAIZ / "data"
SALIDA = DATA / "evaluacion.json"


def cargar():
    autos = json.loads((DATA / "autos.json").read_text(encoding="utf-8"))
    usuarios = json.loads((DATA / "usuarios.json").read_text(encoding="utf-8"))
    return autos, usuarios


def dividir(usuarios, semilla, fraccion=0.25):
    rng = random.Random(semilla)
    train, test = {}, {}
    for u in usuarios:
        items = list(u["calificaciones"].items())
        rng.shuffle(items)
        n_test = max(2, int(len(items) * fraccion)) if len(items) >= 8 else 0
        test[u["id"]] = dict(items[:n_test])
        train[u["id"]] = dict(items[n_test:])
    return train, test


def _media_item(base_usuarios):
    suma, cuenta = {}, {}
    for notas in base_usuarios.values():
        for a, n in notas.items():
            suma[a] = suma.get(a, 0) + n
            cuenta[a] = cuenta.get(a, 0) + 1
    todas = [n for notas in base_usuarios.values() for n in notas.values()]
    return {a: suma[a] / cuenta[a] for a in suma}, float(np.mean(todas))


def rmse(errores):
    return float(np.sqrt(np.mean(np.square(errores)))) if errores else None


def evaluar(semillas=(1, 2, 3, 4, 5), ks=range(1, 9), n_top=10):
    autos, usuarios = cargar()
    ids = [a["id"] for a in autos]
    err = {m: [] for m in ("base", "usuarios", "items", "svd")}
    cubiertos = {m: 0 for m in ("usuarios", "items", "svd")}
    total_pred = 0
    err_k = {k: [] for k in ks}
    claves_rank = ("popularidad", *METODOS, "combinado")
    hits = {m: [] for m in claves_rank}
    prec = {m: [] for m in claves_rank}

    for semilla in semillas:
        train, test = dividir(usuarios, semilla)
        motor = Motor(autos, train, k_svd=4)
        media_item, media_global = _media_item(train)
        modelos_k = {k: ModeloSVD(k=k).fit(train, ids) for k in ks}

        for uid, ocultas in test.items():
            if not ocultas:
                continue
            notas = train[uid]
            otros = {u: v for u, v in train.items() if u != uid}
            for auto, real in ocultas.items():
                total_pred += 1
                base_pred = media_item.get(auto, media_global)
                err["base"].append(base_pred - real)
                p, _ = predecir_usuarios(otros, notas, auto)
                if p is not None:
                    cubiertos["usuarios"] += 1
                err["usuarios"].append((p if p is not None else base_pred) - real)
                # similitud entre autos calculada sin este usuario para no filtrar información
                p, _ = predecir_items(motor.items_similares, notas, auto)
                if p is not None:
                    cubiertos["items"] += 1
                err["items"].append((p if p is not None else base_pred) - real)
                cubiertos["svd"] += 1
                err["svd"].append(motor.svd.predecir(notas, auto) - real)
                for k, m in modelos_k.items():
                    err_k[k].append(m.predecir(notas, auto) - real)

            # ranking
            relevantes = {a for a, n in ocultas.items() if n >= 4}
            if not relevantes:
                continue
            listas = motor.listas(notas)
            listas["combinado"] = Motor.combinar(listas)
            populares = sorted((a for a in ids if a not in notas), key=lambda a: -media_item.get(a, media_global))
            listas["popularidad"] = [{"id": a} for a in populares]
            for m, lista in listas.items():
                top = [r["id"] for r in lista[:n_top]]
                aciertos = len(relevantes & set(top))
                hits[m].append(1.0 if aciertos else 0.0)
                prec[m].append(aciertos / n_top)

    res = {
        "descripcion": f"Validación repetida con {len(semillas)} particiones; se oculta ~25% de las notas de cada usuario.",
        "n_usuarios": len(usuarios),
        "n_autos": len(autos),
        "n_calificaciones": sum(len(u["calificaciones"]) for u in usuarios),
        "metodos": {
            "base": {"nombre": "Promedio del auto (línea base)", "rmse": rmse(err["base"]), "cobertura": 1.0},
            "usuarios": {"nombre": "Por usuarios", "rmse": rmse(err["usuarios"]), "cobertura": cubiertos["usuarios"] / total_pred},
            "items": {"nombre": "Por ítems", "rmse": rmse(err["items"]), "cobertura": cubiertos["items"] / total_pred},
            "svd": {"nombre": "SVD (factores ocultos)", "rmse": rmse(err["svd"]), "cobertura": 1.0},
            "contenido": {"nombre": "Por contenido", "rmse": None, "cobertura": 1.0},
            "popularidad": {"nombre": "Los más populares (línea base)", "rmse": None, "cobertura": 1.0},
            "combinado": {"nombre": "Combinado", "rmse": None, "cobertura": 1.0},
        },
        "ranking": {m: {"acierto_10": float(np.mean(hits[m])), "precision_10": float(np.mean(prec[m]))} for m in hits},
        "curva_svd": {str(k): rmse(v) for k, v in err_k.items()},
    }
    mejor_k = min(err_k, key=lambda k: rmse(err_k[k]))
    res["k_svd"] = int(mejor_k)
    res["metodos"]["svd"]["rmse"] = res["curva_svd"][str(mejor_k)]
    return res


if __name__ == "__main__":
    r = evaluar()
    SALIDA.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(r["descripcion"])
    print(f"{'método':34s} {'RMSE':>6s} {'cobert.':>8s} {'acierto@10':>11s} {'prec@10':>8s}")
    for m, d in r["metodos"].items():
        rk = r["ranking"].get(m)
        rm = f"{d['rmse']:.3f}" if d["rmse"] else "  -"
        print(f"{d['nombre']:34s} {rm:>6s} {d['cobertura']:>8.0%} "
              f"{(rk['acierto_10'] if rk else float('nan')):>11.0%} {(rk['precision_10'] if rk else float('nan')):>8.1%}")
    print("curva SVD (k -> RMSE):", {k: round(v, 3) for k, v in r["curva_svd"].items()}, "| mejor k =", r["k_svd"])
