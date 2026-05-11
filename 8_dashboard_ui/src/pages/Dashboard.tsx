import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

export default function Dashboard() {
  const [stats, setStats] = useState({
    total_transactions: 15420,
    flagged_transactions: 342,
    active_alerts: 3,
    risk_score: 72
  });
  const [alerts, setAlerts] = useState<any[]>([]);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      const response = await fetch('/api/v1/alerts');
      const data = await response.json();
      setAlerts(data);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Fraud Detection Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card className="bg-blue-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Total Transactions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-700">{stats.total_transactions.toLocaleString()}</div>
          </CardContent>
        </Card>
        
        <Card className="bg-red-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Flagged Transactions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-700">{stats.flagged_transactions}</div>
          </CardContent>
        </Card>
        
        <Card className="bg-yellow-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Active Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-yellow-700">{stats.active_alerts}</div>
          </CardContent>
        </Card>
        
        <Card className="bg-purple-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Network Risk Score
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-purple-700">{stats.risk_score}%</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Alerts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {alerts.map((alert, i) => (
                <div key={i} className="p-3 border rounded bg-gray-50">
                  <div className="flex items-center justify-between mb-1">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      alert.severity === 'CRITICAL' ? 'bg-red-200 text-red-800' :
                      alert.severity === 'HIGH' ? 'bg-orange-200 text-orange-800' :
                      'bg-yellow-200 text-yellow-800'
                    }`}>
                      {alert.severity}
                    </span>
                    <span className="text-xs text-gray-500">{alert.type}</span>
                  </div>
                  <p className="text-sm">{alert.description}</p>
                  <div className="text-xs text-gray-400 mt-1">Entity: {alert.entity_id}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <button className="w-full p-3 text-left border rounded hover:bg-blue-50">
                <div className="font-medium">Run Investigation</div>
                <div className="text-sm text-gray-500">Analyze entity for fraud patterns</div>
              </button>
              <button className="w-full p-3 text-left border rounded hover:bg-blue-50">
                <div className="font-medium">Generate SAR Report</div>
                <div className="text-sm text-gray-500">Create suspicious activity report</div>
              </button>
              <button className="w-full p-3 text-left border rounded hover:bg-blue-50">
                <div className="font-medium">Search Transactions</div>
                <div className="text-sm text-gray-500">Query the transaction graph</div>
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
