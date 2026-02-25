// DEPRECATED: Use Better Auth from @/lib/auth.ts instead
// Better Auth uses bcrypt internally for password hashing

export async function hashPassword(password: string): Promise<string> {
  throw new Error("DEPRECATED: Better Auth handles password hashing internally");
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  throw new Error("DEPRECATED: Better Auth handles password verification internally");
}

export function isPasswordHashed(password: string): boolean {
  return password.startsWith("$2");
}

export async function upgradePassword(password: string, plainPassword: string): Promise<{ isValid: boolean; needsRehash: boolean; newHash?: string }> {
  throw new Error("DEPRECATED: Use Better Auth from @/lib/auth.ts");
}
