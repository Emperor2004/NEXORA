import { useState } from 'react'
import { getApiBaseUrl, setSessionToken } from '../../lib/api-client'

export function SettingsPage() {
  const [token, setToken] = useState('')
  return <section className="panel narrow"><span className="eyebrow">CONNECTION</span><h2>Local API access</h2><p>The token stays in this browser tab’s memory and is cleared on refresh. It is never written to storage or sent anywhere except your configured API.</p>
    <label>API bearer token<input type="password" value={token} onChange={(event) => { setToken(event.target.value); setSessionToken(event.target.value) }} placeholder="Optional for loopback development" autoComplete="off" /></label>
    <p className="muted">API base URL: {getApiBaseUrl()}. Set it with <code>VITE_API_BASE_URL</code> before starting Vite.</p><button className="button" onClick={() => { setToken(''); setSessionToken('') }}>Clear token</button>
  </section>
}
