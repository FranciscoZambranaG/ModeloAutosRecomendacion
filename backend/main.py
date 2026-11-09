"""API del recomendador de autos (FastAPI).

Ejecutar:  uvicorn main:app --reload --port 8000
Documentación interactiva en http://localhost:8000/docs
"""
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from recomendador import Motor, recomendar_usuarios

RAIZ = Path(__file__).resolve().parent
DATA = RAIZ / "data"
MIN_CALIFICACIONES = 5

AUTOS: List[dict] = json.loads((DATA / "autos.json").read_text(encoding="utf-8"))
USUARIOS: List[dict] = json.loads((DATA / "usuarios.json").read_text(encoding="utf-8"))
EVALUACION: Optional[dict] = None
if (DATA / "evaluacion.json").exists():
    EVALUACION = json.loads((DATA / "evaluacion.json").read_text(encoding="utf-8"))

AUTOS_POR_ID = {a["id"]: a for a in AUTOS}
NOMBRES = {u["id"]: u["nombre"] for u in USUARIOS}
BASE = {u["id"]: u["calificaciones"] for u in USUARIOS}
MOTOR = Motor(AUTOS, BASE, k_svd=(EVALUACION or {}).get("k_svd", 4))

app = FastAPI(title="Recomendador de autos", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=RAIZ / "static"), name="static")


class PeticionRecomendar(BaseModel):
    calificaciones: Dict[str, int] = Field(default_factory=dict, description="auto_id -> estrellas (1 a 5)")
    usuario_id: Optional[str] = Field(None, description="Opcional: usar las notas de un usuario de ejemplo")
    n: int = Field(6, ge=1, le=12, description="Cuántas recomendaciones por método")


def _coincidencia(metodo: str, puntaje: float) -> int:
    if metodo == "contenido":
        return int(round(max(0.0, min(1.0, (puntaje + 1) / 2)) * 100))
    if metodo == "combinado":
        return int(round(puntaje * 100))
    return int(round((max(1.0, min(5.0, puntaje)) - 1) / 4 * 100))


def _nombre_auto(auto_id: str) -> str:
    return AUTOS_POR_ID[auto_id]["nombre"]


def _porque(metodo: str, r: dict) -> str:
    if metodo == "usuarios":
        nombres = [NOMBRES.get(u, u) for u, _ in r.get("aportes", [])[:2]]
        return f"Les gustó a personas con gustos parecidos a los tuyos ({' y '.join(nombres)})." if nombres else "Les gustó a personas con gustos parecidos."
    if metodo == "items":
        autos = [_nombre_auto(a) for a in r.get("aportes", [])[:2]]
        return f"Se parece a {' y '.join(autos)}, que calificaste alto." if autos else "Se parece a autos que calificaste."
    if metodo == "contenido":
        motivos = r.get("aportes", [])
        return "Comparte con tus favoritos → " + " · ".join(motivos) + "." if motivos else "Sus características encajan con tu perfil."
    if metodo == "svd":
        autos = [_nombre_auto(a) for a in r.get("aportes", [])[:2]]
        return f"Tus factores ocultos de gusto coinciden con los de {' y '.join(autos)}." if autos else "Encaja con tus factores ocultos de gusto."
    nombres = {"usuarios": "usuarios", "items": "ítems", "contenido": "contenido", "svd": "SVD"}
    metodos = [nombres[m] for m in r.get("metodos", [])]
    if len(metodos) >= 2:
        return f"Varios métodos lo ponen arriba: {', '.join(metodos)}."
    return f"Destaca en el método de {metodos[0]}." if metodos else "Puntaje combinado de los cuatro métodos."


def _armar(metodo: str, lista: List[dict], n: int) -> List[dict]:
    salida = []
    for r in lista[:n]:
        salida.append({
            "id": r["id"],
            "auto": AUTOS_POR_ID[r["id"]],
            "estrellas": round(r["puntaje"], 1) if metodo in ("usuarios", "items", "svd") else None,
            "coincidencia": _coincidencia(metodo, r["puntaje"]),
            "porque": _porque(metodo, r),
        })
    return salida


