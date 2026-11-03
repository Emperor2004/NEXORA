import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api-client'
import type { Application } from '../../types'
import { humanize, State } from '../components/opportunities'

const statuses = ['interested', 'preparing', 'submitted', 'interview', 'offered', 'accepted', 'rejected', 'withdrawn']

export function ApplicationsPage() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['applications'], queryFn: () => api<{ applications: Application[] }>('/api/applications') })
  const update = useMutation({ mutationFn: ({ id, status }: { id: string; status: string }) => api<Application>(`/api/applications/${id}`, { method: 'PATCH', body: JSON.stringify({ status, note: '' }) }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['applications'] }) })
  const items = query.data?.applications || []
  return <section><div className="section-heading"><div><span className="eyebrow">APPLICATION TRACKER</span><h2>Your next steps</h2></div><span className="muted">{items.length} tracked</span></div>
    <State loading={query.isLoading} error={query.error} empty={!query.isLoading && !query.error && items.length === 0}><div className="app-list">{items.map((application) => <article className="app-row" key={application.id}>
      <div className="app-icon">↗</div><div className="app-info"><h3>{application.opportunity_title || 'Opportunity'}</h3><p>{application.opportunity_organization || 'Organization not stated'}</p><small>Started {new Date(application.created_at).toLocaleDateString()}</small></div>
      <select aria-label={`Status for ${application.opportunity_title}`} value={application.status} onChange={(event) => update.mutate({ id: application.id, status: event.target.value })}>{statuses.map((status) => <option key={status} value={status}>{humanize(status)}</option>)}</select><Link to={`/opportunities/${application.opportunity_id}`} className="row-link">View →</Link>
    </article>)}</div>{update.error && <div className="notice error">{update.error.message}</div>}</State>
  </section>
}
