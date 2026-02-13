"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function Dashboard() {
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await fetch("/api/auth/session");
        const data = await res.json();
        
        if (data?.user) {
          setSession(data);
        } else {
          // Nicht eingeloggt
          router.push("/auth/signin");
        }
      } catch {
        router.push("/auth/signin");
      } finally {
        setLoading(false);
      }
    };
    
    checkAuth();
  }, [router]);

  const handleSignOut = async () => {
    await fetch("/api/auth/signout", { method: "POST" });
    window.location.href = "/auth/signin";
  };

  if (loading) {
    return (
      <div style={{ 
        minHeight: "100vh", 
        display: "flex", 
        alignItems: "center", 
        justifyContent: "center",
        background: "#0a0a0f",
        color: "#fff",
        fontFamily: "Arial, sans-serif"
      }}>
        <div>Loading BRAiN...</div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  return (
    <div style={{ 
      minHeight: "100vh", 
      background: "#0a0a0f", 
      color: "#fff", 
      fontFamily: "Arial, sans-serif" 
    }}>
      <nav style={{ 
        background: "#1a1a2e", 
        padding: "15px 30px", 
        display: "flex", 
        justifyContent: "space-between",
        alignItems: "center",
        borderBottom: "1px solid #333"
      }}>
        <h1 style={{ color: "#00d4ff", margin: 0 }}>🧠 BRAiN Control Deck</h1>
        <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
          <span style={{ color: "#aaa" }}>{session.user?.email}</span>
          <button
            onClick={handleSignOut}
            style={{
              padding: "8px 16px",
              background: "#ff4444",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer"
            }}
          >
            Sign Out
          </button>
        </div>
      </nav>

      <main style={{ padding: "30px" }}>
        <h2 style={{ color: "#00d4ff" }}>Dashboard</h2>
        <p style={{ color: "#888" }}>Welcome to BRAiN v0.3.0</p>
        
        <div style={{ 
          display: "grid", 
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: "20px",
          marginTop: "30px"
        }}>
          <div style={{ background: "#1a1a2e", padding: "20px", borderRadius: "8px" }}>
            <h3 style={{ color: "#00d4ff", marginTop: 0 }}>🔗 Backend Status</h3>
            <p><a href="http://127.0.0.1:8001/api/health" target="_blank" style={{ color: "#4caf50" }}>✅ Running</a></p>
            <p style={{ fontSize: "14px", color: "#666" }}>Health endpoint active</p>
          </div>

          <div style={{ background: "#1a1a2e", padding: "20px", borderRadius: "8px" }}>
            <h3 style={{ color: "#00d4ff", marginTop: 0 }}>📚 API Documentation</h3>
            <p><a href="http://127.0.0.1:8001/docs" target="_blank" style={{ color: "#00d4ff" }}>Open Swagger UI</a></p>
            <p style={{ fontSize: "14px", color: "#666" }}>Interactive API docs</p>
          </div>

          <div style={{ background: "#1a1a2e", padding: "20px", borderRadius: "8px" }}>
            <h3 style={{ color: "#00d4ff", marginTop: 0 }}>👤 Session Info</h3>
            <p style={{ fontSize: "14px", color: "#aaa" }}>
              User: {session.user?.name}<br/>
              Email: {session.user?.email}<br/>
              Groups: {session.user?.groups?.join(", ") || "operator"}
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
