export type DocumentInfo = {
  id: string;
  filename: string;
  page_count: number;
  workspace: string;
};

export type RunEvent = {
  id: string;
  run_id: string;
  type: string;
  stage: string;
  status: 'started' | 'completed' | 'failed' | 'info';
  title: string;
  detail: string;
  artifact_id?: string | null;
  timestamp: string;
};

export type VerifiedTriple = {
  triple: {
    id: string;
    subject: string;
    predicate: string;
    object: string;
    predicate_uri?: string | null;
    evidence_ids: string[];
    canonicalization: string;
    confidence: number;
  };
  status: string;
  explanation: string;
  provenance: {
    evidence_ids: string[];
    inference_type: string;
  };
};

export type RunInfo = {
  id: string;
  document_id: string;
  question: string;
  status: string;
  events: RunEvent[];
  final_triples: VerifiedTriple[];
  evaluation?: Record<string, unknown> | null;
  error?: string | null;
};
