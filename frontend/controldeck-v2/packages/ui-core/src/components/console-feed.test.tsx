import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConsoleFeed } from './console-feed';

const mockEvents = [
  {
    id: '1',
    timestamp: '2024-02-21T10:30:00Z',
    message: 'System started',
    severity: 'info' as const,
    source: 'system',
  },
  {
    id: '2',
    timestamp: '2024-02-21T10:31:00Z',
    message: 'Warning: High memory usage',
    severity: 'warning' as const,
    source: 'monitor',
  },
  {
    id: '3',
    timestamp: '2024-02-21T10:32:00Z',
    message: 'Error: Connection failed',
    severity: 'error' as const,
    source: 'api',
  },
];

describe('ConsoleFeed', () => {
  it('renders console header', () => {
    render(<ConsoleFeed events={mockEvents} />);
    expect(screen.getByText('Console')).toBeInTheDocument();
  });

  it('renders events with timestamps', () => {
    render(<ConsoleFeed events={mockEvents} />);
    expect(screen.getByText('System started')).toBeInTheDocument();
    expect(screen.getByText('Warning: High memory usage')).toBeInTheDocument();
    expect(screen.getByText('Error: Connection failed')).toBeInTheDocument();
  });

  it('renders severity prefixes', () => {
    render(<ConsoleFeed events={mockEvents} />);
    expect(screen.getByText('[INFO]')).toBeInTheDocument();
    expect(screen.getByText('[WARN]')).toBeInTheDocument();
    expect(screen.getByText('[ERROR]')).toBeInTheDocument();
  });

  it('renders source tags', () => {
    render(<ConsoleFeed events={mockEvents} />);
    expect(screen.getByText('[system]')).toBeInTheDocument();
    expect(screen.getByText('[monitor]')).toBeInTheDocument();
    expect(screen.getByText('[api]')).toBeInTheDocument();
  });

  it('shows LIVE badge when autoScroll is true', () => {
    render(<ConsoleFeed events={mockEvents} autoScroll />);
    expect(screen.getByText('LIVE')).toBeInTheDocument();
  });

  it('shows empty message when no events', () => {
    render(<ConsoleFeed events={[]} emptyMessage="No logs available" />);
    expect(screen.getByText('No logs available')).toBeInTheDocument();
  });

  it('shows line count', () => {
    render(<ConsoleFeed events={mockEvents} />);
    expect(screen.getByText('3 lines')).toBeInTheDocument();
  });

  it('applies correct severity colors', () => {
    const { container } = render(<ConsoleFeed events={mockEvents} />);
    const infoElement = screen.getByText('[INFO]');
    const warnElement = screen.getByText('[WARN]');
    const errorElement = screen.getByText('[ERROR]');
    
    expect(infoElement).toHaveClass('text-info');
    expect(warnElement).toHaveClass('text-warning');
    expect(errorElement).toHaveClass('text-danger');
  });

  it('filters events by severity', () => {
    render(<ConsoleFeed events={mockEvents} filter="error" />);
    expect(screen.getByText('Error: Connection failed')).toBeInTheDocument();
    expect(screen.queryByText('System started')).not.toBeInTheDocument();
    expect(screen.queryByText('Warning: High memory usage')).not.toBeInTheDocument();
  });
});