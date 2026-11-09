import { METODOS } from './Resultados.jsx'

const FILAS = [
  ['base', 'Promedio del auto (línea base)'],
  ['popularidad', 'Los más populares (línea base)'],
  ['usuarios', 'Por usuarios'],
  ['items', 'Por ítems'],
  ['contenido', 'Por contenido'],
  ['svd', 'SVD (factores ocultos)'],
  ['combinado', 'Combinado'],
]

const pct = (x) => `${Math.round(x * 100)}%`

function Barra({ valor, max, mejor }) {
  return (
    <div className="barra-m">
      <div className="pista"><i className={mejor ? 'mejor' : ''} style={{ width: `${(valor / max) * 100}%` }} /></div>
    </div>
  )
}

function CurvaSVD({ curva, mejorK }) {
  const ks = Object.keys(curva).map(Number)
  const ys = ks.map((k) => curva[k])
  const [w, h, pad] = [520, 190, 34]
  const ymin = Math.min(...ys) - 0.01
  const ymax = Math.max(...ys) + 0.01
  const x = (k) => pad + ((k - ks[0]) / (ks.at(-1) - ks[0])) * (w - pad * 2)
  const y = (v) => h - pad - ((v - ymin) / (ymax - ymin)) * (h - pad * 2)
  const d = ks.map((k, i) => `${i ? 'L' : 'M'}${x(k).toFixed(1)},${y(curva[k]).toFixed(1)}`).join(' ')
  return (
    <svg className="curva" viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`Error del SVD según la cantidad de factores; el mejor es ${mejorK}`}>
      <line x1={pad} x2={w - pad} y1={h - pad} y2={h - pad} />
      <path className="l" d={d} />
      {ks.map((k) => (
        <g key={k}>
          <circle className={k === mejorK ? 'm' : ''} cx={x(k)} cy={y(curva[k])} r={k === mejorK ? 5 : 3.5} />
          <text x={x(k)} y={h - pad + 18} textAnchor="middle">{k}</text>
        </g>
      ))}
      <text x={x(mejorK)} y={y(curva[mejorK]) - 12} textAnchor="middle" style={{ fill: 'var(--ink)', fontWeight: 600 }}>
        {curva[mejorK].toFixed(3)}
      </text>
      <text x={w / 2} y={h - 2} textAnchor="middle">factores ocultos (k)</text>
    </svg>
  )
}

export default function Modelo({ evaluacion, error, autos }) {
  return (
    <section className="vista">
      <div className="intro">
        <h1>Cómo funciona.</h1>
        <p>
          Cuatro formas distintas de adivinar qué auto te gustará, y una medición honesta de cuál acierta más.
        </p>
      </div>

      <div className="seccion">
        <h2>Los cuatro métodos</h2>
        <div className="metodos">
          {METODOS.filter((m) => m.clave !== 'combinado').map((m) => (
            <div key={m.clave}>
              <h3>{m.etiqueta}</h3>
              <p>{m.texto}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="seccion">
        <h2>Cuál acierta más</h2>
        {error && <div className="error" role="alert">{error}</div>}
        {!evaluacion && !error && <div className="esqueleto" style={{ height: 260 }} />}
        {evaluacion && (
          <>
            <p>
              Para medirlo, ocultamos ~25% de las notas de cada usuario, dejamos que cada método las adivine y
              repetimos con {evaluacion.descripcion.match(/\d+ particiones/)?.[0] || '5 particiones'}. Con{' '}
              {evaluacion.n_usuarios} usuarios, {evaluacion.n_autos} autos y {evaluacion.n_calificaciones} calificaciones.
            </p>
            <div className="tabla-wrap" style={{ overflowX: 'auto' }}>
              <table className="tabla">
                <thead>
                  <tr>
                    <th scope="col">Método</th>
                    <th scope="col" colSpan={2}>Error al predecir la nota (RMSE, menor es mejor)</th>
                    <th scope="col" colSpan={2}>Acierto en el top 10 (mayor es mejor)</th>
                  </tr>
                </thead>
                <tbody>
                  {(() => {
                    const rmses = FILAS.map(([k]) => evaluacion.metodos[k]?.rmse).filter(Boolean)
                    const mejorRmse = Math.min(...rmses)
                    const aciertos = FILAS.map(([k]) => evaluacion.ranking[k]?.acierto_10).filter((v) => v != null)
                    const mejorAcierto = Math.max(...aciertos)
                    return FILAS.map(([k, nombre]) => {
                      const rmse = evaluacion.metodos[k]?.rmse
                      const ac = evaluacion.ranking[k]?.acierto_10
                      return (
                        <tr key={k}>
                          <td>{nombre}</td>
                          <td className="num" style={{ width: 60 }}>{rmse ? rmse.toFixed(3) : '—'}</td>
                          <td>{rmse ? <Barra valor={rmse} max={Math.max(...rmses)} mejor={rmse === mejorRmse} /> : null}</td>
                          <td className="num" style={{ width: 60 }}>{ac != null ? pct(ac) : '—'}</td>
                          <td>{ac != null ? <Barra valor={ac} max={1} mejor={ac === mejorAcierto} /> : null}</td>
                        </tr>
                      )
                    })
                  })()}
                </tbody>
              </table>
            </div>
            <p className="nota-pie">
              El acierto en el top 10 es el porcentaje de usuarios a los que el método les puso, entre sus 10
              primeras sugerencias, al menos un auto que les gustó (4 o 5 estrellas) y que estaba oculto. El método
              por contenido sale muy bien porque los usuarios son <b>simulados</b> con gustos definidos por las mismas
              características (país, época, categoría) que ese método observa; con personas reales las diferencias
              entre métodos cambiarían.
            </p>
          </>
        )}
      </div>

      {evaluacion && (
        <div className="seccion">
          <h2>El modelo entrenado: SVD</h2>
          <p>
            El SVD resume las notas en unos pocos factores ocultos. Con muy pocos pierde detalle y con demasiados
            memoriza el ruido; el menor error en pruebas se logra con <b className="num">{evaluacion.k_svd}</b> factores,
            que es el que usa esta página. Entrenarlo toma menos de un segundo.
          </p>
          <CurvaSVD curva={evaluacion.curva_svd} mejorK={evaluacion.k_svd} />
        </div>
      )}

      <div className="seccion" style={{ paddingBottom: 80 }}>
        <h2>Datos y créditos</h2>
        <p>
          El catálogo tiene {autos.length} autos reales, modernos y clásicos. Los usuarios y sus calificaciones son
          sintéticos, generados para este proyecto. Las fotos vienen de Wikimedia Commons con licencia libre.
        </p>
        <details className="creditos">
          <summary>Ver créditos de las fotos</summary>
          <ul>
            {autos.map((a) => (
              <li key={a.id}>
                {a.nombre}:{' '}
                <a href={a.credito?.fuente} target="_blank" rel="noreferrer">
                  {a.credito?.autor || 'Autor desconocido'}
                </a>
                {a.credito?.licencia ? `, ${a.credito.licencia}` : ''}
              </li>
            ))}
          </ul>
        </details>
      </div>
    </section>
  )
}
