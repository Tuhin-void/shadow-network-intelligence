/**
 * Shadow Network Intelligence - Badge Component
 * Status badges and labels
 */
import React from 'react';

interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant = 'default', children, className = '' }: BadgeProps) {
  const variantClasses = {
    default: 'bg-gray-100 text-gray-800',
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    danger: 'bg-red-100 text-red-800',
    info: 'bg-blue-100 text-blue-800'
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${variantClasses[variant]} ${className}`}>
      {children}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const variant = severity === 'CRITICAL' ? 'danger' : 
                 severity === 'HIGH' ? 'warning' :
                 severity === 'MEDIUM' ? 'info' : 'default';
  
  return <Badge variant={variant}>{severity}</Badge>;
}