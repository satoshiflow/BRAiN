import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PageContainer, PageHeader, Grid } from './page-layout';

describe('PageContainer', () => {
  it('renders children', () => {
    render(
      <PageContainer>
        <div data-testid="content">Page Content</div>
      </PageContainer>
    );
    
    expect(screen.getByTestId('content')).toBeInTheDocument();
  });

  it('renders as main element', () => {
    render(<PageContainer>Content</PageContainer>);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});

describe('PageHeader', () => {
  it('renders title and description', () => {
    render(
      <PageHeader 
        title="Missions" 
        description="Manage missions" 
      />
    );
    
    expect(screen.getByRole('heading', { name: 'Missions' })).toBeInTheDocument();
    expect(screen.getByText('Manage missions')).toBeInTheDocument();
  });

  it('renders only h1 per page (accessibility)', () => {
    render(<PageHeader title="Dashboard" />);
    
    const headings = screen.getAllByRole('heading', { level: 1 });
    expect(headings).toHaveLength(1);
  });

  it('renders actions', () => {
    render(
      <PageHeader 
        title="Missions"
        actions={<button>New Mission</button>}
      />
    );
    
    expect(screen.getByRole('button', { name: 'New Mission' })).toBeInTheDocument();
  });
});

describe('Grid', () => {
  it('renders with 4 columns by default', () => {
    const { container } = render(
      <Grid>
        <div>Item 1</div>
        <div>Item 2</div>
      </Grid>
    );
    
    expect(container.firstChild).toHaveClass('lg:grid-cols-4');
  });

  it('renders with specified columns', () => {
    const { container } = render(
      <Grid cols={2}>
        <div>Item 1</div>
        <div>Item 2</div>
      </Grid>
    );
    
    expect(container.firstChild).toHaveClass('sm:grid-cols-2');
  });

  it('renders children', () => {
    render(
      <Grid>
        <div data-testid="item-1">Item 1</div>
        <div data-testid="item-2">Item 2</div>
      </Grid>
    );
    
    expect(screen.getByTestId('item-1')).toBeInTheDocument();
    expect(screen.getByTestId('item-2')).toBeInTheDocument();
  });
});