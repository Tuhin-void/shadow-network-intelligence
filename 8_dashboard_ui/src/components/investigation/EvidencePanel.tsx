/**
 * Shadow Network Intelligence - Evidence Panel
 * Shows evidence for investigations
 */
import React from 'react';

export function EvidencePanel({ evidence }) {
  if (!evidence || evidence.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        No evidence collected yet
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {evidence.map((item, index) => (
        <div 
          key={index}
          className="p-3 border rounded-lg bg-slate-50"
        >
          <div className="flex items-center justify-between">
            <span className={`px-2 py-1 rounded text-xs font-medium ${
              item.type === 'transaction' ? 'bg-blue-100 text-blue-800' :
              item.type === 'entity' ? 'bg-purple-100 text-purple-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {item.type.toUpperCase()}
            </span>
            {item.score && (
              <span className="text-sm font-medium">
                Score: {(item.score * 100).toFixed(0)}%
              </span>
            )}
          </div>
          
          <div className="mt-2">
            <div className="font-medium">{item.id || item.name}</div>
            {item.amount && (
              <div className="text-sm text-muted-foreground">
                Amount: ${item.amount.toLocaleString()}
              </div>
            )}
            {item.risk_factors && (
              <div className="mt-1 flex flex-wrap gap-1">
                {item.risk_factors.map((factor, i) => (
                  <span key={i} className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs">
                    {factor}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}