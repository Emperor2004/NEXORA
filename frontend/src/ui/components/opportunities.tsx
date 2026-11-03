import { Link } from 'react-router-dom'
import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { api } from '../../lib/api-client'
import type { Opportunity } from '../../types'

export type OpportunityPage = { opportunities: Opportunity[] }

export function useOpportunities() {
  return useQuery({ queryKey: ['opportunities'], queryFn: () => api<OpportunityPage>('/api/opportunities') })
}

export function titleOf(item: Opportunity) { return item.extraction?.opportunity_title || 'Untitled opportunity' }
export function organizationOf(item: Opportunity) { return item.extraction?.organization || 'Organization not stated' }
export function sourceUrl(item: Opportunity) { return item.source?.url || item.extraction?.source_url || '' }
export function humanize(value: string) { return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) }
export function verificationLabel(item: Opportunity) {
  return humanize(item.verification_status || item.verification?.verification_status || 'not independently verified')
}

export function State({ loading, error, empty, children }: { loading?: boolean; error?: Error | null; empty?: boolean; children: React.ReactNode }) {
  if (loading) return <div className="state">Loading NEXORA data…</div>
  if (error) return <div className="state error">{error.message}. Check the API connection and token in Settings.</div>
  if (empty) return <div className="state">No records yet. Run discovery to find opportunities.</div>
  return <>{children}</>
}

export function OpportunityList({ items }: { items: Opportunity[] }) {
  return <div className="cards">{items.map((item) => <Link className="opportunity-card" to={`/opportunities/${item.opportunity_id}`} key={item.opportunity_id}>
    <div className="card-top"><span className="tag">{item.source?.adapter || item.source?.platform || 'PUBLIC SOURCE'}</span><span className="score">{item.ranking?.score != null ? `${Math.round(item.ranking.score)} fit` : 'REVIEW'}</span></div>
    <h3>{titleOf(item)}</h3><p>{organizationOf(item)}{item.extraction?.location ? ` · ${item.extraction.location}` : ''}</p>
    <div className="card-bottom"><span className="verification">{verificationLabel(item)}</span><span>Open record ↗</span></div>
  </Link>)}</div>
}

export type OpportunityQuery = UseQueryResult<OpportunityPage, Error>
