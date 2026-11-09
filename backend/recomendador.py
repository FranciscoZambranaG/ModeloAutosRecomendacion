"""Motor de recomendación de autos.

Reutiliza la lógica del notebook de películas (distancia euclidiana, filtrado por usuarios
y por ítems) y añade dos métodos más:

* contenido: compara las características de los autos (país, época, categoría, potencia...)
* svd: factorización de matriz (factores ocultos) con un modelo que sí se entrena

Estructuras de datos (igual que en el ejemplo):
    base_usuarios = {usuario: {auto_id: nota}}
    base_items    = {auto_id: {usuario: nota}}
"""
from collections import defaultdict
from math import sqrt

import numpy as np

MIN_COMUNES = 3  # autos en común mínimos para considerar que dos usuarios/autos son comparables
VECINOS = 8      # solo cuentan los K vecinos más parecidos que calificaron el auto (mejora sobre el ejemplo)


# ----------------------------------------------------------------------------------------
# 1) Similitud euclidiana (igual que el notebook, con dos mejoras documentadas)
# ----------------------------------------------------------------------------------------
def euclidiana(base, p1, p2, min_comunes=MIN_COMUNES):
    """Similitud en (0, 1]: 1 = idénticos, 0 = sin nada en común.

    Mejoras sobre el ejemplo: se divide la suma de cuadrados entre la cantidad de elementos
    en común (para no castigar a quien calificó más cosas) y se exige un mínimo de elementos
    en común (con 1 solo coincidencia el ejemplo daba similitudes engañosas).
    """
    comunes = [k for k in base[p1] if k in base[p2]]
    if len(comunes) < min_comunes:
        return 0.0
    suma = sum(pow(base[p1][k] - base[p2][k], 2) for k in comunes)
    return 1 / (1 + sqrt(suma / len(comunes)))


def get_similares(base, persona, n=None, min_comunes=MIN_COMUNES):
    """Lista [(similitud, otro)] ordenada de mayor a menor (igual que el notebook)."""
    puntajes = [(euclidiana(base, persona, otro, min_comunes), otro) for otro in base if otro != persona]
    puntajes.sort(reverse=True)
    return puntajes[:n] if n else puntajes


def invertir(base):
    """usuario->{item:nota}  <=>  item->{usuario:nota}"""
    res = defaultdict(dict)
    for a, notas in base.items():
        for b, nota in notas.items():
            res[b][a] = nota
    return dict(res)


def _similitud_con_notas(base_usuarios, notas, otro, min_comunes=MIN_COMUNES):
    """Similitud entre un usuario nuevo (solo sus notas) y un usuario de la base."""
    tmp = {"__nuevo__": notas, otro: base_usuarios[otro]}
    return euclidiana(tmp, "__nuevo__", otro, min_comunes)


# ----------------------------------------------------------------------------------------
# 2) Filtrado colaborativo por usuarios
# ----------------------------------------------------------------------------------------
def predecir_usuarios(base_usuarios, notas, auto_id, excluir=None, vecinos=None):
    """Nota estimada de `auto_id` para un usuario con `notas`, según usuarios parecidos."""
    sims = vecinos if vecinos is not None else {
        u: _similitud_con_notas(base_usuarios, notas, u) for u in base_usuarios if u != excluir
    }
    candidatos = sorted(
        ((sim, u) for u, sim in sims.items() if sim > 0 and auto_id in base_usuarios[u]), reverse=True
    )[:VECINOS]
    if not candidatos:
        return None, []
    total = sum(sim for sim, _ in candidatos)
    suma = sum(sim * base_usuarios[u][auto_id] for sim, u in candidatos)
    aportes = [(sim * base_usuarios[u][auto_id], sim, u) for sim, u in candidatos]
    return suma / total, aportes


def recomendar_usuarios(base_usuarios, notas, catalogo_ids):
    sims = {u: _similitud_con_notas(base_usuarios, notas, u) for u in base_usuarios}
    res = []
    for auto in catalogo_ids:
        if auto in notas:
            continue
        pred, aportes = predecir_usuarios(base_usuarios, notas, auto, vecinos=sims)
        if pred is not None:
            res.append({"id": auto, "puntaje": pred, "aportes": [(u, s) for _, s, u in aportes[:3]]})
    res.sort(key=lambda r: r["puntaje"], reverse=True)
    return res


# ----------------------------------------------------------------------------------------
# 3) Filtrado colaborativo por ítems
# ----------------------------------------------------------------------------------------
def calcular_items_similares(base_items):
    """item -> [(similitud, otro_item)] (igual que el notebook)."""
    return {item: get_similares(base_items, item) for item in base_items}


def predecir_items(items_similares, notas, auto_id):
    candidatos = [(sim, otro) for sim, otro in items_similares.get(auto_id, []) if sim > 0 and otro in notas][:VECINOS]
    if not candidatos:
        return None, []
    total = sum(sim for sim, _ in candidatos)
    suma = sum(sim * notas[otro] for sim, otro in candidatos)
    aportes = sorted(((sim * notas[otro], otro) for sim, otro in candidatos), reverse=True)
    return suma / total, aportes


