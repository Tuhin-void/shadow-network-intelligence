/**
 * Shadow Network Intelligence - Reports Page
 * Lists and previews generated reports
 */
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

export default function Reports() {
  const [reports] = useState([
    { id: 'RPT_001', type: 'SAR', title: 'Suspicious Activity Report - Case 2024-001', status: 'DRAFT', created: '2024-01-15' },
    { id: 'RPT_002', type: 'EXECUTIVE', title: 'Q4 2024 Executive Summary', status: 'COMPLETED', created: '2024-01-10' },
    { id: 'RPT_003', type: 'SAR', title: 'SAR - Shell Company Ring', status: 'FILED', created: '2024-01-08' },
  ]);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Reports</h1>
        <button className="px-4 py-2 bg-blue-600 text-white rounded">
          Generate New Report
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {reports.map((report) => (
          <Card key={report.id} className="cursor-pointer hover:shadow-lg transition-shadow">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">{report.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    report.type === 'SAR' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'
                  }`}>
                    {report.type}
                  </span>
                  <span className={`text-xs ${
                    report.status === 'COMPLETED' ? 'text-green-600' :
                    report.status === 'FILED' ? 'text-blue-600' :
                    'text-yellow-600'
                  }`}>
                    {report.status}
                  </span>
                </div>
                <div className="text-sm text-muted-foreground">
                  Created: {report.created}
                </div>
                <div className="flex gap-2 mt-4">
                  <button className="flex-1 px-3 py-2 border rounded text-sm hover:bg-gray-50">
                    View
                  </button>
                  <button className="flex-1 px-3 py-2 border rounded text-sm hover:bg-gray-50">
                    Export
                  </button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}