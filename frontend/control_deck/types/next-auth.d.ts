import { DefaultSession } from "next-auth";
import { JWT } from "next-auth/jwt";

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    idToken?: string;
    provider?: string;
    user: {
      id: string;
      groups?: string[];
    } & DefaultSession["user"];
  }

  interface User {
    groups?: string[];
  }

  interface Profile {
    groups?: string[];
    sub?: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    idToken?: string;
    provider?: string;
    groups?: string[];
  }
}
