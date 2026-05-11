/**
 * Shadow Network Intelligence - Alert Sidebar
 * Real-time fraud alert feed
 */
import React, { useState, useEffect } from 'react';

interface Alert {
  id: string;
  type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  created_at: string;
}

export function AlertSidebar() {
  const [alerts, setAlerts] = useState<Alert[]>([
    {
      id: 'ALT_001',
      type: 'RAPID_TRANSFER',
      severity: 'HIGH',
      description: '5 transactions within 1 hour between same accounts',
      created_at: new Date().toISOString()
    },
    {
      id: 'ALT_002',
      type: 'SHELL_COMPANY',
      severity: 'CRITICAL',
      description: 'Circular ownership detected between 3 companies',
      created_at: new Date(Date.now() - 300000).toISOString()
    }
  ]);

  const severityColors = {
    LOW: 'border-l-yellow-400',
    MEDIUM: 'border-l-orange-400',
    HIGH: 'border-l-red-400',
    CRITICAL: 'border-l-red-700 animate-pulse'
  };

  return (
    <aside className="w-80 border-l bg-card overflow-y-auto">
      <div className="p-4 border-b">
        <h2 className="font-semibold">Active Alerts</h2>
        <p className="text-sm text-muted-foreground">{alerts.length} pending</p>
      </div>
      
      <div className="divide-y">
        {alerts.map((alert) => (
          <div 
            key={alert.id}
            className={`p-4 border-l-4 ${severityColors[alert.severity]} hover:bg-accent cursor-pointer`}
          >
            <div className="flex items-start justify-between">
              <span className={`text-xs font-medium px-2 py-1 rounded ${
                alert.severity === 'CRITICAL' ? 'bg-red-100 text-red-700' :
                alert.severity === 'HIGH' ? 'bg-red-50 text-red-600' :
                'bg-yellow-50 text-yellow-600'
              }`}>
                {alert.severity}
              </span>
              <span className="text-xs text-muted-foreground">
                {new Date(alert.created_at).toLocaleTimeString()}
              </span>
            </div>
            <div className="mt-2 text-sm font-medium">{alert.type}</div>
            <p className="mt-1 text-sm text-muted-foreground">{alert.description}</p>
          </div>
        ))}
      </div>
    </aside>
  );
}
