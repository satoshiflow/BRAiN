/**
 * Admin Users API - GET /api/admin/users
 * 
 * Lists all users (admin only)
 * 
 * SECURITY:
 * - Admin authentication required
 * - No sensitive data exposed
 * - Pagination support
 */

import { auth } from "@/auth";
import { NextResponse } from "next/server";
import { hasRequiredRole } from "@/lib/auth-helpers";

// In-memory user store (replace with database in production)
const USERS = [
  {
    id: "usr_001",
    email: "admin@falklabs.io",
    name: "System Administrator",
    role: "admin",
    groups: ["brain:admin", "brain:operators", "brain:viewers"],
    createdAt: "2025-01-01T00:00:00Z",
    lastLogin: "2025-02-13T06:00:00Z",
    status: "active",
  },
  {
    id: "usr_002",
    email: "operator@falklabs.io",
    name: "Operations User",
    role: "operator",
    groups: ["brain:operators", "brain:viewers"],
    createdAt: "2025-01-15T00:00:00Z",
    lastLogin: "2025-02-12T18:00:00Z",
    status: "active",
  },
  {
    id: "usr_003",
    email: "viewer@falklabs.io",
    name: "View Only User",
    role: "viewer",
    groups: ["brain:viewers"],
    createdAt: "2025-01-20T00:00:00Z",
    lastLogin: null,
    status: "inactive",
  },
];

export async function GET(request: Request) {
  try {
    // Check authentication
    const session = await auth();
    if (!session?.user) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    // Check admin role
    if (!hasRequiredRole(session.user.role || "", "admin")) {
      return NextResponse.json(
        { error: "Forbidden: Admin access required" },
        { status: 403 }
      );
    }

    // Get query parameters
    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get("page") || "1");
    const limit = parseInt(searchParams.get("limit") || "20");
    const role = searchParams.get("role");
    const status = searchParams.get("status");
    const search = searchParams.get("search");

    // Filter users
    let filteredUsers = [...USERS];

    if (role) {
      filteredUsers = filteredUsers.filter(u => u.role === role);
    }

    if (status) {
      filteredUsers = filteredUsers.filter(u => u.status === status);
    }

    if (search) {
      const searchLower = search.toLowerCase();
      filteredUsers = filteredUsers.filter(u =>
        u.email.toLowerCase().includes(searchLower) ||
        u.name.toLowerCase().includes(searchLower)
      );
    }

    // Pagination
    const total = filteredUsers.length;
    const startIndex = (page - 1) * limit;
    const endIndex = startIndex + limit;
    const paginatedUsers = filteredUsers.slice(startIndex, endIndex);

    // Remove sensitive data (passwordHash is not in this object, but good practice)
    const safeUsers = paginatedUsers.map(({ ...user }) => user);

    return NextResponse.json({
      users: safeUsers,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    });
  } catch (error) {
    console.error("[Admin API] Error fetching users:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
