import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Sidebar } from './sidebar';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  usePathname: () => '/missions',
}));

describe('Sidebar', () => {
  it('renders navigation items', () => {
    render(<Sidebar />);
    
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Missions')).toBeInTheDocument();
    expect(screen.getByText('Events')).toBeInTheDocument();
    expect(screen.getByText('Agents')).toBeInTheDocument();
    expect(screen.getByText('Health')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('shows active state for current path', () => {
    render(<Sidebar />);
    
    const missionsLink = screen.getByText('Missions').closest('a');
    expect(missionsLink).toHaveClass('border-l-2', 'border-primary');
  });

  it('renders BRAiN logo', () => {
    render(<Sidebar />);
    expect(screen.getByText('BRAiN')).toBeInTheDocument();
  });

  it('renders navigation groups', () => {
    render(<Sidebar />);
    
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Operations')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();
  });
});