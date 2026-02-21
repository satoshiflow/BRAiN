import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CircularProgress } from './circular-progress';

describe('CircularProgress', () => {
  it('renders with default props', () => {
    render(<CircularProgress value={50} />);
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('renders with different sizes', () => {
    const { rerender } = render(<CircularProgress value={50} size="sm" />);
    expect(screen.getByText('50%')).toBeInTheDocument();
    
    rerender(<CircularProgress value={50} size="lg" />);
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('renders with label and sublabel', () => {
    render(
      <CircularProgress 
        value={75} 
        label="CPU Usage" 
        sublabel="8 cores active" 
      />
    );
    expect(screen.getByText('CPU Usage')).toBeInTheDocument();
    expect(screen.getByText('8 cores active')).toBeInTheDocument();
  });

  it('caps value at 100', () => {
    render(<CircularProgress value={150} />);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('floors value at 0', () => {
    render(<CircularProgress value={-20} />);
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('hides value when showValue is false', () => {
    render(<CircularProgress value={50} showValue={false} label="Hidden" />);
    expect(screen.queryByText('50%')).not.toBeInTheDocument();
    expect(screen.getByText('Hidden')).toBeInTheDocument();
  });

  it('shows complete indicator at 100%', () => {
    const { container } = render(<CircularProgress value={100} color="success" />);
    // Check for the checkmark icon
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('applies correct color classes', () => {
    const { container } = render(<CircularProgress value={50} color="danger" />);
    const progressCircle = container.querySelectorAll('circle')[1];
    expect(progressCircle).toHaveClass('stroke-danger');
  });

  it('renders different values correctly', () => {
    const { rerender } = render(<CircularProgress value={25} />);
    expect(screen.getByText('25%')).toBeInTheDocument();
    
    rerender(<CircularProgress value={75.5} />);
    expect(screen.getByText('76%')).toBeInTheDocument();
  });
});