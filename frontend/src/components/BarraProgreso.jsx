import { ArrowRight } from 'lucide-react'

export const MINIMO = 5

export default function BarraProgreso({ total, onVer, onBorrar, cargando }) {
  const listo = total >= MINIMO
  return (
    <div className="barra" role="region" aria-label="Progreso de tus calificaciones">
      <div className="barra-in">
        <div className="progreso">
          <strong className="num">
            {listo ? `${total} autos calificados` : `${total} de ${MINIMO} autos`}
            <span className="sub">
              {' '}
              {listo ? '· ya puedes ver tus recomendaciones' : `· faltan ${MINIMO - total}`}
            </span>
          </strong>
          <div className="pips" aria-hidden="true">
            {Array.from({ length: MINIMO }, (_, i) => (
              <i key={i} className={i < total ? 'lleno' : ''} />
            ))}
          </div>
        </div>
        {total > 0 && (
          <button className="btn fantasma" onClick={onBorrar}>
            Borrar todo
          </button>
        )}
        <button className="btn primario" disabled={!listo || cargando} onClick={onVer}>
          {cargando ? 'Calculando…' : 'Ver recomendaciones'}
          {!cargando && <ArrowRight size={18} aria-hidden="true" />}
        </button>
      </div>
    </div>
  )
}
