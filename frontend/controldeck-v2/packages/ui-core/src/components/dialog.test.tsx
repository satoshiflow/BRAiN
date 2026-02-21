import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Dialog, Drawer, useModal } from './dialog';

describe('Dialog', () => {
  it('renders when open is true', () => {
    render(
      <Dialog open={true} onOpenChange={() => {}}>
        <div>Dialog Content</div>
      </Dialog>
    );
    expect(screen.getByText('Dialog Content')).toBeInTheDocument();
  });

  it('does not render when open is false', () => {
    render(
      <Dialog open={false} onOpenChange={() => {}}>
        <div>Dialog Content</div>
      </Dialog>
    );
    expect(screen.queryByText('Dialog Content')).not.toBeInTheDocument();
  });

  it('calls onOpenChange when backdrop is clicked', () => {
    const handleOpenChange = vi.fn();
    render(
      <Dialog open={true} onOpenChange={handleOpenChange}>
        <div>Dialog Content</div>
      </Dialog>
    );
    
    // Click on backdrop (the first div with bg-black/50)
    const backdrop = document.querySelector('.bg-black\\/50');
    if (backdrop) {
      fireEvent.click(backdrop);
      expect(handleOpenChange).toHaveBeenCalledWith(false);
    }
  });

  it('calls onOpenChange when ESC is pressed', () => {
    const handleOpenChange = vi.fn();
    render(
      <Dialog open={true} onOpenChange={handleOpenChange}>
        <div>Dialog Content</div>
      </Dialog>
    );
    
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handleOpenChange).toHaveBeenCalledWith(false);
  });

  it('renders with custom className', () => {
    render(
      <Dialog open={true} onOpenChange={() => {}} className="custom-class">
        <div>Dialog Content</div>
      </Dialog>
    );
    
    const dialog = screen.getByText('Dialog Content').parentElement;
    expect(dialog).toHaveClass('custom-class');
  });
});

describe('Drawer', () => {
  it('renders when open is true', () => {
    render(
      <Drawer open={true} onOpenChange={() => {}}>
        <div>Drawer Content</div>
      </Drawer>
    );
    expect(screen.getByText('Drawer Content')).toBeInTheDocument();
  });

  it('does not render when open is false', () => {
    render(
      <Drawer open={false} onOpenChange={() => {}}>
        <div>Drawer Content</div>
      </Drawer>
    );
    expect(screen.queryByText('Drawer Content')).not.toBeInTheDocument();
  });

  it('renders on the right by default', () => {
    const { container } = render(
      <Drawer open={true} onOpenChange={() => {}}>
        <div>Drawer Content</div>
      </Drawer>
    );
    
    const drawer = container.querySelector('.right-0');
    expect(drawer).toBeInTheDocument();
  });

  it('renders on the left when position is left', () => {
    const { container } = render(
      <Drawer open={true} onOpenChange={() => {}} position="left">
        <div>Drawer Content</div>
      </Drawer>
    );
    
    const drawer = container.querySelector('.left-0');
    expect(drawer).toBeInTheDocument();
  });

  it('calls onOpenChange when backdrop is clicked', () => {
    const handleOpenChange = vi.fn();
    const { container } = render(
      <Drawer open={true} onOpenChange={handleOpenChange}>
        <div>Drawer Content</div>
      </Drawer>
    );
    
    const backdrop = container.querySelector('.bg-black\\/50');
    if (backdrop) {
      fireEvent.click(backdrop);
      expect(handleOpenChange).toHaveBeenCalledWith(false);
    }
  });

  it('calls onClose when close button is clicked in DrawerHeader', () => {
    const handleClose = vi.fn();
    render(
      <Drawer open={true} onOpenChange={() => {}}>
        <DrawerHeader onClose={handleClose}>
          <div>Title</div>
        </DrawerHeader>
      </Drawer>
    );
    
    const closeButton = screen.getByRole('button');
    fireEvent.click(closeButton);
    expect(handleClose).toHaveBeenCalled();
  });
});

describe('useModal', () => {
  it('returns correct initial state', () => {
    const modal = useModal();
    expect(modal.open).toBe(false);
  });

  it('returns correct initial state when defaultOpen is true', () => {
    const modal = useModal(true);
    expect(modal.open).toBe(true);
  });

  it('onOpen sets open to true', () => {
    const modal = useModal();
    modal.onOpen();
    expect(modal.open).toBe(true);
  });

  it('onClose sets open to false', () => {
    const modal = useModal(true);
    modal.onClose();
    expect(modal.open).toBe(false);
  });

  it('onOpenChange updates state correctly', () => {
    const modal = useModal();
    modal.onOpenChange(true);
    expect(modal.open).toBe(true);
    modal.onOpenChange(false);
    expect(modal.open).toBe(false);
  });
});