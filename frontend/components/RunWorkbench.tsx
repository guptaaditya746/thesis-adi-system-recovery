 'use client';

import { useEffect, useMemo, useState } from 'react';
import { Activity, Braces, Database, FileSearch2, FlaskConical, Network, Play, Upload, Workflow } from 'lucide-react';
import { API_BASE, getArtifact, getRun, startRun, uploadPdf } from '@/lib/api';
import { DocumentInfo, RunEvent, RunInfo } from '@/lib/types';
import { PipelineTimeline } from './PipelineTimeline';
import { TripleGraph } from './TripleGraph';

type Tab = 'evidence' | 'ontology' | 'sparql' | 'triples' | 'evaluation' | 'events';

const tabMeta: Array<[Tab, string, React.ReactNode]> = [
  ['evidence', 'Evidence', <FileSearch2 size={15} key="i" />],
  ['ontology', 'Ontology', <Network size={15} key="i" />],
  ['sparql', 'SPARQL', <Braces size={15} key="i" />],
  ['triples', 'Triples', <Database size={15} key="i" />],
  ['evaluation', 'Evaluation', <FlaskConical size={15} key="i" />],
  ['events', 'Events', <Activity size={15} key="i" />],
];

export function RunWorkbench() {
  const [document, setDocument] = useState<DocumentInfo | null>(null);
  const [question, setQuestion] = useState('');
  const [run, setRun] = useState<RunInfo | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [tab, setTab] = useState<Tab>('evidence');
  const [artifact, setArtifact] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function onFile(file?: File) {
    if (!file) return;
    setBusy(true); setError('');
    try { setDocument(await uploadPdf(file)); } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }

  async function launch() {
    if (!document || !question.trim()) return;
    setBusy(true); setError(''); setEvents([]); setArtifact(null);
    try {
      const created = await startRun(document.id, question.trim());
      setRun(created);
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    if (!run?.id) return;
    const stream = new EventSource(`${API_BASE}/api/runs/${run.id}/events`);
    stream.onmessage = (message) => {
      const evt = JSON.parse(message.data) as RunEvent;
      setEvents(old => old.some(x => x.id === evt.id) ? old : [...old, evt]);
      if (evt.status === 'completed' || evt.status === 'failed') getRun(run.id).then(setRun).catch(() => null);
      if (evt.stage === 'run' && ['completed', 'failed'].includes(evt.status)) stream.close();
    };
    stream.onerror = () => stream.close();
    return () => stream.close();
  }, [run?.id]);

  useEffect(() => {
    if (!run?.id) return;
    const mapping: Record<Tab, string | null> = {
      evidence: 'evidence', ontology: 'subontology', sparql: 'sparql', triples: 'verified_triples',
      evaluation: 'evaluation', events: null,
    };
    const name = mapping[tab];
    if (!name) { setArtifact(events); return; }
    getArtifact(run.id, name).then(setArtifact).catch(() => setArtifact(null));
  }, [tab, run?.id, events.length]);

  const progress = useMemo(() => {
    const completed = new Set(events.filter(e => e.status === 'completed').map(e => e.stage));
    return Math.min(100, Math.round((completed.size / 8) * 100));
  }, [events]);

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand"><div className="logo"><Workflow size={18} /></div><div><strong>ADI Research Workbench</strong><span>Ontology-guided scientific KG pipeline</span></div></div>
        <div className="statusPill"><span className={`dot ${run?.status ?? 'idle'}`} />{run?.status ?? 'idle'}</div>
      </header>

      <section className="hero">
        <div><div className="eyebrow">THESIS EXPERIMENT CONSOLE</div><h1>Follow every artifact, from paper to graph.</h1><p>Question-specific ontology adaptation, SPARQL intent, agentic PDF retrieval, EDC extraction, provenance, validation, and evaluation in one inspectable run.</p></div>
        <div className="progressCard"><span>Run progress</span><strong>{progress}%</strong><div className="progress"><i style={{ width: `${progress}%` }} /></div></div>
      </section>

      <section className="grid">
        <aside className="leftPanel panel">
          <div className="panelTitle">Experiment input</div>
          <label className="uploadBox">
            <Upload size={20} /><strong>{document ? document.filename : 'Upload scientific PDF'}</strong>
            <span>{document ? `${document.page_count} pages · ${document.id}` : 'PDF is parsed into pages, sections and searchable text'}</span>
            <input type="file" accept="application/pdf" onChange={e => onFile(e.target.files?.[0])} />
          </label>
          <label className="fieldLabel">Research question</label>
          <textarea value={question} onChange={e => setQuestion(e.target.value)} placeholder="What does the paper report about…?" rows={6} />
          <button className="primary" onClick={launch} disabled={!document || !question.trim() || busy}><Play size={16} />Start pipeline</button>
          {error && <div className="error">{error}</div>}
          <div className="divider" />
          <div className="panelTitle">Pipeline</div>
          <PipelineTimeline events={events} />
        </aside>

        <section className="workPanel panel">
          <div className="tabs">{tabMeta.map(([id, label, icon]) => <button key={id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>{icon}{label}</button>)}</div>
          {tab === 'evidence' && document ? (
            <div className="evidenceLayout">
              <div className="artifact"><div className="artifactHeader"><FileSearch2 size={15} />Retrieved evidence</div>{artifact ? <pre>{JSON.stringify(artifact, null, 2)}</pre> : <div className="empty">Evidence appears after agentic retrieval.</div>}</div>
              <iframe className="pdfFrame" src={`${API_BASE}/api/documents/${document.id}/pdf`} title="Scientific paper PDF" />
            </div>
          ) : tab === 'triples' && run?.final_triples?.length ? (
            <div className="tripleLayout">
              <div className="tripleTable">{run.final_triples.map(v => <div className="tripleRow" key={v.triple.id}><div><span className="badge">{v.status}</span><strong>{v.triple.subject}</strong><span className="predicate">{v.triple.predicate}</span><strong>{v.triple.object}</strong></div><small>{v.triple.canonicalization} · confidence {Math.round(v.triple.confidence * 100)}% · evidence {v.triple.evidence_ids.join(', ') || 'none'}</small><p>{v.explanation}</p></div>)}</div>
              <TripleGraph triples={run.final_triples} />
            </div>
          ) : tab === 'sparql' && artifact && typeof artifact === 'object' && 'query' in (artifact as Record<string, unknown>) ? (
            <div className="artifact"><div className="artifactHeader"><Braces size={17} />Generated SPARQL</div><pre className="code">{String((artifact as Record<string, unknown>).query)}</pre><pre>{JSON.stringify(artifact, null, 2)}</pre></div>
          ) : (
            <div className="artifact"><div className="artifactHeader">{tabMeta.find(t => t[0] === tab)?.[2]}{tabMeta.find(t => t[0] === tab)?.[1]}</div>{artifact ? <pre>{JSON.stringify(artifact, null, 2)}</pre> : <div className="empty">This artifact will appear when its stage completes.</div>}</div>
          )}
        </section>
      </section>
    </main>
  );
}