def recomendar_items(items_similares, notas, catalogo_ids):
    res = []
    for auto in catalogo_ids:
        if auto in notas:
            continue
        pred, aportes = predecir_items(items_similares, notas, auto)
        if pred is not None:
            res.append({"id": auto, "puntaje": pred, "aportes": [o for _, o in aportes[:2]]})
    res.sort(key=lambda r: r["puntaje"], reverse=True)
    return res


# ----------------------------------------------------------------------------------------
# 4) Basado en contenido
# ----------------------------------------------------------------------------------------
class ModeloContenido:
    PESOS = {"categoria": 1.0, "pais": 1.0, "epoca": 1.0, "marca": 0.8, "anio": 1.2, "hp": 1.0}

    def __init__(self, autos):
        self.ids = [a["id"] for a in autos]
        self.idx = {a: i for i, a in enumerate(self.ids)}
        self.autos = {a["id"]: a for a in autos}
        cols = []
        for campo in ("categoria", "pais", "epoca", "marca"):
            valores = sorted({a[campo] for a in autos})
            m = np.array([[1.0 if a[campo] == v else 0.0 for v in valores] for a in autos])
            cols.append(m * self.PESOS[campo])
        anio = np.array([a["anio"] for a in autos], dtype=float)
        anio = (anio - anio.min()) / (anio.max() - anio.min())
        hp = np.log(np.array([a["hp"] for a in autos], dtype=float))
        hp = (hp - hp.min()) / (hp.max() - hp.min())
        cols.append(anio[:, None] * self.PESOS["anio"])
        cols.append(hp[:, None] * self.PESOS["hp"])
        x = np.hstack(cols)
        self.x = x / np.linalg.norm(x, axis=1, keepdims=True)

    def similares(self, auto_id, n=6):
        sims = self.x @ self.x[self.idx[auto_id]]
        orden = [i for i in np.argsort(-sims) if self.ids[i] != auto_id][:n]
        return [(float(sims[i]), self.ids[i]) for i in orden]

    def perfil(self, notas):
        media = np.mean(list(notas.values()))
        p = np.zeros(self.x.shape[1])
        for auto, nota in notas.items():
            if auto in self.idx:
                p += (nota - media) * self.x[self.idx[auto]]
        return p

    def recomendar(self, notas):
        p = self.perfil(notas)
        norma = np.linalg.norm(p)
        if norma == 0:
            return []
        scores = self.x @ (p / norma)
        res = []
        for i, auto in enumerate(self.ids):
            if auto in notas:
                continue
            res.append({"id": auto, "puntaje": float(scores[i]), "aportes": self._motivos(auto, notas)})
        res.sort(key=lambda r: r["puntaje"], reverse=True)
        return res

    def _motivos(self, auto_id, notas):
        """Características que el auto comparte con los favoritos del usuario."""
        favoritos = [self.autos[a] for a, n in notas.items() if n >= 4 and a in self.autos]
        if not favoritos:
            return []
        a = self.autos[auto_id]
        motivos = []
        for campo, etiqueta in (("pais", "país"), ("categoria", "categoría"), ("epoca", "época"), ("marca", "marca")):
            comparten = sum(1 for f in favoritos if f[campo] == a[campo])
            if comparten / len(favoritos) >= 0.3:
                motivos.append((comparten / len(favoritos), f"{etiqueta}: {a[campo]}"))
        motivos.sort(reverse=True)
        return [m for _, m in motivos[:3]]