def _resumen(notas: Dict[str, int]) -> dict:
    favoritos = [a for a, n in sorted(notas.items(), key=lambda kv: -kv[1]) if n >= 4][:3]
    gustados = [AUTOS_POR_ID[a] for a, n in notas.items() if n >= 4]
    etiquetas = Counter()
    for a in gustados:
        etiquetas[a["pais"]] += 1
        etiquetas[a["categoria"]] += 1
        etiquetas[a["epoca"]] += 1
    top = [e for e, c in etiquetas.most_common(3) if c >= max(2, len(gustados) * 0.3)]
    return {
        "calificados": len(notas),
        "promedio": round(sum(notas.values()) / len(notas), 2),
        "favoritos": [_nombre_auto(a) for a in favoritos],
        "gustos": top,
    }


@app.get("/api/salud")
def salud():
    return {"ok": True, "autos": len(AUTOS), "usuarios": len(USUARIOS)}


@app.get("/api/autos")
def listar_autos():
    return AUTOS


@app.get("/api/autos/{auto_id}/similares")
def autos_similares(auto_id: str, n: int = 6):
    if auto_id not in AUTOS_POR_ID:
        raise HTTPException(404, "Ese auto no existe en el catálogo.")
    n = max(1, min(n, 12))
    por_contenido = [
        {"auto": AUTOS_POR_ID[i], "similitud": round(s, 3)} for s, i in MOTOR.contenido.similares(auto_id, n)
    ]
    por_gustos = [
        {"auto": AUTOS_POR_ID[i], "similitud": round(s, 3)}
        for s, i in MOTOR.items_similares.get(auto_id, [])[:n] if s > 0
    ]
    return {"auto": AUTOS_POR_ID[auto_id], "por_caracteristicas": por_contenido, "por_gustos_de_usuarios": por_gustos}


@app.get("/api/usuarios")
def listar_usuarios():
    return [
        {"id": u["id"], "nombre": u["nombre"], "perfil": u["perfil"], "calificados": len(u["calificaciones"])}
        for u in USUARIOS
    ]


@app.get("/api/usuarios/{usuario_id}")
def ver_usuario(usuario_id: str):
    if usuario_id not in BASE:
        raise HTTPException(404, "Ese usuario no existe.")
    u = next(x for x in USUARIOS if x["id"] == usuario_id)
    return {"id": u["id"], "nombre": u["nombre"], "perfil": u["perfil"], "calificaciones": u["calificaciones"]}


@app.post("/api/recomendar")
def recomendar(p: PeticionRecomendar):
    if p.usuario_id and p.usuario_id not in BASE:
        raise HTTPException(404, "Ese usuario no existe.")
    notas = dict(BASE[p.usuario_id]) if p.usuario_id else dict(p.calificaciones)
    desconocidos = [a for a in notas if a not in AUTOS_POR_ID]
    if desconocidos:
        raise HTTPException(422, f"Autos desconocidos: {', '.join(desconocidos[:3])}")
    if any(not 1 <= v <= 5 for v in notas.values()):
        raise HTTPException(422, "Las calificaciones deben estar entre 1 y 5 estrellas.")
    if len(notas) < MIN_CALIFICACIONES:
        raise HTTPException(422, f"Califica al menos {MIN_CALIFICACIONES} autos para poder recomendarte (llevas {len(notas)}).")
    if len(notas) >= len(AUTOS):
        raise HTTPException(422, "Ya calificaste todo el catálogo: no queda nada por recomendar.")

    listas = MOTOR.listas(notas)
    if p.usuario_id:  # quitar a la persona de sus propios vecinos (evita que se recomiende a sí misma)
        listas["usuarios"] = recomendar_usuarios(
            {u: v for u, v in BASE.items() if u != p.usuario_id}, notas, MOTOR.ids
        )
    listas["combinado"] = Motor.combinar(listas)
    return {
        "resumen": _resumen(notas),
        **{m: _armar(m, lista, p.n) for m, lista in listas.items()},
    }


@app.get("/api/evaluacion")
def evaluacion():
    if EVALUACION is None:
        raise HTTPException(404, "Aún no se ha ejecutado evaluar.py")
    return EVALUACION
