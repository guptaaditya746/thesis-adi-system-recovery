 'use client';

import { useMemo } from 'react';
import { Background, Controls, Edge, Node, ReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { VerifiedTriple } from '@/lib/types';

export function TripleGraph({ triples }: { triples: VerifiedTriple[] }) {
  const { nodes, edges } = useMemo(() => {
    const labels = Array.from(new Set(triples.flatMap(t => [t.triple.subject, t.triple.object])));
    const nodes: Node[] = labels.map((label, i) => ({
      id: label,
      position: { x: (i % 4) * 220, y: Math.floor(i / 4) * 140 },
      data: { label },
    }));
    const edges: Edge[] = triples.map((t, i) => ({
      id: t.triple.id || `e-${i}`,
      source: t.triple.subject,
      target: t.triple.object,
      label: t.triple.predicate,
      animated: t.status === 'supported',
    }));
    return { nodes, edges };
  }, [triples]);

  if (!triples.length) return <div className="empty">Triples will appear here.</div>;
  return <div className="graph"><ReactFlow nodes={nodes} edges={edges} fitView><Background /><Controls /></ReactFlow></div>;
}
