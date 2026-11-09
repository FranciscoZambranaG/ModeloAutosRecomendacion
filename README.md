# Garaje · Recomendador de autos

Sistema de recomendación de autos deportivos y clásicos con web en React y backend en Python.
Es la versión para autos del notebook `SistemaRecomendacion.ipynb` (películas / MovieLens).

## Cómo ejecutarlo

Necesitas dos terminales.

```bash
# 1) Backend (FastAPI, puerto 8000)
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # solo la primera vez
.venv/bin/uvicorn main:app --port 8000

# 2) Frontend (React + Vite, puerto 5173)
cd frontend
npm install                                                          # solo la primera vez
npm run dev
```

Abre http://localhost:5173. La documentación interactiva de la API está en http://localhost:8000/docs.

## Cómo funciona

El usuario califica al menos 5 autos (1–5 estrellas). El backend lo trata como un usuario nuevo
y calcula cuatro listas más una combinada (`backend/recomendador.py`):

| Método | Idea |
|---|---|
| Por usuarios | Distancia euclidiana con los 120 usuarios; promedio ponderado de sus notas (igual que el notebook). |
| Por ítems | Autos que reciben notas parecidas de las mismas personas; se ponderan por tus notas. |
| Por contenido | Perfil con tus favoritos (país, época, categoría, marca, año, potencia) y similitud coseno. |
| SVD | Modelo entrenado de factores ocultos (soft-impute + fold-in para usuarios nuevos). |
| Combinado | Promedio de los cuatro puntajes normalizados. |

Mejoras sobre el notebook: la distancia se divide entre la cantidad de autos en común, se exige un mínimo de
3 en común y solo cuentan los 8 vecinos más parecidos.

## Datos

* `backend/data/autos.json`: 69 autos reales (modernos y clásicos) con fotos de Wikimedia Commons y su crédito.
* `backend/data/usuarios.json`: 120 usuarios **sintéticos** con perfiles de gusto (italianos, muscle cars, JDM...).
* `backend/data/evaluacion.json`: resultados de la validación (los muestra la pestaña "Cómo funciona").

Regenerar: `python scripts/generar_usuarios.py` y luego `python evaluar.py`
(para el catálogo: `scripts/construir_catalogo.py`, que descarga las fotos).

## Resultados (validación con notas ocultas)

| Método | RMSE ↓ | Acierto@10 ↑ |
|---|---|---|
| Promedio del auto | 0.989 | – |
| Más populares | – | 44% |
| Por usuarios | 0.932 | 56% |
| Por ítems | 0.884 | 57% |
| SVD (k=3) | 0.885 | 58% |
| Por contenido | – | 69% |
| Combinado | – | 68% |

Como los usuarios son simulados a partir de las mismas características que mira el método por contenido,
este sale favorecido; con personas reales las diferencias cambiarían.

## Pruebas

```bash
cd backend && .venv/bin/python -m pytest -q     # 24 pruebas del motor y la API
```
