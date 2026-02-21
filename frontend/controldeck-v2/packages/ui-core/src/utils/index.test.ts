import { describe, it, expect } from 'vitest';
import { cn, formatDate, formatRelativeTime, truncate, generateId } from './index';

describe('cn (className merge)', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    expect(cn('foo', true && 'bar', false && 'baz')).toBe('foo bar');
  });

  it('handles tailwind conflicts', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4');
  });

  it('handles undefined and null', () => {
    expect(cn('foo', undefined, null, 'bar')).toBe('foo bar');
  });
});

describe('formatDate', () => {
  it('formats date to German locale', () => {
    const date = new Date('2024-02-21T14:30:00');
    const formatted = formatDate(date);
    expect(formatted).toContain('21.02.2024');
    expect(formatted).toContain('14:30');
  });

  it('handles string dates', () => {
    const formatted = formatDate('2024-02-21T14:30:00');
    expect(formatted).toContain('21.02.2024');
  });
});

describe('formatRelativeTime', () => {
  it('returns "gerade eben" for recent times', () => {
    const now = new Date();
    expect(formatRelativeTime(now)).toBe('gerade eben');
  });

  it('returns minutes for times within hour', () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
    expect(formatRelativeTime(fiveMinutesAgo)).toBe('5 Min.');
  });

  it('returns hours for times within day', () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000);
    expect(formatRelativeTime(twoHoursAgo)).toBe('2 Std.');
  });

  it('returns days for older times', () => {
    const twoDaysAgo = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000);
    expect(formatRelativeTime(twoDaysAgo)).toBe('2 Tage');
  });
});

describe('truncate', () => {
  it('returns original string if within limit', () => {
    expect(truncate('hello', 10)).toBe('hello');
  });

  it('truncates long strings with ellipsis', () => {
    expect(truncate('hello world', 8)).toBe('hello...');
  });

  it('handles exact length', () => {
    expect(truncate('hello', 5)).toBe('hello');
  });
});

describe('generateId', () => {
  it('generates a string', () => {
    const id = generateId();
    expect(typeof id).toBe('string');
  });

  it('generates unique ids', () => {
    const id1 = generateId();
    const id2 = generateId();
    expect(id1).not.toBe(id2);
  });

  it('generates ids of expected length', () => {
    const id = generateId();
    expect(id.length).toBe(7);
  });
});