import { DocumentInfo, RunInfo } from './types';

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

export async function uploadPdf(file: File): Promise<DocumentInfo> {
  const body = new FormData();
  body.append('file', file);
  const res = await fetch(`${API_BASE}/api/documents`, { method: 'POST', body });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function startRun(documentId: string, question: string): Promise<RunInfo> {
  const res = await fetch(`${API_BASE}/api/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId, question }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getRun(runId: string): Promise<RunInfo> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getArtifact(runId: string, name: string): Promise<unknown> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/artifacts/${name}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(await res.text());
  const type = res.headers.get('content-type') ?? '';
  return type.includes('json') ? res.json() : res.text();
}
