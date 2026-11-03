import { Link, NavLink, Route, Routes } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getApiBaseUrl } from '../lib/api-client'
import { useOpportunities } from './components/opportunities'
import { ApplicationsPage } from './pages/ApplicationsPage'
import { DashboardPage } from './pages/DashboardPage'
import { DiscoverPage, type WorkflowForm, type WorkflowResult } from './pages/DiscoverPage'
import { OpportunityDetailPage, OpportunitiesPage } from './pages/OpportunitiesPage'
import { SettingsPage } from './pages/SettingsPage'

export default function App() {
  const queryClient = useQueryClient()
  const health = useQuery({ queryKey: ['health'], queryFn: () => api<{ status: string }>('/health'), refetchInterval: 30_000 })
  const opportunities = useOpportunities()
  const discovery = useMutation({
    mutationFn: (body: WorkflowForm) => api<WorkflowResult>('/api/workflow/run', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => queryClient.invalidateQueries(),
  })

  return <div className="shell">
    <aside className="sidebar">
      <Link className="brand" to="/">NEXORA<span>FIELD NOTES FOR YOUR NEXT STEP</span></Link>
      <nav><NavLink to="/" end>Overview</NavLink><NavLink to="/discover">Discover</NavLink><NavLink to="/opportunities">Opportunities</NavLink><NavLink to="/applications">Applications</NavLink><NavLink to="/settings">Settings</NavLink></nav>
      <div className="side-footer"><span className={`pulse ${health.isSuccess ? '' : 'off'}`} /> API {health.isSuccess ? 'connected' : 'unavailable'}<small>{getApiBaseUrl()}</small></div>
    </aside>
    <main><header className="topbar"><div><span className="eyebrow">INTERNSHIP INTELLIGENCE</span><h1>Find work that moves you forward.</h1></div><Link className="button primary" to="/discover">Start a search <span>↗</span></Link></header>
      <Routes>
        <Route path="/" element={<DashboardPage opportunities={opportunities} />} />
        <Route path="/discover" element={<DiscoverPage mutation={discovery} />} />
        <Route path="/opportunities" element={<OpportunitiesPage />} />
        <Route path="/opportunities/:id" element={<OpportunityDetailPage />} />
        <Route path="/applications" element={<ApplicationsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<div className="state">Page not found.</div>} />
      </Routes>
    </main>
  </div>
}
