/**
 * Password hashing and verification utilities
 * Uses bcryptjs for secure password handling
 */

import bcrypt from 'bcryptjs';

const SALT_ROUNDS = 12; // Industry standard: 10-12 rounds
const BCRYPT_HASH_PREFIX = '$2b$'; // bcrypt hash identifier

/**
 * Hash a plain text password using bcrypt
 * @param password - Plain text password
 * @returns Hashed password string
 */
export async function hashPassword(password: string): Promise<string> {
  if (!password || password.length < 8) {
    throw new Error('Password must be at least 8 characters long');
  }
  
  const salt = await bcrypt.genSalt(SALT_ROUNDS);
  const hash = await bcrypt.hash(password, salt);
  return hash;
}

/**
 * Verify a plain text password against a hashed password
 * @param password - Plain text password to verify
 * @param hash - Stored hashed password
 * @returns Boolean indicating if password matches
 */
export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  if (!password || !hash) {
    return false;
  }
  
  return bcrypt.compare(password, hash);
}

/**
 * Check if a password is already hashed (bcrypt format)
 * @param password - String to check
 * @returns Boolean indicating if already hashed
 */
export function isPasswordHashed(password: string): boolean {
  if (!password) return false;
  return password.startsWith(BCRYPT_HASH_PREFIX);
}

/**
 * Upgrade path: Hash a plaintext password if not already hashed
 * Use this during login to migrate legacy plaintext passwords
 * @param password - Password string (hashed or plaintext)
 * @param plainPassword - Plain text password entered by user
 * @returns Object with isValid, needsRehash, and newHash
 */
export async function upgradePassword(
  password: string, 
  plainPassword: string
): Promise<{ 
  isValid: boolean; 
  needsRehash: boolean; 
  newHash?: string 
}> {
  // Check if already hashed
  if (isPasswordHashed(password)) {
    const isValid = await verifyPassword(plainPassword, password);
    return { isValid, needsRehash: false };
  }
  
  // Legacy plaintext password - verify directly and rehash
  const isValid = password === plainPassword;
  
  if (isValid) {
    const newHash = await hashPassword(plainPassword);
    return { isValid, needsRehash: true, newHash };
  }
  
  return { isValid: false, needsRehash: false };
}

export default {
  hashPassword,
  verifyPassword,
  isPasswordHashed,
  upgradePassword,
};
