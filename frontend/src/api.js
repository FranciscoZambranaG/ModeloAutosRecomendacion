// Cliente mínimo para el backend FastAPI (el proxy de Vite reenvía /api al puerto 8000).
async function pedir(url, opciones) {
  let r
  try {
    r = await fetch(url, opciones)
  } catch {
    throw new Error('No se pudo conectar con el servidor. ¿Está encendido el backend (puerto 8000)?')
  }
  if (!r.ok) {
    let msg = 'Algo salió mal. Inténtalo de nuevo.'
    try {
      const j = await r.json()
      if (typeof j.detail === 'string') msg = j.detail
    } catch { /* sin cuerpo JSON */ }
    throw new Error(msg)
  }
  return r.json()
}

export const obtenerAutos = () => pedir('/api/autos')
export const obtenerUsuarios = () => pedir('/api/usuarios')
export const obtenerUsuario = (id) => pedir(`/api/usuarios/${id}`)
export const obtenerEvaluacion = () => pedir('/api/evaluacion')
export const recomendar = (cuerpo) =>
  pedir('/api/recomendar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpo),
  })
