import { useState } from 'react'
import Estrellas from './Estrellas.jsx'

const TEXTO_NOTA = { 1: 'No me gusta', 2: 'Poco', 3: 'Normal', 4: 'Me gusta', 5: 'Me encanta' }

export default function TarjetaAuto({ auto, nota, onNota, indice }) {
  const [cargada, setCargada] = useState(false)
  return (
    <article className={`auto ${nota ? 'calificado' : ''}`} style={{ '--i': Math.min(indice, 14) }}>
      <div className="foto">
        <img
          src={auto.imagen}
          alt={auto.nombre}
          loading="lazy"
          className={cargada ? 'cargada' : ''}
          onLoad={() => setCargada(true)}
        />
        <span className="etiqueta">{auto.categoria}</span>
      </div>
      <div className="auto-info">
        <h3>{auto.nombre}</h3>
        <p className="meta num">
          {auto.anio} · {auto.pais} · {auto.hp} hp
        </p>
        <p className="desc">{auto.descripcion}</p>
        <div className="nota">
          <Estrellas valor={nota || 0} onChange={(n) => onNota(auto.id, n)} nombre={auto.nombre} />
          <span className="nota-valor" aria-live="polite">{nota ? TEXTO_NOTA[nota] : 'Sin calificar'}</span>
        </div>
      </div>
    </article>
  )
}
