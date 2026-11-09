import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { obtenerAutos, obtenerUsuarios, obtenerUsuario, obtenerEvaluacion, recomendar } from './api.js'
import Calificar from './components/Calificar.jsx'
import BarraProgreso, { MINIMO } from './components/BarraProgreso.jsx'
import Resultados from './components/Resultados.jsx'
import Modelo from './components/Modelo.jsx'

const CLAVE = 'garaje.notas.v1'

function leerGuardado() {
  try {
    const g = JSON.parse(localStorage.getItem(CLAVE) || '{}')
    return g && typeof g.notas === 'object' ? g : {}
  } catch {
    return {}
  }
}

export default function App() {
  const guardado = useRef(leerGuardado()).current
  const [autos, setAutos] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [evaluacion, setEvaluacion] = useState(null)
  const [errorCarga, setErrorCarga] = useState('')
  const [notas, setNotas] = useState(guardado.notas || {})
  const [demoId, setDemoId] = useState(guardado.demoId || '')
  const [cargandoDemo, setCargandoDemo] = useState(false)
  const [vista, setVista] = useState('calificar')
  const [datos, setDatos] = useState(null)
  const [claveDatos, setClaveDatos] = useState('')
  const [cargando, setCargando] = useState(false)
  const [errorRec, setErrorRec] = useState('')

  const total = Object.keys(notas).length

  const cargarTodo = useCallback(() => {
    setErrorCarga('')
    Promise.all([obtenerAutos(), obtenerUsuarios()])
      .then(([a, u]) => { setAutos(a); setUsuarios(u) })
      .catch((e) => setErrorCarga(e.message))
    obtenerEvaluacion().then(setEvaluacion).catch(() => {})
  }, [])
  useEffect(cargarTodo, [cargarTodo])

  useEffect(() => {
    try { localStorage.setItem(CLAVE, JSON.stringify({ notas, demoId })) } catch { /* sin almacenamiento */ }
  }, [notas, demoId])

  // Solo se conservan notas de autos que existen en el catálogo actual.
  useEffect(() => {
    if (!autos.length) return
    const ids = new Set(autos.map((a) => a.id))
    setNotas((n) => {
      const limpio = Object.fromEntries(Object.entries(n).filter(([k]) => ids.has(k)))
      return Object.keys(limpio).length === Object.keys(n).length ? n : limpio
    })
  }, [autos])

  const calificar = (id, n) => {
    setDemoId('')
    setNotas((prev) => {
      const sig = { ...prev }
      if (n) sig[id] = n
      else delete sig[id]
      return sig
    })
  }

  const elegirDemo = async (id) => {
    if (!id) { setDemoId(''); return }
    setCargandoDemo(true)
    try {
      const u = await obtenerUsuario(id)
      setNotas(u.calificaciones)
      setDemoId(id)
    } catch (e) {
      setErrorCarga(e.message)
    } finally {
      setCargandoDemo(false)
    }
  }

  const clave = useMemo(() => JSON.stringify([notas, demoId]), [notas, demoId])

  const pedir = useCallback(async () => {
    setCargando(true)
    setErrorRec('')
    try {
      const cuerpo = demoId ? { usuario_id: demoId, n: 6 } : { calificaciones: notas, n: 6 }
      const r = await recomendar(cuerpo)
      setDatos(r)
      setClaveDatos(clave)
    } catch (e) {
      setErrorRec(e.message)
    } finally {
      setCargando(false)
    }
  }, [notas, demoId, clave])

  // Al entrar a resultados, recalcula solo si las notas cambiaron desde el último cálculo.
  useEffect(() => {
    if (vista === 'resultados' && total >= MINIMO && clave !== claveDatos && !cargando && !errorRec) pedir()
  }, [vista, total, clave, claveDatos, cargando, errorRec, pedir])

  const ir = (v) => {
    setErrorRec('')
    setVista(v)
    window.scrollTo({ top: 0 })
  }

  const borrar = () => { setNotas({}); setDemoId(''); setDatos(null); setClaveDatos('') }

  return (
    <>
      <header className="top">
        <div className="wrap">
          <div className="brand">
            <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
              <path d="M3.5 19a9.5 9.5 0 1 1 19 0" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
              <path d="M13 19l5-7" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
            </svg>
            <span>Garaje</span>
          </div>
          <nav className="nav" aria-label="Secciones">
            <button aria-current={vista === 'calificar' ? 'page' : undefined} onClick={() => ir('calificar')}>
              Calificar{total > 0 && <span className="contador num">{total}</span>}
            </button>
            <button aria-current={vista === 'resultados' ? 'page' : undefined} onClick={() => ir('resultados')}>
              Recomendaciones
            </button>
            <button aria-current={vista === 'modelo' ? 'page' : undefined} onClick={() => ir('modelo')}>
              Cómo funciona
            </button>
          </nav>
        </div>
      </header>

      <main className="wrap">
        {errorCarga && (
          <div className="error" role="alert">
            <span>{errorCarga}</span>
            <button className="btn borde" onClick={cargarTodo}>Reintentar</button>
          </div>
        )}

        {!autos.length && !errorCarga && (
          <div className="rejilla" style={{ paddingTop: 48 }} aria-busy="true">
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} className="esqueleto" style={{ aspectRatio: '16/10' }} />
            ))}
          </div>
        )}

        {autos.length > 0 && vista === 'calificar' && (
          <>
            <Calificar
              autos={autos}
              notas={notas}
              onNota={calificar}
              usuarios={usuarios}
              demoId={demoId}
              onDemo={elegirDemo}
              cargandoDemo={cargandoDemo}
            />
            <BarraProgreso total={total} cargando={cargando} onBorrar={borrar} onVer={() => ir('resultados')} />
          </>
        )}

        {autos.length > 0 && vista === 'resultados' && (
          <Resultados
            datos={datos}
            cargando={cargando}
            error={errorRec}
            total={total}
            onVolver={() => ir('calificar')}
            onReintentar={pedir}
          />
        )}

        {autos.length > 0 && vista === 'modelo' && <Modelo evaluacion={evaluacion} autos={autos} error="" />}
      </main>
    </>
  )
}
