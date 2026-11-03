export type ApiOptions = RequestInit & { query?: Record<string, string | number | undefined> }

let sessionToken = ''

export function setSessionToken(token: string) {
  sessionToken = token.trim()
}

export function getApiBaseUrl() {
  return (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const url = new URL(`${getApiBaseUrl()}${path}`)
  Object.entries(options.query || {}).forEach(([key, value]) => {
    if (value !== undefined) url.searchParams.set(key, String(value))
  })
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (sessionToken) headers.set('Authorization', `Bearer ${sessionToken}`)
  const { query: _query, ...request } = options
  const response = await fetch(url, { ...request, headers })
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = await response.json()
      detail = typeof body.detail === 'string' ? body.detail : detail
    } catch { /* keep HTTP status */ }
    throw new Error(detail)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
