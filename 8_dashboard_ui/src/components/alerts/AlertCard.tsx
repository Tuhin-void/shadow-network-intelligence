/**
 * Shadow Network Intelligence - Alert Card Component
 * Individual alert display
 */
import React from 'react';

export function AlertCard({ alert, onClick }) {
  const severityColors = {
    LOW: 'border-l-yellow-400 bg-yellow-50',
    MEDIUM: 'border-l-orange-400 bg-orange-50',
    HIGH: 'border-l-red-400 bg-red-50',
    CRITICAL: 'border-l-red-700 bg-red-100 animate-pulse'
  };

  const severityBadges = {
    LOW: 'bg-yellow-100 text-yellow-800',
    MEDIUM: 'bg-orange-100 text-orange-800',
    HIGH: 'bg-red-100 text-red-800',
    CRITICAL: 'bg-red-200 text-red-900'
  };

  return (
    <div 
      className={`p-4 border-l-4 cursor-pointer hover:shadow-md transition-shadow ${severityColors[alert.severity]}`}
      onClick={() => onClick?.(alert)}
    >
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs font-medium px-2 py-1 rounded ${severityBadges[alert.severity]}`}>
          {alert.severity}
        </span>
        <span className="text-xs text-muted-foreground">
          {new Date(alert.created_at).toLocaleTimeString()}
        </span>
      </div>
      
      <div className="font-medium text-sm">{alert.type.replace(/_/g, ' ')}</div>
      
      <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
        {alert.description}
      </p>
      
      <div className="mt-3 flex items-center gap-2">
        <span className="text-xs text-muted-foreground">
          Entity: {alert.entity_id}
        </span>
        <span className="text-xs text-muted-foreground">
          Risk: {(alert.risk_score * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}