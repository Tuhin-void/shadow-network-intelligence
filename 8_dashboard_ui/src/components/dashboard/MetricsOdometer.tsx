/**
 * Shadow Network Intelligence - Metrics Odometer
 * Animated metrics display component
 */
import React, { useState, useEffect } from 'react';

interface MetricsOdometerProps {
  value: number;
  suffix?: string;
  highlight?: boolean;
  alert?: boolean;
}

export function MetricsOdometer({ 
  value, 
  suffix = '', 
  highlight = false,
  alert = false 
}: MetricsOdometerProps) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const duration = 1000;
    const steps = 30;
    const increment = value / steps;
    let current = 0;

    const timer = setInterval(() => {
      current += increment;
      if (current >= value) {
        setDisplayValue(value);
        clearInterval(timer);
      } else {
        setDisplayValue(Math.floor(current));
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [value]);

  const colorClass = alert 
    ? 'text-red-600' 
    : highlight 
      ? 'text-blue-600' 
      : 'text-foreground';

  return (
    <div className={`text-4xl font-bold font-mono ${colorClass}`}>
      {displayValue.toLocaleString()}{suffix}
    </div>
  );
}
