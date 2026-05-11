import React, { useState } from 'react';

export function GraphView() {
  const [nodes] = useState([
    { id: 'ACC001', type: 'Account', x: 100, y: 100 },
    { id: 'ACC002', type: 'Account', x: 200, y: 150 },
    { id: 'CPY001', type: 'Company', x: 300, y: 100 },
    { id: 'PER001', type: 'Person', x: 200, y: 200 },
  ]);

  return (
    <div className="h-full bg-gray-100 rounded p-4">
      <svg className="w-full h-full" viewBox="0 0 400 300">
        {nodes.map((node) => (
          <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
            <circle r="20" fill={node.type === 'Account' ? '#3b82f6' : node.type === 'Company' ? '#8b5cf6' : '#22c55e'} />
            <text textAnchor="middle" dy="35" className="text-xs fill-gray-700">{node.id}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}
