import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { KpiCard } from './kpi-card';

describe('KpiCard', () => {
  it('renders title and value', () => {
    render(<KpiCard title="Test KPI" value={42} />);
    expect(screen.getByText('Test KPI')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('renders with positive delta', () => {
    render(
      <KpiCard 
        title="Revenue" 
        value="€1,000" 
        delta={{ value: 10, label: 'vs last month' }}
        status="positive"
      />
    );
    expect(screen.getByText('10%')).toBeInTheDocument();
    expect(screen.getByText('vs last month')).toBeInTheDocument();
  });

  it('renders with negative delta', () => {
    render(
      <KpiCard 
        title="Loss" 
        value="€500" 
        delta={{ value: -5 }}
        status="negative"
      />
    );
    expect(screen.getByText('5%')).toBeInTheDocument();
  });

  it('shows skeleton when loading', () => {
    render(<KpiCard title="Loading" value={0} loading />);
    expect(screen.queryByText('0')).not.toBeInTheDocument();
    // Skeleton should have animate-pulse class
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    render(
      <KpiCard 
        title="With Icon" 
        value={100}
        icon={<span data-testid="icon">📊</span>}
      />
    );
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });
});