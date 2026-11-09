import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
NOTAS = {"ferrari-f40": 5, "lamborghini-countach": 5, "porsche-959": 4, "ford-model-t": 1, "vw-beetle": 2}


def test_salud_y_catalogo():
    assert client.get("/api/salud").json()["ok"] is True
    autos = client.get("/api/autos").json()
    assert len(autos) >= 60
    assert {"id", "nombre", "anio", "pais", "hp", "categoria", "epoca", "imagen", "credito"} <= set(autos[0])


def test_imagenes_se_sirven():
    autos = client.get("/api/autos").json()
    for a in autos[:5] + autos[-5:]:
        r = client.get(a["imagen"])
        assert r.status_code == 200 and r.headers["content-type"].startswith("image/")


def test_recomendar_devuelve_cinco_listas():
    r = client.post("/api/recomendar", json={"calificaciones": NOTAS, "n": 4})
    assert r.status_code == 200
    d = r.json()
    assert d["resumen"]["calificados"] == 5
    for metodo in ("combinado", "usuarios", "items", "contenido", "svd"):
        assert len(d[metodo]) == 4, metodo
        for rec in d[metodo]:
            assert rec["id"] not in NOTAS
            assert rec["auto"]["imagen"].startswith("/static/autos/")
            assert 0 <= rec["coincidencia"] <= 100
            assert rec["porque"]
    assert all(r["estrellas"] is not None and 1 <= r["estrellas"] <= 5 for r in d["svd"])
    assert all(r["estrellas"] is None for r in d["contenido"])


def test_minimo_cinco_calificaciones():
    r = client.post("/api/recomendar", json={"calificaciones": {"ferrari-f40": 5, "vw-beetle": 3}})
    assert r.status_code == 422 and "al menos 5" in r.json()["detail"]


@pytest.mark.parametrize("cuerpo", [
    {"calificaciones": {**NOTAS, "auto-inventado": 3}},
    {"calificaciones": {**NOTAS, "mclaren-f1": 9}},
    {"calificaciones": {**NOTAS, "mclaren-f1": 0}},
])
def test_validaciones(cuerpo):
    assert client.post("/api/recomendar", json=cuerpo).status_code == 422


def test_n_fuera_de_rango():
    assert client.post("/api/recomendar", json={"calificaciones": NOTAS, "n": 99}).status_code == 422


def test_usuario_de_ejemplo():
    usuarios = client.get("/api/usuarios").json()
    assert len(usuarios) >= 40
    uid = usuarios[0]["id"]
    detalle = client.get(f"/api/usuarios/{uid}").json()
    r = client.post("/api/recomendar", json={"usuario_id": uid})
    assert r.status_code == 200
    ya = set(detalle["calificaciones"])
    for metodo in ("combinado", "usuarios", "items", "contenido", "svd"):
        assert not ya & {x["id"] for x in r.json()[metodo]}, metodo
    assert client.get("/api/usuarios/zzz").status_code == 404
    assert client.post("/api/recomendar", json={"usuario_id": "zzz"}).status_code == 404


def test_autos_similares():
    r = client.get("/api/autos/ferrari-f40/similares?n=5")
    assert r.status_code == 200
    d = r.json()
    assert len(d["por_caracteristicas"]) == 5
    assert all(x["auto"]["id"] != "ferrari-f40" for x in d["por_caracteristicas"] + d["por_gustos_de_usuarios"])
    assert client.get("/api/autos/nope/similares").status_code == 404


def test_evaluacion():
    d = client.get("/api/evaluacion").json()
    assert d["metodos"]["svd"]["rmse"] < d["metodos"]["base"]["rmse"]
    assert d["ranking"]["combinado"]["acierto_10"] > d["ranking"]["popularidad"]["acierto_10"]
