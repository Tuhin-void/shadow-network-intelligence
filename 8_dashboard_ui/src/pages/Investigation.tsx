import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Timeline } from '../components/investigation/Timeline';
import { EvidencePanel } from '../components/investigation/EvidencePanel';

export default function Investigation() {
  const { id } = useParams();
  const [investigation, setInvestigation] = React.useState<any>(null);

  React.useEffect(() => {
    if (id) {
      fetchInvestigation(id);
    }
  }, [id]);

  const fetchInvestigation = async (invId: string) => {
    try {
      const response = await fetch(`/api/v1/investigate/${invId}`);
      if (response.ok) {
        const data = await response.json();
        setInvestigation(data);
      }
    } catch (error) {
      console.error('Failed to fetch investigation:', error);
    }
  };

  if (!investigation) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Investigation {id}</h1>
        <p>Loading investigation...</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Investigation: {investigation.investigation_id}</h1>
        <Link to="/" className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">
          Back to Dashboard
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Risk Assessment</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-4">
                <span className="text-lg">Risk Score:</span>
                <span className={`text-2xl font-bold ${
                  investigation.risk_score > 0.7 ? 'text-red-600' :
                  investigation.risk_score > 0.4 ? 'text-yellow-600' : 'text-green-600'
                }`}>
                  {(investigation.risk_score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="text-gray-700">{investigation.answer}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Evidence</CardTitle>
            </CardHeader>
            <CardContent>
              <EvidencePanel evidence={investigation.evidence || []} />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Investigation Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <Timeline events={[
                { timestamp: new Date().toISOString(), action: 'Investigation Started', status: 'completed' },
                { timestamp: new Date().toISOString(), action: 'Evidence Collection', status: 'completed' },
                { timestamp: new Date().toISOString(), action: 'Risk Analysis', status: 'active' },
              ]} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recommended Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {(investigation.recommended_actions || []).map((action: string, i: number) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="w-2 h-2 mt-2 bg-blue-500 rounded-full"></span>
                    <span className="text-sm">{action}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
