"""Genera usuarios sintéticos con gustos coherentes y sus calificaciones (data/usuarios.json).

Cada usuario mezcla un perfil principal (70%) y uno secundario (30%), más un sesgo personal y
ruido. Así hay patrones reales que los métodos de similitud pueden descubrir, sin ser triviales.

Uso:  python scripts/generar_usuarios.py
"""
import json
import random
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
AUTOS = json.loads((RAIZ / "data" / "autos.json").read_text(encoding="utf-8"))
SALIDA = RAIZ / "data" / "usuarios.json"

ELECTRICOS = {"tesla-model-s-plaid", "porsche-taycan", "ferrari-sf90", "mclaren-p1", "honda-nsx-2016"}


def afin_italianos(a):
    return (2.0 if a["pais"] == "Italia" else 0) + (0.8 if "deportivo" in a["categoria"].lower() else 0) \
        + (0.8 if a["marca"] in ("Ferrari", "Lamborghini", "Maserati", "Pagani") else 0) - (1.0 if a["pais"] == "Estados Unidos" else 0)


def afin_americanos(a):
    return (2.0 if a["pais"] == "Estados Unidos" else 0) + (1.2 if a["categoria"] == "Muscle car" else 0) \
        + (0.5 if a["epoca"] == "Clásico" else 0) - (0.8 if a["hp"] < 100 else 0) - (0.8 if a["pais"] == "Japón" else 0)


def afin_jdm(a):
    return (2.4 if a["pais"] == "Japón" else 0) + (0.6 if a["marca"] in ("Nissan", "Toyota", "Mazda", "Honda", "Subaru", "Mitsubishi") else 0) \
        - (0.8 if a["pais"] == "Estados Unidos" else 0)


def afin_aleman(a):
    return (2.2 if a["pais"] == "Alemania" else 0) + (0.8 if a["marca"] in ("Porsche", "BMW", "Audi", "Mercedes-AMG", "Mercedes-Benz") else 0) \
        - (0.8 if a["pais"] == "Italia" else 0)


def afin_britanico(a):
    return (2.2 if a["pais"] == "Reino Unido" else 0) + (0.9 if a["marca"] in ("Aston Martin", "Jaguar", "Lotus", "McLaren") else 0) \
        - (0.5 if a["hp"] < 80 else 0)


def afin_hiper(a):
    return (2.2 * (np.log(a["hp"]) - np.log(100)) / (np.log(1600) - np.log(100))) + (1.0 if a["categoria"] == "Superdeportivo" else 0) \
        + (0.5 if a["epoca"] == "Moderno" else 0) - (1.5 if a["hp"] < 150 else 0)


def afin_nostalgico(a):
    return (1.5 if a["epoca"] == "Clásico" else -1.0) + (1.2 if a["categoria"] == "Clásico" else 0) \
        + (1.0 if a["anio"] < 1975 else 0) - (0.8 if a["hp"] > 600 else 0)


def afin_electrico(a):
    return (2.8 if a["id"] in ELECTRICOS else 0) + (0.8 if a["epoca"] == "Moderno" else -0.8) - (0.6 if a["categoria"] == "Muscle car" else 0)


PERFILES = {
    "Fan de los superdeportivos italianos": afin_italianos,
    "Amante de los muscle cars americanos": afin_americanos,
    "Entusiasta del JDM japonés": afin_jdm,
    "Purista del motor alemán": afin_aleman,
    "Gran turismo a la británica": afin_britanico,
    "Cazador de hiperdeportivos": afin_hiper,
    "Nostálgico de los clásicos": afin_nostalgico,
    "Curioso de la era eléctrica": afin_electrico,
}

NOMBRES = [
    "Valeria", "Martín", "Camila", "Sebastián", "Lucía", "Mateo", "Sofía", "Diego", "Paula", "Andrés",
    "Daniela", "Javier", "Fernanda", "Nicolás", "Carolina", "Tomás", "Isabela", "Gabriel", "Mariana", "Felipe",
    "Renata", "Esteban", "Natalia", "Ignacio", "Julieta", "Rodrigo", "Antonia", "Emilio", "Bianca", "Santiago",
    "Elena", "Bruno", "Alejandra", "Joaquín", "Victoria", "Hugo", "Pilar", "Cristian", "Abril", "Leandro",
]


def main(semilla=2024, n_usuarios=120):
    rng = random.Random(semilla)
    nrng = np.random.default_rng(semilla)
    nombres_perfil = list(PERFILES)
    usuarios = []
    for i in range(n_usuarios):
        nombre = NOMBRES[i % len(NOMBRES)]
        principal = nombres_perfil[i % len(nombres_perfil)]
        secundario = rng.choice([p for p in nombres_perfil if p != principal])
        sesgo = nrng.normal(0, 0.35)
        favorita = rng.choice(sorted({a["marca"] for a in AUTOS}))
        afinidades = {}
        for a in AUTOS:
            e = 0.7 * PERFILES[principal](a) + 0.3 * PERFILES[secundario](a)
            e += 0.9 if a["marca"] == favorita else 0
            afinidades[a["id"]] = 2.6 + 0.65 * e + sesgo + nrng.normal(0, 0.55)
        # cada persona califica entre 14 y 26 autos; tiende a calificar lo que conoce/le interesa
        n = rng.randint(14, 26)
        ids = [a["id"] for a in AUTOS]
        pesos = np.exp(0.5 * np.array([afinidades[x] for x in ids]))
        elegidos = nrng.choice(ids, size=n, replace=False, p=pesos / pesos.sum())
        califs = {str(a): int(np.clip(round(afinidades[a]), 1, 5)) for a in elegidos}
        usuarios.append({
            "id": f"u{i + 1:03d}",
            "nombre": f"{nombre} {chr(65 + (i * 7 + i // len(NOMBRES) * 5) % 26)}.",
            "perfil": principal,
            "perfil_secundario": secundario,
            "calificaciones": califs,
        })
    SALIDA.write_text(json.dumps(usuarios, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(u["calificaciones"]) for u in usuarios)
    dist = np.bincount([v for u in usuarios for v in u["calificaciones"].values()], minlength=6)[1:]
    print(f"{len(usuarios)} usuarios, {total} calificaciones sobre {len(AUTOS)} autos")
    print("distribución 1-5 estrellas:", dist.tolist())
    print(f"densidad de la matriz: {total / (len(usuarios) * len(AUTOS)):.1%}")


if __name__ == "__main__":
    main()
