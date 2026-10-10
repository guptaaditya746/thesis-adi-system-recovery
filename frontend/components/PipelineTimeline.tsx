import { CheckCircle2, CircleDashed, LoaderCircle, XCircle } from 'lucide-react';
import { RunEvent } from '@/lib/types';

const stages = ['question', 'ontology', 'sparql', 'retrieval', 'edc', 'verification', 'validation', 'evaluation'];

export function PipelineTimeline({ events }: { events: RunEvent[] }) {
  return (
    <div className="timeline">
      {stages.map((stage, index) => {
        const latest = [...events].reverse().find(e => e.stage === stage);
        const status = latest?.status;
        const Icon = status === 'completed' ? CheckCircle2 : status === 'failed' ? XCircle : status === 'started' ? LoaderCircle : CircleDashed;
        return (
          <div className={`timelineRow ${status ?? 'pending'}`} key={stage}>
            <div className="timelineRail">
              <Icon size={18} className={status === 'started' ? 'spin' : ''} />
              {index < stages.length - 1 && <span className="line" />}
            </div>
            <div>
              <div className="stageName">{stage}</div>
              <div className="stageDetail">{latest?.title ?? 'Waiting'}</div>
              {latest?.detail && <div className="muted small">{latest.detail}</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
