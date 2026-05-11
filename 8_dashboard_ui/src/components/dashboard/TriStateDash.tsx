/**
 * Shadow Network Intelligence - Tri-State Risk Dashboard
 * Shows True/False/Unknown risk assessment states
 */
import React from 'react';

export function TriStateDash() {
  const states = [
    { 
      label: 'Confirmed Fraud', 
      count: 45, 
      color: 'bg-red-500',
      textColor: 'text-red-600',
      icon: '🚨'
    },
    { 
      label: 'Legitimate', 
      count: 892, 
      color: 'bg-green-500',
      textColor: 'text-green-600',
      icon: '✓'
    },
    { 
      label: 'Under Review', 
      count: 127, 
      color: 'bg-yellow-500',
      textColor: 'text-yellow-600',
      icon: '?'
    },
  ];

  const total = states.reduce((acc, s) => acc + s.count, 0);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        {states.map((state) => (
          <div 
            key={state.label}
            className="relative overflow-hidden rounded-lg border p-4"
          >
            <div className="flex items-center justify-between">
              <span className="text-3xl">{state.icon}</span>
              <span className={`text-4xl font-bold ${state.textColor}`}>
                {state.count}
              </span>
            </div>
            <div className="mt-2">
              <div className="text-sm text-muted-foreground">
                {state.label}
              </div>
              <div className="mt-2 h-2 w-full rounded-full bg-gray-200">
                <div 
                  className={`h-2 rounded-full ${state.color}`}
                  style={{ width: `${(state.count / total) * 100}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
      
      <div className="text-center text-sm text-muted-foreground">
        Total Reviewed: {total} transactions
      </div>
    </div>
  );
}
