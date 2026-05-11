import { useState, useCallback } from 'react';

const API_BASE = '/api/v1';

interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

export function useApi<T = any>() {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: false,
    error: null
  });

  const request = useCallback(async (url: string, options?: RequestInit) => {
    setState({ data: null, loading: true, error: null });

    try {
      const response = await fetch(`${API_BASE}${url}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      setState({ data, loading: false, error: null });
      return data;
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Unknown error');
      setState({ data: null, loading: false, error: err });
      throw err;
    }
  }, []);

  return { ...state, request };
}

export function useAlerts() {
  const api = useApi();
  
  return {
    ...api,
    fetchAlerts: async (status = 'open') => {
      return api.request(`/alerts?status=${status}`);
    }
  };
}

export function useInvestigations() {
  const api = useApi();
  
  return {
    ...api,
    investigate: async (query: string, entityId?: string) => {
      return api.request('/investigate', {
        method: 'POST',
        body: JSON.stringify({ query, entity_id: entityId })
      });
    },
    getInvestigation: async (id: string) => {
      return api.request(`/investigate/${id}`);
    }
  };
}

export function useReports() {
  const api = useApi();
  
  return {
    ...api,
    generateSAR: async (investigationId: string, format = 'json') => {
      return api.request('/reports/sar', {
        method: 'POST',
        body: JSON.stringify({ investigation_id: investigationId, format })
      });
    }
  };
}

export function useMetrics() {
  const api = useApi();
  
  return {
    ...api,
    fetchMetrics: async () => {
      return api.request('/metrics');
    }
  };
}
