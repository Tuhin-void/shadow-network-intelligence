/**
 * Shadow Network Intelligence - Risk Radar Chart
 * Displays risk dimensions as a radar/spider chart
 */
import React from 'react';

export function RiskRadar() {
  const dimensions = [
    { name: 'Transaction Risk', value: 0.75 },
    { name: 'Network Risk', value: 0.82 },
    { name: 'Behavioral Risk', value: 0.65 },
    { name: 'Geographic Risk', value: 0.88 },
    { name: 'Entity Risk', value: 0.70 },
  ];

  const size = 300;
  const center = size / 2;
  const maxRadius = size / 2 - 40;

  const getPoint = (angle: number, value: number) => {
    const radians = (angle - 90) * (Math.PI / 180);
    return {
      x: center + maxRadius * value * Math.cos(radians),
      y: center + maxRadius * value * Math.sin(radians),
    };
  };

  const getLabelPoint = (angle: number) => {
    const radians = (angle - 90) * (Math.PI / 180);
    return {
      x: center + (maxRadius + 25) * Math.cos(radians),
      y: center + (maxRadius + 25) * Math.sin(radians),
    };
  };

  const angles = dimensions.map((_, i) => (360 / dimensions.length) * i);
  const points = dimensions.map((d, i) => getPoint(angles[i], d.value));

  return (
    <div className="flex justify-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background circles */}
        {[0.25, 0.5, 0.75, 1].map((scale) => (
          <circle
            key={scale}
            cx={center}
            cy={center}
            r={maxRadius * scale}
            fill="none"
            stroke="currentColor"
            strokeOpacity={0.1}
            strokeWidth={1}
          />
        ))}

        {/* Axis lines */}
        {angles.map((angle, i) => {
          const point = getPoint(angle, 1);
          return (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={point.x}
              y2={point.y}
              stroke="currentColor"
              strokeOpacity={0.2}
              strokeWidth={1}
            />
          );
        })}

        {/* Data polygon */}
        <polygon
          points={points.map((p) => `${p.x},${p.y}`).join(' ')}
          fill="rgba(59, 130, 246, 0.3)"
          stroke="rgb(59, 130, 246)"
          strokeWidth={2}
        />

        {/* Data points */}
        {points.map((point, i) => (
          <circle
            key={i}
            cx={point.x}
            cy={point.y}
            r={5}
            fill="rgb(59, 130, 246)"
          />
        ))}

        {/* Labels */}
        {dimensions.map((dim, i) => {
          const labelPoint = getLabelPoint(angles[i]);
          return (
            <text
              key={i}
              x={labelPoint.x}
              y={labelPoint.y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-xs fill-current text-muted-foreground"
            >
              {dim.name}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
