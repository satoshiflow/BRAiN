import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Timeline } from './timeline';

const mockEvents = [
  {
    id: '1',
    timestamp: '2024-02-21T10:30:00Z',
    title: 'System started',
    description: 'All services initialized',
    severity: 'success' as const,
  },
  {
    id: '2',
    timestamp: '2024-02-21T10:31:00Z',
    title: 'Warning triggered',
    severity: 'warning' as const,
  },
  {
    id: '3',
    timestamp: '2024-02-21T10:32:00Z',
    title: 'Error occurred',
    description: 'Connection timeout',
    severity: 'error' as const,
  },
];

describe('Timeline', () => {
  it('renders events', () => {
    render(<Timeline events={mockEvents} />);
    expect(screen.getByText('System started')).toBeInTheDocument();
    expect(screen.getByText('Warning triggered')).toBeInTheDocument();
    expect(screen.getByText('Error occurred')).toBeInTheDocument();
  });

  it('renders descriptions', () => {
    render(<Timeline events={mockEvents} />);
    expect(screen.getByText('All services initialized')).toBeInTheDocument();
    expect(screen.getByText('Connection timeout')).toBeInTheDocument();
  });

  it('renders severity badges', () => {
    render(<Timeline events={mockEvents} />);
    expect(screen.getByText('success')).toBeInTheDocument();
    expect(screen.getByText('warning')).toBeInTheDocument();
    expect(screen.getByText('error')).toBeInTheDocument();
  });

  it('renders timestamps', () => {
    render(<Timeline events={mockEvents} />);
    expect(screen.getByText('11:30')).toBeInTheDocument();
    expect(screen.getByText('11:31')).toBeInTheDocument();
    expect(screen.getByText('11:32')).toBeInTheDocument();
  });

  it('groups by day when groupBy is day', () => {
    render(<Timeline events={mockEvents} groupBy="day" />);
    expect(screen.getByText('21.02.2024')).toBeInTheDocument();
  });

  it('shows empty message when no events', () => {
    render(<Timeline events={[]} />);
    expect(screen.getByText('No events to display')).toBeInTheDocument();
  });

  it('renders with custom icons', () => {
    const eventsWithIcons = [
      {
        ...mockEvents[0],
        icon: '🚀',
      },
    ];
    render(<Timeline events={eventsWithIcons} />);
    expect(screen.getByText('🚀')).toBeInTheDocument();
  });
});