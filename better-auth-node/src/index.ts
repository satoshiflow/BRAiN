import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { toNodeHandler } from "better-auth/node";
import { auth } from "./auth";

// Load environment variables
dotenv.config();

const app = express();
const PORT = parseInt(process.env.PORT || "3000", 10);
const NODE_ENV = process.env.NODE_ENV || "development";

// CORS Configuration
const corsOptions = {
  origin: process.env.TRUSTED_ORIGINS?.split(",") || [
    "https://control.brain.falklabs.de",
    "https://axe.brain.falklabs.de",
    "https://api.brain.falklabs.de",
    "http://localhost:3000",
    "http://localhost:3456"
  ],
  credentials: true,
  methods: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization", "X-Requested-With"],
};

app.use(cors(corsOptions));

// Body parsing middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Better Auth Handler - alle Auth Endpoints
app.all("/api/auth/*", toNodeHandler(auth));

// Health Check Endpoint
app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    service: "better-auth",
    timestamp: new Date().toISOString(),
    environment: NODE_ENV,
  });
});

// Root Endpoint
app.get("/", (req, res) => {
  res.json({
    service: "Better Auth",
    version: "1.0.0",
    status: "running",
    endpoints: {
      auth: "/api/auth/*",
      health: "/health",
    },
  });
});

// Error Handling
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error("Error:", err);
  res.status(500).json({
    error: "Internal Server Error",
    message: NODE_ENV === "development" ? err.message : "Something went wrong",
  });
});

// Start Server
app.listen(PORT, "0.0.0.0", () => {
  console.log(`🚀 Better Auth Service running on port ${PORT}`);
  console.log(`📍 Environment: ${NODE_ENV}`);
  console.log(`🔒 Trusted Origins: ${corsOptions.origin.join(", ")}`);
  console.log(`💾 Database: ${process.env.DATABASE_URL ? "Configured" : "Not configured"}`);
});

export default app;