import json
from math import isclose, sqrt
from pathlib import Path

import numpy as np
import pytest

from recomendador import (Motor, ModeloContenido, ModeloSVD, euclidiana, get_similares, invertir,
                          recomendar_usuarios)

DATA = Path(__file__).resolve().parent.parent / "data"
AUTOS = json.loads((DATA / "autos.json").read_text(encoding="utf-8"))
USUARIOS = json.loads((DATA / "usuarios.json").read_text(encoding="utf-8"))
BASE = {u["id"]: u["calificaciones"] for u in USUARIOS}


def test_euclidiana_identicos_y_distintos():
    base = {"a": {"x": 5, "y": 4, "z": 3}, "b": {"x": 5, "y": 4, "z": 3}, "c": {"x": 1, "y": 1, "z": 1}}
    assert euclidiana(base, "a", "b") == 1.0
    assert 0 < euclidiana(base, "a", "c") < 0.5


def test_euclidiana_valor_manual():
    base = {"a": {"x": 3.0, "y": 3.5, "z": 1.0}, "b": {"x": 3.0, "y": 4.0, "z": 1.0}}
    # diferencias: 0, 0.5, 0 -> suma 0.25 / 3 comunes
    assert isclose(euclidiana(base, "a", "b"), 1 / (1 + sqrt(0.25 / 3)))


def test_euclidiana_exige_minimo_en_comun():
    base = {"a": {"x": 5, "y": 5}, "b": {"x": 5, "y": 5}}
    assert euclidiana(base, "a", "b") == 0.0           # solo 2 en común
    assert euclidiana(base, "a", "b", min_comunes=2) == 1.0


def test_get_similares_ordena_de_mayor_a_menor():
    base = {"a": {"x": 5, "y": 4, "z": 3}, "b": {"x": 5, "y": 4, "z": 3}, "c": {"x": 1, "y": 1, "z": 1}}
    res = get_similares(base, "a")
    assert [o for _, o in res] == ["b", "c"]
    assert res[0][0] >= res[1][0]


def test_invertir_es_involutiva():
    assert invertir(invertir(BASE)) == BASE


def test_catalogo_consistente():
    ids = [a["id"] for a in AUTOS]
    assert len(ids) == len(set(ids)) >= 60
    for a in AUTOS:
        assert Path(DATA.parent, a["imagen"].lstrip("/")).exists(), a["id"]
        assert a["credito"] and a["credito"]["fuente"].startswith("https://commons.wikimedia.org/")
        assert a["epoca"] in ("Moderno", "Clásico")
    assert {"Moderno", "Clásico"} == {a["epoca"] for a in AUTOS}
    for u in USUARIOS:
        assert set(u["calificaciones"]) <= set(ids)
        assert all(1 <= v <= 5 for v in u["calificaciones"].values())


@pytest.fixture(scope="module")
def motor():
    return Motor(AUTOS, BASE, k_svd=3)


def test_no_recomienda_lo_ya_calificado(motor):
    notas = {"ferrari-f40": 5, "lamborghini-countach": 5, "porsche-959": 4, "mclaren-f1": 5, "ferrari-testarossa": 4}
    for metodo, lista in motor.listas(notas).items():
        ids = [r["id"] for r in lista]
        assert not set(ids) & set(notas), metodo
        assert len(ids) == len(set(ids)), metodo
        assert lista == sorted(lista, key=lambda r: r["puntaje"], reverse=True), metodo
        assert len(lista) > 20, metodo


def test_gustos_italianos_recomiendan_italianos(motor):
    notas = {"ferrari-f40": 5, "lamborghini-countach": 5, "ferrari-testarossa": 5, "pagani-huayra": 5,
             "ford-model-t": 1, "vw-beetle": 1, "dodge-charger-1969": 2}
    for metodo in ("contenido", "svd", "items", "usuarios"):
        top = [motor.autos[r["id"]] for r in motor.listas(notas)[metodo][:10]]
        italianos = sum(1 for a in top if a["pais"] == "Italia")
        assert italianos >= 3, (metodo, [a["nombre"] for a in top])


def test_gustos_opuestos_cambian_resultado(motor):
    italiano = {"ferrari-f40": 5, "lamborghini-countach": 5, "ferrari-testarossa": 5, "pagani-huayra": 5, "maserati-mc20": 4}
    jdm = {"nissan-skyline-r34": 5, "mazda-rx7-fd": 5, "datsun-240z": 5, "toyota-2000gt": 5, "honda-nsx-1990": 4}
    for metodo in ("contenido", "svd", "combinado"):
        a = motor.listas(italiano)
        b = motor.listas(jdm)
        a["combinado"], b["combinado"] = Motor.combinar(a), Motor.combinar(b)
        top_a = [r["id"] for r in a[metodo][:5]]
        top_b = [r["id"] for r in b[metodo][:5]]
        assert top_a != top_b, metodo


def test_svd_predice_en_rango_y_reconstruye(motor):
    ids = [a["id"] for a in AUTOS]
    for uid in list(BASE)[:5]:
        notas = BASE[uid]
        for auto in ids[:10]:
            assert 1.0 <= motor.svd.predecir(notas, auto) <= 5.0
    # el modelo ajustado explica mejor las notas de entrenamiento que el promedio global
    errores_svd = [motor.svd.predecir({k: v for k, v in n.items() if k != a}, a) - v
                   for n in list(BASE.values())[:30] for a, v in list(n.items())[:3]]
    media = np.mean([v for n in BASE.values() for v in n.values()])
    errores_base = [media - v for n in list(BASE.values())[:30] for _, v in list(n.items())[:3]]
    assert np.sqrt(np.mean(np.square(errores_svd))) < np.sqrt(np.mean(np.square(errores_base)))


def test_contenido_similares_incluye_misma_marca():
    cont = ModeloContenido(AUTOS)
    cercanos = [i for _, i in cont.similares("ferrari-f40", 5)]
    assert "ferrari-f40" not in cercanos
    assert any(i.startswith(("ferrari", "lamborghini", "porsche-959", "mclaren-f1")) for i in cercanos)


def test_usuario_nuevo_sin_nada_en_comun_no_rompe(motor):
    # un solo auto calificado: ningún usuario llega al mínimo de coincidencias, no debe fallar
    res = recomendar_usuarios(BASE, {"ford-model-t": 5}, motor.ids)
    assert res == []


def test_combinar_normaliza_entre_0_y_1(motor):
    notas = {"ferrari-f40": 5, "lamborghini-countach": 5, "porsche-959": 4, "mclaren-f1": 5, "ferrari-testarossa": 4}
    comb = Motor.combinar(motor.listas(notas))
    assert all(0 <= r["puntaje"] <= 1 for r in comb)
    assert comb[0]["puntaje"] >= comb[-1]["puntaje"]
