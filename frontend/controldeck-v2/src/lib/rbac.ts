/**
 * RBAC - Role-Based Access Control
 * 
 * Implements role hierarchy for authorization:
 * admin (100) > operator (50) > agent (25) > user (10)
 */

export type UserRole = 'admin' | 'operator' | 'agent' | 'user';

const roleHierarchy: Record<UserRole, number> = {
  admin: 100,
  operator: 50,
  agent: 25,
  user: 10,
};

/**
 * Check if user role meets the required role level
 * Uses hierarchy: admin > operator > agent > user
 */
export function hasRole(
  sessionRole: string | undefined | null,
  required: UserRole
): boolean {
  const userLevel = roleHierarchy[sessionRole as UserRole] ?? 0;
  const requiredLevel = roleHierarchy[required] ?? 0;
  return userLevel >= requiredLevel;
}

/**
 * Check if user has admin role
 */
export function isAdmin(sessionRole: string | undefined | null): boolean {
  return hasRole(sessionRole, 'admin');
}

/**
 * Check if user has operator or higher role
 */
export function isOperator(sessionRole: string | undefined | null): boolean {
  return hasRole(sessionRole, 'operator');
}

/**
 * Get role display name
 */
export function getRoleDisplayName(role: string | undefined): string {
  const displayNames: Record<string, string> = {
    admin: 'Administrator',
    operator: 'Operator',
    agent: 'Agent',
    user: 'User',
  };
  return displayNames[role || ''] || 'Unknown';
}
