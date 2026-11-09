import { useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import Estrellas from './Estrellas.jsx'

export const METODOS = [
  {
    clave: 'combinado',
    etiqueta: 'Combinado',
    texto: 'Mezcla los cuatro métodos: cada uno puntúa todos los autos, se normalizan los puntajes y se promedian. Es la lista más equilibrada.',
  },
  {
    clave: 'usuarios',
    etiqueta: 'Por usuarios',
    texto: 'Busca a los aficionados cuyas notas se parecen más a las tuyas (distancia euclidiana) y promedia lo que opinaron de los autos que aún no calificas.',
  },
  {
    clave: 'items',
    etiqueta: 'Por ítems',
    texto: 'Mira qué autos recibieron notas parecidas de las mismas personas que los que tú calificaste, y te propone los más cercanos a tus favoritos.',
  },
  {
    clave: 'contenido',
    etiqueta: 'Por contenido',
    texto: 'Ignora a los demás usuarios: arma tu perfil con las características de los autos que te gustaron (país, época, categoría, marca, año y potencia) y busca autos parecidos.',
  },
  {
    clave: 'svd',
    etiqueta: 'Factores ocultos (SVD)',
    texto: 'Un modelo entrenado con todas las calificaciones: descubre factores ocultos de gusto, ubica tu perfil entre ellos y predice qué nota le pondrías a cada auto.',
  },
]

function Foto({ auto }) {
  const [ok, setOk] = useState(false)
  return (
    <div className="foto">
      <img src={auto.imagen} alt={auto.nombre} className={ok ? 'cargada' : ''} onLoad={() => setOk(true)} />
      <span className="etiqueta">{auto.categoria}</span>
    </div>
  )
}

function Puntaje({ rec }) {
  return (
    <div className="ajuste">
      <div className="medidor" role="img" aria-label={`${rec.coincidencia}% de coincidencia`}>
        <i style={{ width: `${rec.coincidencia}%` }} />
      </div>
      <strong className="num">{rec.coincidencia}% coincidencia</strong>
      {rec.estrellas != null && (
        <span className="ajuste" style={{ gap: 6 }}>
          <Estrellas valor={rec.estrellas} chicas />
          <span className="meta num">{rec.estrellas.toFixed(1)} estimado</span>
        </span>
      )}
    </div>
  )
}

export default function Resultados({ datos, cargando, error, onVolver, onReintentar, total }) {
  const [metodo, setMetodo] = useState('combinado')
  const actual = METODOS.find((m) => m.clave === metodo)

  if (total < 5) {
    return (
      <section className="vista estado">
        <h2>Aún no hay recomendaciones</h2>
        <p>Califica al menos cinco autos para que podamos conocer tu gusto.</p>
        <button className="btn primario" onClick={onVolver}>
          <ArrowLeft size={18} aria-hidden="true" /> Ir a calificar
        </button>
      </section>
    )
  }

  const lista = datos?.[metodo] || []
  const [primero, ...resto] = lista

  return (
    <section className="vista">
      <div className="res-cab">
        <h1>Tu garaje ideal</h1>
        {datos && (
          <p>
            Calificaste <b className="num">{datos.resumen.calificados}</b> autos con un promedio de{' '}
            <b className="num">{datos.resumen.promedio.toFixed(1)}</b>.
            {datos.resumen.favoritos.length > 0 && <> Tus favoritos: <b>{datos.resumen.favoritos.join(', ')}</b>.</>}
            {datos.resumen.gustos.length > 0 && <> Lo que más se repite en ellos: <b>{datos.resumen.gustos.join(' · ')}</b>.</>}
          </p>
        )}
        <div>
          <button className="btn borde" onClick={onVolver}>
            <ArrowLeft size={18} aria-hidden="true" /> Ajustar calificaciones
          </button>
        </div>
      </div>

      <div className="pestanas" role="tablist" aria-label="Método de recomendación">
        {METODOS.map((m) => (
          <button key={m.clave} role="tab" aria-selected={metodo === m.clave} onClick={() => setMetodo(m.clave)}>
            {m.etiqueta}
          </button>
        ))}
      </div>
      <p className="explica" role="tabpanel">
        <b>{actual.etiqueta}.</b> {actual.texto}
      </p>

      {error && (
        <div className="error" role="alert">
          <span>{error}</span>
          <button className="btn borde" onClick={onReintentar}>Reintentar</button>
        </div>
      )}

      {cargando && !datos && (
        <div className="podio" aria-busy="true">
          <div className="esqueleto" style={{ aspectRatio: '16/10' }} />
          <div className="esqueleto" style={{ height: 120 }} />
        </div>
      )}

      {primero && (
        <>
          <article className="podio" key={`${metodo}-${primero.id}`}>
            <Foto auto={primero.auto} />
            <div className="rec-info">
              <span className="rec-num">Tu mejor opción</span>
              <h2>{primero.auto.nombre}</h2>
              <p className="meta num">
                {primero.auto.anio} · {primero.auto.pais} · {primero.auto.hp} hp · {primero.auto.categoria}
              </p>
              <Puntaje rec={primero} />
              <p className="porque">{primero.porque}</p>
            </div>
          </article>
          <div className="resto">
            {resto.map((r, i) => (
              <article className="auto" key={`${metodo}-${r.id}`} style={{ '--i': i }}>
                <Foto auto={r.auto} />
                <div className="auto-info">
                  <h3>
                    <span className="rec-num num">{i + 2}</span> {r.auto.nombre}
                  </h3>
                  <p className="meta num">
                    {r.auto.anio} · {r.auto.pais} · {r.auto.hp} hp
                  </p>
                  <Puntaje rec={r} />
                  <p className="porque">{r.porque}</p>
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
