/**
 * BRAiN Authentication Helpers
 * 
 * Pure utility functions - NOT Server Actions
 * Can be used in middleware and client components
 */

/**
 * Role hierarchy for permission checking
 */
const roleHierarchy = {
  admin: 3,
  operator: 2,
  viewer: 1,
};

/**
 * Check if user has required role
 * Called by middleware and server components
 */
export function hasRequiredRole(
  userRole: string,
  requiredRole: "admin" | "operator" | "viewer"
): boolean {
  const userLevel = roleHierarchy[userRole as keyof typeof roleHierarchy] || 0;
  const requiredLevel = roleHierarchy[requiredRole];

  return userLevel >= requiredLevel;
}

/**
 * Check if user can access AXE UI
 * Only admin and operator roles allowed
 */
export function canAccessAxe(userRole: string): boolean {
  return userRole === "admin" || userRole === "operator";
}

/**
 * Get role level for comparison
 */
export function getRoleLevel(role: string): number {
  return roleHierarchy[role as keyof typeof roleHierarchy] || 0;
}
