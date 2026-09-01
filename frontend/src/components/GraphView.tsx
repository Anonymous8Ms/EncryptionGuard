import { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import coseBilkent from 'cytoscape-cose-bilkent';
import type { GraphEvidence } from '../services/api';

cytoscape.use(coseBilkent);

const nodeColors: Record<string, string> = {
  account: '#141414',
  device: '#1351AA',
  ip: '#444343',
  token: '#7A7A7A',
  order: '#141414',
  payment: '#1351AA',
  refund: '#444343',
};

const nodeLabels: Record<string, string> = {
  account: 'ACCT',
  device: 'DEV',
  ip: 'IP',
  token: 'TKN',
  order: 'ORD',
  payment: 'PAY',
  refund: 'REF',
};

interface GraphViewProps {
  graphData: GraphEvidence;
  className?: string;
}

export default function GraphView({ graphData, className }: GraphViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const elements: cytoscape.ElementDefinition[] = [
      ...graphData.nodes.map((node) => ({
        data: {
          id: node.id,
          label: nodeLabels[node.type] || node.type.toUpperCase(),
          type: node.type,
          ...node.properties,
        },
      })),
      ...graphData.edges.map((edge, idx) => ({
        data: {
          id: `edge-${idx}`,
          source: edge.source,
          target: edge.target,
          relationship: edge.relationship,
          ...edge.properties,
        },
      })),
    ];

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'background-color': (ele: cytoscape.NodeSingular) =>
              nodeColors[ele.data('type')] || '#141414',
            color: '#E3E2DE',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '10px',
            'font-family': '"JetBrains Mono", Consolas, monospace',
            'font-weight': 700,
            'letter-spacing': '0.1em',
            width: 40,
            height: 40,
            'border-width': 0,
            'text-wrap': 'ellipsis',
            'text-max-width': '60px',
          } as cytoscape.Css.Node,
        },
        {
          selector: 'edge',
          style: {
            width: 1,
            'line-color': '#C7C7C7',
            'target-arrow-color': '#C7C7C7',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.8,
            'curve-style': 'bezier',
            label: 'data(relationship)',
            'font-size': '9px',
            'font-family': '"JetBrains Mono", Consolas, monospace',
            color: '#7A7A7A',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
          } as cytoscape.Css.Edge,
        },
      ],
      layout: {
        name: 'cose-bilkent',
        animate: 'end',
        animationDuration: 500,
        nodeDimensionsIncludeLabels: true,
        randomize: false,
        fit: true,
        padding: 40,
      } as cytoscape.LayoutOptions,
    });

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [graphData]);

  return (
    <div className={className}>
      <div
        ref={containerRef}
        className="w-full h-[500px] border border-border bg-cream"
      />
      <div className="mt-6 flex flex-wrap gap-8">
        {Object.entries(nodeColors).map(([type, color]) => (
          <div key={type} className="flex items-center gap-3">
            <div
              className="w-3 h-3"
              style={{ backgroundColor: color }}
            />
            <span className="mono-label">{nodeLabels[type]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
