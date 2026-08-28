import { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import coseBilkent from 'cytoscape-cose-bilkent';
import type { GraphEvidence } from '../services/api';

cytoscape.use(coseBilkent);

const nodeColors: Record<string, string> = {
  account: '#3B82F6',
  device: '#22C55E',
  ip: '#EAB308',
  token: '#A855F7',
  order: '#6366F1',
  payment: '#EC4899',
  refund: '#EF4444',
};

const nodeLabels: Record<string, string> = {
  account: 'Account',
  device: 'Device',
  ip: 'IP Address',
  token: 'Token',
  order: 'Order',
  payment: 'Payment',
  refund: 'Refund',
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
          label: node.label,
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
              nodeColors[ele.data('type')] || '#9CA3AF',
            color: '#1F2937',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '11px',
            'font-weight': 'bold',
            width: 50,
            height: 50,
            'border-width': 2,
            'border-color': '#374151',
            'text-wrap': 'ellipsis',
            'text-max-width': '80px',
          } as cytoscape.Css.Node,
        },
        {
          selector: 'edge',
          style: {
            width: 2,
            'line-color': '#9CA3AF',
            'target-arrow-color': '#9CA3AF',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(relationship)',
            'font-size': '9px',
            color: '#6B7280',
            'text-rotation': 'autorotate',
            'text-margin-y': -10,
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
        padding: 30,
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
        className="w-full h-96 border border-gray-200 rounded-lg bg-gray-50"
      />
      <div className="mt-3 flex flex-wrap gap-3">
        {Object.entries(nodeColors).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div
              className="w-3 h-3 rounded-full border border-gray-400"
              style={{ backgroundColor: color }}
            />
            <span className="text-xs text-gray-600">{nodeLabels[type]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
