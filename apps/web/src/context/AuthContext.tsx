"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import type { User, Session } from "@supabase/supabase-js";
import { createClient } from "../lib/supabase/client";

export interface AuthContextType {
  user: User | null;
  session: Session | null;
  accessToken: string | null;
  loading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const supabase = createClient();

    // 1. Initial Session Retrieval
    const initializeAuth = async () => {
      try {
        const { data, error } = await supabase.auth.getSession();
        if (error) {
          console.error("Error retrieving Supabase session:", error.message);
        } else if (data.session) {
          setSession(data.session);
          setUser(data.session.user);
          setAccessToken(data.session.access_token);
        }
      } catch (err) {
        console.error("Unexpected error retrieving initial session:", err);
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();

    // 2. Real-Time Auth State Subscription
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, currentSession) => {
      setSession(currentSession);
      setUser(currentSession?.user ?? null);
      setAccessToken(currentSession?.access_token ?? null);
      setLoading(false);
    });

    // 3. Listener Cleanup on Unmount
    return () => {
      subscription.unsubscribe();
    };
  }, []);

  // 4. Sign Out Method
  const signOut = async () => {
    const supabase = createClient();
    try {
      await supabase.auth.signOut();
    } catch (err) {
      console.error("Error during signOut:", err);
    } finally {
      setUser(null);
      setSession(null);
      setAccessToken(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        accessToken,
        loading,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