# ----------------------------------------------------------------------------------------
# 5) SVD (factores ocultos) — el modelo "entrenado"
# ----------------------------------------------------------------------------------------
class ModeloSVD:
    """Factorización de matriz con SVD truncado e imputación iterativa (soft-impute).

    1. Se arma la matriz usuarios x autos con huecos donde nadie calificó.
    2. Se quitan los sesgos (promedio global, de usuario y de auto).
    3. Se rellenan los huecos con ceros y se repite: SVD de rango k -> reconstruir -> reemplazar
       solo los huecos por la reconstrucción, hasta que converge.
    4. Para un usuario nuevo se calcula su vector de gustos ("fold-in") con mínimos cuadrados
       regularizados, sin reentrenar todo el modelo.
    """

    def __init__(self, k=4, iteraciones=60, reg=1.0):
        self.k, self.iteraciones, self.reg = k, iteraciones, reg

    def fit(self, base_usuarios, autos_ids):
        self.items = list(autos_ids)
        self.idx = {a: i for i, a in enumerate(self.items)}
        usuarios = list(base_usuarios)
        r = np.full((len(usuarios), len(self.items)), np.nan)
        for u, user in enumerate(usuarios):
            for auto, nota in base_usuarios[user].items():
                if auto in self.idx:
                    r[u, self.idx[auto]] = nota
        obs = ~np.isnan(r)
        self.mu = np.nanmean(r)
        # sesgos con regularización simple (shrinkage) para ítems poco calificados
        self.bi = np.array([
            np.nansum(r[:, j] - self.mu) / (obs[:, j].sum() + 3) for j in range(r.shape[1])
        ])
        res = r - self.mu - self.bi[None, :]
        bu = np.array([np.nansum(res[u]) / (obs[u].sum() + 3) for u in range(r.shape[0])])
        res = res - bu[:, None]
        x = np.where(obs, res, 0.0)
        for _ in range(self.iteraciones):
            u_, s, vt = np.linalg.svd(x, full_matrices=False)
            rec = (u_[:, : self.k] * s[: self.k]) @ vt[: self.k]
            nuevo = np.where(obs, res, rec)
            if np.abs(nuevo - x).max() < 1e-4:
                x = nuevo
                break
            x = nuevo
        u_, s, vt = np.linalg.svd(x, full_matrices=False)
        self.s = s[: self.k]
        self.v = vt[: self.k].T  # items x k
        self.q = self.v  # vector latente de cada auto
        return self

    def _vector_usuario(self, notas):
        js = [self.idx[a] for a in notas if a in self.idx]
        if not js:
            return 0.0, np.zeros(self.k)
        y = np.array([notas[self.items[j]] for j in js]) - self.mu - self.bi[js]
        bu = y.sum() / (len(js) + 3)
        y = y - bu
        v = self.v[js]
        p = np.linalg.solve(v.T @ v + self.reg * np.eye(self.k), v.T @ y)
        return bu, p

    def predecir(self, notas, auto_id):
        bu, p = self._vector_usuario(notas)
        j = self.idx[auto_id]
        return float(np.clip(self.mu + self.bi[j] + bu + self.v[j] @ p, 1, 5))

    def recomendar(self, notas):
        bu, p = self._vector_usuario(notas)
        preds = np.clip(self.mu + self.bi + bu + self.v @ p, 1, 5)
        favoritos = [a for a, n in sorted(notas.items(), key=lambda kv: -kv[1]) if n >= 4 and a in self.idx][:5]
        res = []
        for j, auto in enumerate(self.items):
            if auto in notas:
                continue
            aportes = []
            if favoritos:
                qs = self.q[j]
                cercanos = []
                for f in favoritos:
                    qf = self.q[self.idx[f]]
                    den = np.linalg.norm(qs) * np.linalg.norm(qf)
                    cercanos.append((float(qs @ qf / den) if den else 0.0, f))
                cercanos.sort(reverse=True)
                aportes = [f for c, f in cercanos[:2] if c > 0]
            res.append({"id": auto, "puntaje": float(preds[j]), "aportes": aportes})
        res.sort(key=lambda r: r["puntaje"], reverse=True)
        return res


# ----------------------------------------------------------------------------------------
# 6) Motor que une todo
# ----------------------------------------------------------------------------------------
METODOS = ("usuarios", "items", "contenido", "svd")


class Motor:
    def __init__(self, autos, base_usuarios, k_svd=4):
        self.autos = {a["id"]: a for a in autos}
        self.ids = [a["id"] for a in autos]
        self.base_usuarios = base_usuarios
        self.base_items = invertir(base_usuarios)
        self.items_similares = calcular_items_similares(self.base_items)
        self.contenido = ModeloContenido(autos)
        self.svd = ModeloSVD(k=k_svd).fit(base_usuarios, self.ids)

    def listas(self, notas):
        """Devuelve las listas de cada método (sin recortar) para un usuario con `notas`."""
        return {
            "usuarios": recomendar_usuarios(self.base_usuarios, notas, self.ids),
            "items": recomendar_items(self.items_similares, notas, self.ids),
            "contenido": self.contenido.recomendar(notas),
            "svd": self.svd.recomendar(notas),
        }

    @staticmethod
    def combinar(listas, pesos=None):
        """Mezcla las listas: cada método se normaliza a 0-1 (min-max) y se promedian."""
        pesos = pesos or {m: 1.0 for m in METODOS}
        acum, presencia = defaultdict(float), defaultdict(list)
        total_peso = sum(pesos.values())
        for metodo, lista in listas.items():
            if not lista:
                continue
            puntajes = [r["puntaje"] for r in lista]
            lo, hi = min(puntajes), max(puntajes)
            for pos, r in enumerate(lista):
                norm = (r["puntaje"] - lo) / (hi - lo) if hi > lo else 0.5
                acum[r["id"]] += pesos.get(metodo, 1.0) * norm
                if pos < 10:
                    presencia[r["id"]].append(metodo)
        res = [{"id": a, "puntaje": s / total_peso, "metodos": presencia[a]} for a, s in acum.items()]
        res.sort(key=lambda r: r["puntaje"], reverse=True)
        return res
