import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

interface SearchFilters {
  query: string;
  entityType: string;
  riskLevel: string;
  dateRange: string;
}

export default function Search() {
  const [filters, setFilters] = useState<SearchFilters>({
    query: '',
    entityType: 'all',
    riskLevel: 'all',
    dateRange: '30d'
  });
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(filters)
      });
      const data = await response.json();
      setResults(data.results || []);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Transaction Search</h1>
      
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Search Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Search Query</label>
              <input
                type="text"
                className="w-full px-3 py-2 border rounded"
                placeholder="Enter search terms..."
                value={filters.query}
                onChange={(e) => setFilters({...filters, query: e.target.value})}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Entity Type</label>
              <select
                className="w-full px-3 py-2 border rounded"
                value={filters.entityType}
                onChange={(e) => setFilters({...filters, entityType: e.target.value})}
              >
                <option value="all">All</option>
                <option value="Account">Account</option>
                <option value="Company">Company</option>
                <option value="Person">Person</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Risk Level</label>
              <select
                className="w-full px-3 py-2 border rounded"
                value={filters.riskLevel}
                onChange={(e) => setFilters({...filters, riskLevel: e.target.value})}
              >
                <option value="all">All</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Date Range</label>
              <select
                className="w-full px-3 py-2 border rounded"
                value={filters.dateRange}
                onChange={(e) => setFilters({...filters, dateRange: e.target.value})}
              >
                <option value="7d">Last 7 days</option>
                <option value="30d">Last 30 days</option>
                <option value="90d">Last 90 days</option>
                <option value="1y">Last year</option>
              </select>
            </div>
          </div>
          
          <button
            className="mt-4 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            onClick={handleSearch}
            disabled={loading}
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </CardContent>
      </Card>

      {results.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Results ({results.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {results.map((result, index) => (
                <div key={index} className="p-3 border rounded hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-medium">{result.id || result.name}</span>
                      <span className="ml-2 text-sm text-muted-foreground">
                        {result.type}
                      </span>
                    </div>
                    {result.risk_score && (
                      <span className={`px-2 py-1 rounded text-xs ${
                        result.risk_score > 0.7 ? 'bg-red-100 text-red-800' :
                        result.risk_score > 0.4 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        Risk: {(result.risk_score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="text-center text-muted-foreground py-12">
          Enter search criteria and click Search to find transactions
        </div>
      )}
    </div>
  );
}