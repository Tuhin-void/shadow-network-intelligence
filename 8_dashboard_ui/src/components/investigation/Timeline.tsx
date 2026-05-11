/**
 * Shadow Network Intelligence - Investigation Timeline
 * Shows investigation progress timeline
 */
import React from 'react';

export function Timeline({ events }) {
  if (!events || events.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        No timeline events yet
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />
      
      <div className="space-y-4">
        {events.map((event, index) => (
          <div key={index} className="relative pl-10">
            <div 
              className={`absolute left-2 w-4 h-4 rounded-full border-2 ${
                event.status === 'completed' 
                  ? 'bg-green-500 border-green-500' 
                  : event.status === 'active'
                  ? 'bg-blue-500 border-blue-500 animate-pulse'
                  : 'bg-gray-300 border-gray-300'
              }`}
              style={{ top: '4px' }}
            />
            
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>{event.timestamp}</span>
              <span className="font-medium text-foreground">{event.action}</span>
            </div>
            
            {event.description && (
              <p className="mt-1 text-sm">{event.description}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}