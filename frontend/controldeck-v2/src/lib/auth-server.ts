/**
 * Server-side authentication utilities
 * - Secure password hashing on signup
 * - Password verification on login
 * - Migration path for legacy plaintext passwords
 */

import crypto from 'crypto';
import { hashPassword, verifyPassword, upgradePassword, isPasswordHashed } from './password';
import { createSession, destroySession, getSession } from './session';

// User type definition
export interface User {
  id: string;
  email: string;
  password: string; // hashed password
  createdAt: Date;
  updatedAt: Date;
}

// In-memory user store (replace with database in production)
const userStore = new Map<string, User>();
const emailIndex = new Map<string, string>(); // email -> userId

/**
 * Sign up a new user
 * - Hashes password with bcrypt
 * - Creates user record
 * - Creates session
 */
export async function signup(
  email: string, 
  password: string
): Promise<{ userId: string; sessionId: string }> {
  // Validate input
  if (!email || !email.includes('@')) {
    throw new Error('Valid email is required');
  }
  
  if (!password || password.length < 8) {
    throw new Error('Password must be at least 8 characters');
  }
  
  // Check if user already exists
  const existingUserId = emailIndex.get(email.toLowerCase());
  if (existingUserId) {
    throw new Error('User already exists');
  }
  
  // Hash password securely
  const hashedPassword = await hashPassword(password);
  
  // Create user
  const userId = `user_${crypto.randomUUID()}`;
  const now = new Date();
  
  const user: User = {
    id: userId,
    email: email.toLowerCase(),
    password: hashedPassword,
    createdAt: now,
    updatedAt: now,
  };
  
  userStore.set(userId, user);
  emailIndex.set(email.toLowerCase(), userId);
  
  // Create session
  const sessionId = await createSession(userId);
  
  return { userId, sessionId };
}

/**
 * Login a user
 * - Verifies password
 * - Migration path: rehashes plaintext passwords on first login
 * - Creates session
 */
export async function login(
  email: string, 
  password: string,
  rememberMe = false
): Promise<{ userId: string; sessionId: string }> {
  // Find user
  const userId = emailIndex.get(email.toLowerCase());
  if (!userId) {
    throw new Error('Invalid credentials');
  }
  
  const user = userStore.get(userId);
  if (!user) {
    throw new Error('Invalid credentials');
  }
  
  // Check if password needs upgrade (legacy plaintext)
  if (!isPasswordHashed(user.password)) {
    // Legacy: plaintext password - verify and upgrade
    if (user.password !== password) {
      throw new Error('Invalid credentials');
    }
    
    // Upgrade to hashed password
    const newHash = await hashPassword(password);
    user.password = newHash;
    user.updatedAt = new Date();
    userStore.set(userId, user);
  } else {
    // Modern: verify bcrypt hash
    const isValid = await verifyPassword(password, user.password);
    if (!isValid) {
      throw new Error('Invalid credentials');
    }
  }
  
  // Create session
  const sessionId = await createSession(userId, rememberMe);
  
  return { userId, sessionId };
}

/**
 * Logout user
 */
export async function logout(): Promise<void> {
  await destroySession();
}

/**
 * Get user by ID
 */
export function getUserById(userId: string): User | null {
  return userStore.get(userId) || null;
}

/**
 * Update user password
 */
export async function updatePassword(
  userId: string, 
  newPassword: string
): Promise<void> {
  const user = userStore.get(userId);
  if (!user) {
    throw new Error('User not found');
  }
  
  if (!newPassword || newPassword.length < 8) {
    throw new Error('Password must be at least 8 characters');
  }
  
  const hashedPassword = await hashPassword(newPassword);
  user.password = hashedPassword;
  user.updatedAt = new Date();
  userStore.set(userId, user);
}

/**
 * Delete user account
 */
export function deleteUser(userId: string): void {
  const user = userStore.get(userId);
  if (user) {
    emailIndex.delete(user.email.toLowerCase());
    userStore.delete(userId);
  }
}

// Re-export from session for convenience
export { requireUser, getSession } from './session';

/**
 * Check if user is authenticated
 * Returns true if valid session exists, false otherwise
 */
export async function isUserAuthenticated(): Promise<boolean> {
  const session = await getSession();
  return session !== null;
}
