import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Language, SessionState, CitizenProfile, HealthStatus } from '../types/index.ts';
import { fetchHealth, initSession, terminateSession, fetchProfile, updateProfile } from '../services/api';

interface SessionContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  session: SessionState;
  health: HealthStatus | null;
  profile: CitizenProfile;
  giveConsent: () => Promise<void>;
  declineConsent: () => void;
  saveProfile: (updated: Partial<CitizenProfile>) => Promise<void>;
  wipeAndEndSession: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}


const defaultProfile: CitizenProfile = {
  age: null,
  state: null,
  district: null,
  landAcres: null,
  landType: null,
  annualIncome: null,
  rationCardType: null,
  occupation: null,
  socialCategory: null,
  gender: null,
  isIncomeTaxPayer: null,
  hasPuccaHouse: null,
  ownsAgriculturalLand: null,
  hasGirlChildUnder10: null,
  hasExistingLpg: null,
  enrolledInCropInsurance: null,
  residenceType: 'RURAL',
  bisVerified: false,
  awaasPlusVerified: false,
  isConfirmed: false,
};

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export const SessionProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [language, setLanguage] = useState<Language>('hi');
  const [health, setHealth] = useState<HealthStatus | null>(null);

  // Strictly ephemeral session storage (tab-only, never unencrypted localStorage for PII)
  const [session, setSession] = useState<SessionState>(() => {
    const savedSessionId = sessionStorage.getItem('sahayak_session_id');
    const savedCitizenId = sessionStorage.getItem('sahayak_citizen_id');
    const savedConsent = sessionStorage.getItem('sahayak_consent_granted');
    return {
      sessionId: savedSessionId,
      citizenId: savedCitizenId,
      preferredLanguage: 'hi',
      consentGrantedAt: savedConsent,
      isActive: Boolean(savedSessionId),
      isLoading: false,
      error: null,
    };
  });

  const [profile, setProfile] = useState<CitizenProfile>(defaultProfile);

  // Poll health status on mount
  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        const res = await fetchHealth();
        if (isMounted) setHealth(res);
      } catch {
        if (isMounted) {
          setHealth({
            status: 'offline',
            app_name: 'SAHAYAK',
            version: '0.1.0',
            environment: 'development',
            database_connected: false,
            timestamp: new Date().toISOString(),
          });
        }
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Fetch profile if citizen ID is known
  useEffect(() => {
    if (!session.citizenId) return;
    let isMounted = true;
    fetchProfile(session.citizenId, session.sessionId)
      .then((p) => {
        if (isMounted) setProfile(p);
      })
      .catch(() => {
        // Keep default empty profile
      });
    return () => {
      isMounted = false;
    };
  }, [session.citizenId]);

  const giveConsent = async () => {
    setSession((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const data = await initSession(language, true);
      sessionStorage.setItem('sahayak_session_id', data.session_id);
      sessionStorage.setItem('sahayak_citizen_id', data.citizen_id);
      if (data.consent_granted_at) {
        sessionStorage.setItem('sahayak_consent_granted', data.consent_granted_at);
      }
      setSession({
        sessionId: data.session_id,
        citizenId: data.citizen_id,
        preferredLanguage: language,
        consentGrantedAt: data.consent_granted_at,
        isActive: true,
        isLoading: false,
        error: null,
      });
    } catch (err) {
      setSession((prev) => ({
        ...prev,
        isLoading: false,
        error: (err as Error).message || 'Failed to initialize session',
      }));
    }
  };

  const declineConsent = () => {
    sessionStorage.removeItem('sahayak_session_id');
    sessionStorage.removeItem('sahayak_citizen_id');
    sessionStorage.removeItem('sahayak_consent_granted');
    setSession((prev) => ({
      ...prev,
      consentGrantedAt: null,
      isActive: false,
    }));
  };

  const saveProfile = async (updated: Partial<CitizenProfile>) => {
    if (!session.citizenId) {
      // In-memory update before session registration
      setProfile((prev) => ({ ...prev, ...updated }));
      return;
    }
    const res = await updateProfile(session.citizenId, updated, session.sessionId);
    setProfile(res);
  };

  const wipeAndEndSession = async () => {
    if (session.sessionId) {
      try {
        await terminateSession(session.sessionId);
      } catch {
        // Best effort backend notification
      }
    }
    // Purge ephemeral storage and in-memory PII
    sessionStorage.clear();
    setProfile(defaultProfile);
    setSession({
      sessionId: null,
      citizenId: null,
      preferredLanguage: language,
      consentGrantedAt: null,
      isActive: false,
      isLoading: false,
      error: null,
    });
  };

  const refreshProfile = async () => {
    if (!session.citizenId) return;
    try {
      const p = await fetchProfile(session.citizenId, session.sessionId);
      setProfile(p);
    } catch {
      // Keep existing profile on error
    }
  };

  return (
    <SessionContext.Provider
      value={{
        language,
        setLanguage,
        session,
        health,
        profile,
        giveConsent,
        declineConsent,
        saveProfile,
        wipeAndEndSession,
        refreshProfile,
      }}
    >
      {children}
    </SessionContext.Provider>
  );

};

export const useSession = (): SessionContextType => {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
};
