import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import TarjetaAuto from './TarjetaAuto.jsx'

const EPOCAS = [
  ['todas', 'Todos'],
  ['Moderno', 'Modernos'],
  ['Clásico', 'Clásicos'],
]

export default function Calificar({ autos, notas, onNota, usuarios, demoId, onDemo, cargandoDemo }) {
  const [epoca, setEpoca] = useState('todas')
  const [categoria, setCategoria] = useState('todas')
  const [texto, setTexto] = useState('')

  const categorias = useMemo(() => [...new Set(autos.map((a) => a.categoria))].sort(), [autos])
  const visibles = useMemo(() => {
    const q = texto.trim().toLowerCase()
    return autos.filter(
      (a) =>
        (epoca === 'todas' || a.epoca === epoca) &&
        (categoria === 'todas' || a.categoria === categoria) &&
        (!q || `${a.nombre} ${a.pais} ${a.categoria}`.toLowerCase().includes(q)),
    )
  }, [autos, epoca, categoria, texto])

  return (
    <section className="vista">
      <div className="intro">
        <h1>Dinos qué autos te gustan.</h1>
        <p>
          Califica al menos cinco con estrellas. Compararemos tu gusto con el de {usuarios.length} aficionados y con
          las características de cada auto para sugerirte los que te faltan.
        </p>
      </div>

      <div className="controles" role="group" aria-label="Filtros del catálogo">
        <div className="segmentos">
          {EPOCAS.map(([valor, etiqueta]) => (
            <button key={valor} aria-pressed={epoca === valor} onClick={() => setEpoca(valor)}>
              {etiqueta}
            </button>
          ))}
        </div>
        <label className="campo">
          <select value={categoria} onChange={(e) => setCategoria(e.target.value)} aria-label="Categoría">
            <option value="todas">Todas las categorías</option>
            {categorias.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className="campo">
          <Search size={16} aria-hidden="true" />
          <input
            type="search"
            placeholder="Buscar marca o país"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            aria-label="Buscar autos"
          />
        </label>
        <span className="espacio" />
        <label className="demo">
          <span>O prueba con un perfil de ejemplo:</span>
          <span className="campo">
            <select
              value={demoId || ''}
              disabled={cargandoDemo}
              onChange={(e) => onDemo(e.target.value)}
              aria-label="Perfil de ejemplo"
            >
              <option value="">Ninguno</option>
              {usuarios.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nombre} · {u.perfil}
                </option>
              ))}
            </select>
          </span>
        </label>
      </div>

      {visibles.length === 0 ? (
        <div className="estado">
          <h2>Ningún auto coincide</h2>
          <p>Prueba con otra categoría o borra la búsqueda.</p>
          <button className="btn borde" onClick={() => { setEpoca('todas'); setCategoria('todas'); setTexto('') }}>
            Quitar filtros
          </button>
        </div>
      ) : (
        <div className="rejilla">
          {visibles.map((a, i) => (
            <TarjetaAuto key={a.id} auto={a} nota={notas[a.id]} onNota={onNota} indice={i} />
          ))}
        </div>
      )}
    </section>
  )
}
