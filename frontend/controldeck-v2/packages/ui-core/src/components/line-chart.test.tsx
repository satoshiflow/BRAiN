import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LineChart, Sparkline } from './line-chart';

const mockData = [
  { timestamp: '2024-02-21T10:00:00Z', value: 10 },
  { timestamp: '2024-02-21T10:05:00Z', value: 25 },
  { timestamp: '2024-02-21T10:10:00Z', value: 15 },
  { timestamp: '2024-02-21T10:15:00Z', value: 30 },
  { timestamp: '2024-02-21T10:20:00Z', value: 20 },
];

describe('LineChart', () => {
  it('renders with title', () => {
    render(<LineChart data={mockData} title="CPU Usage" />);
    expect(screen.getByText('CPU Usage')).toBeInTheDocument();
  });

  it('renders without title', () => {
    const { container } = render(<LineChart data={mockData} />);
    expect(container.querySelector('.recharts-responsive-container')).toBeInTheDocument();
  });

  it('renders with different heights', () => {
    const { rerender } = render(<LineChart data={mockData} height={100} />);
    expect(document.querySelector('.recharts-wrapper')).toBeInTheDocument();
    
    rerender(<LineChart data={mockData} height={300} />);
    expect(document.querySelector('.recharts-wrapper')).toBeInTheDocument();
  });

  it('renders with showDots', () => {
    render(<LineChart data={mockData} showDots />);
    // Dots would be rendered in the SVG
    expect(document.querySelector('.recharts-line')).toBeInTheDocument();
  });

  it('renders with custom formatters', () => {
    render(
      <LineChart 
        data={mockData} 
        formatYAxis={(v) => `${v}%`}
        formatTooltip={(v) => `${v} percent`}
      />
    );
    expect(document.querySelector('.recharts-wrapper')).toBeInTheDocument();
  });
});

describe('Sparkline', () => {
  it('renders sparkline with data', () => {
    const data = [10, 25, 15, 30, 20];
    render(<Sparkline data={data} />);
    expect(document.querySelector('.recharts-wrapper')).toBeInTheDocument();
  });

  it('renders with different colors', () => {
    const data = [10, 25, 15];
    const { rerender } = render(<Sparkline data={data} color="success" />);
    expect(document.querySelector('.recharts-wrapper')).toBeInTheDocument();
    
    rerender(<Sparkline data={data} color="danger" />);
    expect(document.querySelector('.recharts-wrapper')).toBeInTheDocument();
  });
});