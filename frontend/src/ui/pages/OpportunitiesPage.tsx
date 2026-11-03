import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api-client'
import type { Application, Opportunity } from '../../types'
import { humanize, OpportunityList, sourceUrl, State, titleOf, organizationOf, verificationLabel, useOpportunities } from '../components/opportunities'

export function OpportunitiesPage() {
  const query = useOpportunities()
  const items = query.data?.opportunities || []
  return <section><div className="section-heading"><div><span className="eyebrow">YOUR LIBRARY</span><h2>Opportunities</h2></div><span className="muted">{items.length} records</span></div><State loading={query.isLoading} error={query.error} empty={!query.isLoading && !query.error && items.length === 0}><OpportunityList items={items} /></State></section>
}

export function OpportunityDetailPage() {
  const { id = '' } = useParams()
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['opportunity', id], queryFn: () => api<Opportunity>(`/api/opportunities/${encodeURIComponent(id)}`) })
  const create = useMutation({ mutationFn: () => api<Application>('/api/applications', { method: 'POST', body: JSON.stringify({ opportunity_id: id, notes: '' }) }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['applications'] }) })
  const item = query.data
  const risk = item?.verification?.fraud_risk || item?.fraud_risk || {}
  const riskSignals = risk.signals || risk.indicators || []

  return <State loading={query.isLoading} error={query.error}>{item && <>
    <Link className="back" to="/opportunities">← All opportunities</Link>
    <section className="detail-head"><span className="tag">{item.source?.adapter || 'SOURCE RECORD'}</span><h2>{titleOf(item)}</h2><p>{organizationOf(item)} · {item.extraction?.location || 'Location not stated'}</p><div className="detail-actions">{sourceUrl(item) && <a className="button" href={sourceUrl(item)} target="_blank" rel="noreferrer">Original posting ↗</a>}<button className="button primary" onClick={() => create.mutate()} disabled={create.isPending}>Track application</button></div>{create.error && <p className="field-error">{create.error.message}</p>}</section>
    <div className="detail-grid"><section className="panel"><span className="eyebrow">SOURCE BACKED DETAILS</span><h3>What the posting says</h3><dl>{Object.entries(item.extraction || {}).filter(([key, value]) => value != null && !['evidence', 'raw_text'].includes(key)).map(([key, value]) => <div key={key}><dt>{humanize(key)}</dt><dd>{Array.isArray(value) ? value.join(', ') : String(value)}</dd></div>)}</dl>
      {Array.isArray(item.extraction?.evidence) && <><h3>Evidence</h3>{item.extraction.evidence.map((evidence: any, index: number) => <blockquote key={index}>“{evidence.quote || evidence.text || JSON.stringify(evidence)}”<small>{evidence.field_name || evidence.field || evidence.source_location || evidence.source || 'Source evidence'}</small></blockquote>)}</>}
    </section><aside><div className="panel"><span className="eyebrow">VERIFICATION</span><h3>{verificationLabel(item)}</h3><p>{item.verification?.verification_reason || 'Employer corroboration is assessed independently from the page’s official or platform domain.'}</p>
      {item.verification?.independent_sources?.map((source: any, index: number) => source.url ? <a className="source-link" key={source.url + index} href={source.url} target="_blank" rel="noreferrer">Independent corroboration ↗<br />{source.url}</a> : null)}
      <div className="risk">Risk review: {humanize(risk.level || risk.status || 'unknown')}</div>{Array.isArray(riskSignals) && riskSignals.map((signal: any, index: number) => <blockquote key={index}>{signal.quote || signal.evidence || String(signal)}</blockquote>)}</div>
      <div className="panel source-panel"><span className="eyebrow">ORIGINAL SOURCE</span><p>{item.source?.platform || item.source?.adapter || 'Source recorded'}</p>{sourceUrl(item) && <a href={sourceUrl(item)} target="_blank" rel="noreferrer" className="source-link">{sourceUrl(item)}</a>}
        {item.source_records?.length ? <><h3>Other discovered sources</h3>{item.source_records.map((source, index) => source.url ? <a className="source-link source-record" key={`${source.url}-${index}`} href={source.url} target="_blank" rel="noreferrer">{source.adapter || source.platform || 'Additional source'} ↗<br />{source.url}</a> : null)}</> : null}
      </div></aside></div>
  </>}</State>
}
