import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Topbar } from './topbar';

describe('Topbar', () => {
  it('renders title and subtitle', () => {
    render(
      <Topbar 
        title="Dashboard" 
        subtitle="System overview" 
      />
    );
    
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('System overview')).toBeInTheDocument();
  });

  it('renders without subtitle', () => {
    render(<Topbar title="Missions" />);
    
    expect(screen.getByText('Missions')).toBeInTheDocument();
    expect(screen.queryByText('System overview')).not.toBeInTheDocument();
  });

  it('renders action buttons', () => {
    render(
      <Topbar 
        title="Dashboard"
        actions={<button data-testid="custom-action">Action</button>}
      />
    );
    
    expect(screen.getByTestId('custom-action')).toBeInTheDocument();
  });

  it('renders mobile menu button', () => {
    render(<Topbar title="Dashboard" onMenuClick={() => {}} />);
    
    // Menu button should be present (hidden on lg screens via CSS)
    expect(screen.getByRole('button', { name: /menu/i })).toBeInTheDocument();
  });
});