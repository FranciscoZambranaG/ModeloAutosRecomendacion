import { useState } from 'react'
import { Star } from 'lucide-react'

// Calificación de 1 a 5. Pulsar la misma nota otra vez la quita.
export default function Estrellas({ valor = 0, onChange, nombre, chicas = false }) {
  const [hover, setHover] = useState(0)
  const activo = hover || valor
  if (!onChange) {
    return (
      <span className={`estrellas ${chicas ? 'chicas' : ''}`} role="img" aria-label={`${valor} de 5 estrellas`}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} tabIndex={-1} className={n <= Math.round(valor) ? 'on' : ''} aria-hidden="true">
            <Star />
          </button>
        ))}
      </span>
    )
  }
  return (
    <span className="estrellas" role="radiogroup" aria-label={`Tu nota para ${nombre}`} onMouseLeave={() => setHover(0)}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          role="radio"
          aria-checked={valor === n}
          aria-label={`${n} ${n === 1 ? 'estrella' : 'estrellas'}`}
          className={n <= activo ? 'on' : ''}
          onMouseEnter={() => setHover(n)}
          onClick={() => onChange(valor === n ? 0 : n)}
        >
          <Star />
        </button>
      ))}
    </span>
  )
}
