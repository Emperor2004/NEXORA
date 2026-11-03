export type Opportunity = {
  opportunity_id: string
  verification_status?: string
  extraction?: Record<string, any>
  source?: Record<string, any>
  source_records?: Array<Record<string, any>>
  verification?: Record<string, any>
  fraud_risk?: Record<string, any>
  eligibility?: Record<string, any>
  ranking?: Record<string, any>
}
export type Application = {
  id: string
  opportunity_id: string
  opportunity_title?: string
  opportunity_organization?: string
  status: string
  notes: string
  created_at: string
  history?: Array<{ new_status: string; note: string; changed_at: string }>
}
