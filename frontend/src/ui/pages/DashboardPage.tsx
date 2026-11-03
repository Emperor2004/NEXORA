import { Link } from 'react-router-dom'
import { api } from '../../lib/api-client'
import { useQuery } from '@tanstack/react-query'
import type { Application } from '../../types'
import { OpportunityList, State, type OpportunityQuery } from '../components/opportunities'

export function DashboardPage({ opportunities }: { opportunities: OpportunityQuery }) {
  const applications = useQuery({ queryKey: ['applications'], queryFn: () => api<{ applications: Application[] }>('/api/applications') })
  const items = opportunities.data?.opportunities || []
  const apps = applications.data?.applications || []
  return <><section className="hero"><div><span className="eyebrow">YOUR SEARCH DESK</span><h2>Good opportunities leave<br />a trail of evidence.</h2><p>Search across public sources, review what’s verified, then track the applications you choose to make.</p><Link className="button light" to="/discover">Describe what you’re looking for <span>→</span></Link></div><div className="hero-mark">N<span>↗</span></div></section>
    <div className="stats"><div className="stat"><span>OPPORTUNITIES LOADED</span><b>{opportunities.isLoading ? '—' : items.length}</b><small>Latest records from the local API</small></div><div className="stat"><span>APPLICATIONS LOADED</span><b>{applications.isLoading ? '—' : apps.length}</b><small>User managed, status by status</small></div><div className="stat"><span>API WORKFLOW</span><b>{opportunities.isError ? 'Offline' : opportunities.isLoading ? 'Checking' : 'Ready'}</b><small>Results are grounded in source evidence</small></div></div>
    <div className="section-heading"><div><span className="eyebrow">RECENT FINDS</span><h2>Opportunities</h2></div><Link to="/opportunities">View all →</Link></div>
    <State loading={opportunities.isLoading} error={opportunities.error} empty={!opportunities.isLoading && !opportunities.error && items.length === 0}><OpportunityList items={items.slice(0, 4)} /></State>
  </>
}
