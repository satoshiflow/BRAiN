import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HeatmapGrid, HeatmapStats } from './heatmap-grid';

const mockCells = [
  { id: '1', label: 'API', status: 'healthy' as const, value: 99 },
  { id: '2', label: 'DB', status: 'healthy' as const, value: 98 },
  { id: '3', label: 'Cache', status: 'warning' as const, value: 75 },
  { id: '4', label: 'Worker', status: 'critical' as const, value: 45 },
  { id: '5', label: 'Queue', status: 'offline' as const },
];

describe('HeatmapGrid', () => {
  it('renders cells with labels', () => {
    render(<HeatmapGrid cells={mockCells} />);
    expect(screen.getByText('API')).toBeInTheDocument();
    expect(screen.getByText('DB')).toBeInTheDocument();
    expect(screen.getByText('Cache')).toBeInTheDocument();
  });

  it('renders status badges', () => {
    render(<HeatmapGrid cells={mockCells} />);
    expect(screen.getByText('healthy')).toBeInTheDocument();
    expect(screen.getByText('warning')).toBeInTheDocument();
    expect(screen.getByText('critical')).toBeInTheDocument();
    expect(screen.getByText('offline')).toBeInTheDocument();
  });

  it('renders values when showValues is true', () => {
    render(<HeatmapGrid cells={mockCells} showValues />);
    expect(screen.getByText('99%')).toBeInTheDocument();
    expect(screen.getByText('98%')).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('hides values when showValues is false', () => {
    render(<HeatmapGrid cells={mockCells} showValues={false} />);
    expect(screen.queryByText('99%')).not.toBeInTheDocument();
  });

  it('shows empty message when no cells', () => {
    render(<HeatmapGrid cells={[]} />);
    expect(screen.getByText('No data to display')).toBeInTheDocument();
  });

  it('calls onClick when cell is clicked', () => {
    const handleClick = vi.fn();
    const cellsWithClick = [{ ...mockCells[0], onClick: handleClick }];
    render(<HeatmapGrid cells={cellsWithClick} />);
    
    screen.getByText('API').click();
    expect(handleClick).toHaveBeenCalled();
  });
});

describe('HeatmapStats', () => {
  it('renders stats summary', () => {
    render(<HeatmapStats cells={mockCells} />);
    expect(screen.getByText('Healthy: 2/5')).toBeInTheDocument();
    expect(screen.getByText('Warning: 1/5')).toBeInTheDocument();
    expect(screen.getByText('Critical: 1/5')).toBeInTheDocument();
    expect(screen.getByText('Offline: 1/5')).toBeInTheDocument();
  });
});