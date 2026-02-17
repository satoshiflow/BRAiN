/**
 * BRAiN Auth API Route
 * 
 * SECURITY:
 * - Only POST requests accepted for authentication
 * - CSRF protection enabled
 * - Rate limiting via middleware
 * - bcrypt password verification
 */

import { handlers } from "@/auth";

// Export only the handlers from NextAuth
// GET is allowed for OAuth callbacks
// POST is allowed for credentials login
export const { GET, POST } = handlers;
