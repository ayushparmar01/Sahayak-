import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { SessionProvider } from './context/SessionContext';
import { Navbar } from './components/Navbar';
import { ConsentBanner } from './components/ConsentBanner';
import { HomePage } from './pages/HomePage';
import { SchemesPage } from './pages/SchemesPage';
import { ProfilePage } from './pages/ProfilePage';
import { DocumentsPage } from './pages/DocumentsPage';
import { ApplicationsPage } from './pages/ApplicationsPage';
import { FollowUpPage } from './pages/FollowUpPage';
import { PrivacyPage } from './pages/PrivacyPage';
import { VoiceAssistantPage } from './pages/VoiceAssistantPage';

export const App: React.FC = () => {
  return (
    <Router>
      <SessionProvider>
        <div className="min-h-screen flex flex-col bg-stone-50 text-stone-900">
          <Navbar />
          <ConsentBanner />
          <main className="flex-1 pb-12">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/assistant" element={<VoiceAssistantPage />} />
              <Route path="/schemes" element={<SchemesPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/documents" element={<DocumentsPage />} />
              <Route path="/applications" element={<ApplicationsPage />} />
              <Route path="/followup" element={<FollowUpPage />} />
              <Route path="/privacy" element={<PrivacyPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>

          <footer className="bg-stone-900 text-stone-400 py-6 text-center text-xs border-t border-stone-800">
            <div className="max-w-7xl mx-auto px-4 space-y-1">
              <p className="font-semibold text-stone-200">
                SAHAYAK (सहायक) — Voice-First Multi-Agent AI for Government Scheme Access
              </p>
              <p>Deviathon 2.0 National Hackathon • GLA University, Mathura • Theme: Mission Bharat + AI Frontier</p>
              <p className="text-[11px] text-stone-500 pt-1">
                Zero-Aadhaar storage policy • DPDP Act 2023 aligned • Deterministic rules engine
              </p>
            </div>
          </footer>
        </div>
      </SessionProvider>
    </Router>
  );
};

export default App;
