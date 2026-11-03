import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import type { UseMutationResult } from '@tanstack/react-query'
import type { Opportunity } from '../../types'
import { humanize, OpportunityList } from '../components/opportunities'

const workflowSchema = z.object({
  user_request: z.string().min(10, 'Describe the internship you want in at least 10 characters.').max(3000),
  max_results: z.number().min(1).max(10),
  candidate_profile: z.object({ degrees: z.array(z.string()), branches: z.array(z.string()), academic_years: z.array(z.string()), cgpa: z.number().nullable(), nationality: z.string().nullable(), target_domains: z.array(z.string()), preferred_locations: z.array(z.string()) }).nullable(),
})
export type WorkflowForm = z.infer<typeof workflowSchema>
export type WorkflowResult = { workflow_status?: string; opportunities?: Opportunity[] }
export type DiscoveryMutation = UseMutationResult<WorkflowResult, Error, WorkflowForm>
const emptyProfile = { degrees: [], branches: [], academic_years: [], cgpa: null, nationality: null, target_domains: [], preferred_locations: [] }
const split = (value: string) => value.split(',').map((part) => part.trim()).filter(Boolean)

export function DiscoverPage({ mutation }: { mutation: DiscoveryMutation }) {
  const { register, handleSubmit, formState: { errors }, setValue } = useForm<WorkflowForm>({ resolver: zodResolver(workflowSchema), defaultValues: { user_request: '', max_results: 5, candidate_profile: null } })
  const [withProfile, setWithProfile] = useState(false)
  const result = mutation.data
  return <div className="discover-grid"><section className="panel"><span className="eyebrow">NEW SEARCH</span><h2>What kind of internship are you looking for?</h2><p>Be specific about the field, location, dates, or experience level. NEXORA searches public sources and keeps links to the original postings.</p><form onSubmit={handleSubmit((data) => mutation.mutate(data))}>
    <label>Your search brief<textarea rows={5} {...register('user_request')} placeholder="e.g. Summer research internships in computational biology at universities or public research institutes in India" /></label>{errors.user_request && <small className="field-error">{errors.user_request.message}</small>}
    <label>Maximum opportunities<select {...register('max_results', { valueAsNumber: true })}>{[3, 5, 8, 10].map((count) => <option key={count} value={count}>{count} results</option>)}</select></label>
    <label className="checkline"><input type="checkbox" checked={withProfile} onChange={(event) => { setWithProfile(event.target.checked); setValue('candidate_profile', event.target.checked ? emptyProfile : null) }} /> Include candidate details for initial eligibility assessment</label>
    {withProfile && <div className="profile-fields"><label>Degrees, comma separated<input onChange={(event) => setValue('candidate_profile.degrees', split(event.target.value))} placeholder="BSc, MSc" /></label><label>Fields of study<input onChange={(event) => setValue('candidate_profile.branches', split(event.target.value))} placeholder="Biology, Computer Science" /></label><label>Preferred locations<input onChange={(event) => setValue('candidate_profile.preferred_locations', split(event.target.value))} placeholder="India, Bengaluru" /></label><label>CGPA (out of 10)<input type="number" step="0.01" min="0" max="10" onChange={(event) => setValue('candidate_profile.cgpa', event.target.value ? Number(event.target.value) : null)} /></label><p className="muted full">Details are sent to the configured model provider as needed by the workflow. Don’t include sensitive personal information.</p></div>}
    {mutation.error && <div className="notice error">{mutation.error.message}</div>}<button className="button primary" disabled={mutation.isPending}>{mutation.isPending ? 'Searching public sources…' : 'Run discovery →'}</button>
  </form></section>
    <aside className="note-panel"><span className="eyebrow">HOW IT WORKS</span><ol><li>Search across source categories</li><li>Retrieve public vacancy pages</li><li>Extract details with source evidence</li><li>Review employer signals and risk cues</li></ol><p>Discovery can take a few minutes. Search results are leads; review the original announcement before applying.</p></aside>
    {result && <section className="result-panel"><div className="section-heading"><div><span className="eyebrow">RUN {humanize(result.workflow_status || 'completed')}</span><h2>Discovery results</h2></div></div><p>{result.opportunities?.length || 0} opportunity records returned. Review evidence and verification details on each record.</p>{result.opportunities?.length ? <OpportunityList items={result.opportunities} /> : <div className="state">No opportunities were returned for this search.</div>}</section>}
  </div>
}

