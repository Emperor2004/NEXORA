import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, setSessionToken } from './api-client'

describe('API client', () => {
  afterEach(() => { vi.unstubAllGlobals(); setSessionToken('') })

  it('adds the in-memory bearer token and serializes query parameters', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ opportunities: [] }) })
    vi.stubGlobal('fetch', fetchMock)
    setSessionToken('session-secret')
    await api('/api/opportunities', { query: { limit: 10, offset: 0 } })
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('limit=10')
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer session-secret')
  })

  it('surfaces API error details', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401, statusText: 'Unauthorized', json: async () => ({ detail: 'A valid bearer token is required.' }) }))
    await expect(api('/api/opportunities')).rejects.toThrow('A valid bearer token is required.')
  })
})
