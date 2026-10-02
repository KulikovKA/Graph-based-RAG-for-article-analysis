export interface Session {
  user_id: string;
  csrf_token: string;
}
export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}
export interface ConversationDetail extends Conversation {
  idea: { id: string; version_no: number; normalized: unknown } | null;
  last_runs: string[];
}
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  run_id: string | null;
  created_at: string;
}
export interface Page<T> {
  items: T[];
  next_cursor: string | null;
}
export interface Progress {
  schema_version: 1;
  attempt: number;
  stage: string;
  phase: 'started' | 'completed' | 'waiting';
  stage_started_at?: string | null;
  counts: { feature_count?: number; candidate_count?: number; selected_document_count?: number };
}
export interface Claim {
  text: string;
  evidence_ids: string[];
  quotes: { evidence_id: string; start: number; end: number; text: string }[];
}
export interface Limitation {
  code: string;
  message: string;
}
export interface Answer {
  schema_version: 1;
  summary: Claim[];
  matches: { feature_id: string; document_id: string; claims: Claim[] }[];
  differences: { feature_id: string; claims: Claim[] }[];
  limitations: Limitation[];
  followup_suggestions: string[];
}
export interface PublicAnalysis {
  schema_version: 1;
  items: Claim[];
  limitations: Limitation[];
}
export interface Presentation {
  schema_version: 1;
  presentation_id: string;
  renderer_version: string;
  text: string;
  text_sha256: string;
  chunk_count: number;
}
export interface Source {
  document_id: string;
  revision_id: string;
  title: string;
  kind: string;
  publication_date?: string | null;
  url: string;
  evidence_ids: string[];
}
export interface Evidence {
  evidence_id: string;
  document_id: string;
  revision_id: string;
  chunk_id: string;
  section: string;
  span_start: number;
  span_end: number;
  quoted_span: string;
  source_url: string;
}
export interface Coverage {
  sources: { source: string; status: string; reason_code?: string | null }[];
  channels: { channel: string; status: string; reason_code?: string | null }[];
  partial: boolean;
  historical: boolean;
}
export interface Run {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  stage: string;
  progress: Progress | Record<string, never>;
  idea_version_id: string | null;
  source_run_id: string | null;
  outcome: 'analysis' | 'safe_fallback' | 'no_evidence' | 'clarification' | null;
  answer: Answer | null;
  public_analysis: PublicAnalysis | null;
  answer_presentation: Presentation | null;
  sources: Source[];
  coverage: Coverage;
  graph_url: string | null;
  created_at: string;
  completed_at: string | null;
  error_code: string | null;
}
export interface Accepted {
  message_id: string;
  run_id: string;
  status_url: string;
  events_url: string;
}
export interface MessageInput {
  content: string;
  expected_idea_version: number;
  source_run_id?: string;
  analyze: true;
}
export interface Envelope {
  run_id: string;
  seq: number;
  at: string;
  payload: Record<string, unknown>;
}
