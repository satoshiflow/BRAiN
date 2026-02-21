import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusPill } from './status-pill';

describe('StatusPill', () => {
  it('renders live status with pulse', () => {
    render(<StatusPill status="live" pulse>LIVE</StatusPill>);
    expect(screen.getByText('LIVE')).toBeInTheDocument();
    expect(document.querySelector('.animate-ping')).toBeInTheDocument();
  });

  it('renders degraded status', () => {
    render(<StatusPill status="degraded">Degraded</StatusPill>);
    expect(screen.getByText('Degraded')).toBeInTheDocument();
  });

  it('renders down status', () => {
    render(<StatusPill status="down">Down</StatusPill>);
    expect(screen.getByText('Down')).toBeInTheDocument();
  });

  it('renders safe status', () => {
    render(<StatusPill status="safe">Safe</StatusPill>);
    expect(screen.getByText('Safe')).toBeInTheDocument();
  });

  it('renders idle status', () => {
    render(<StatusPill status="idle">Idle</StatusPill>);
    expect(screen.getByText('Idle')).toBeInTheDocument();
  });

  it('has correct color classes for live status', () => {
    render(<StatusPill status="live">LIVE</StatusPill>);
    const pill = screen.getByText('LIVE').parentElement;
    expect(pill).toHaveClass('bg-success/20', 'text-success');
  });
});