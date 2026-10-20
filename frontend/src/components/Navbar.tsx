import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useSession } from '../context/SessionContext';
import { translations } from '../i18n/translations';
import { GlobeIcon, Trash2Icon, ShieldCheckIcon } from './Icons';

export const Navbar: React.FC = () => {
  const { language, setLanguage, session, health, wipeAndEndSession } = useSession();
  const t = translations[language];
  const location = useLocation();

  const navLinks = [
    { to: '/', label: t.nav.home },
    { to: '/assistant', label: t.nav.assistant },
    { to: '/schemes', label: t.nav.schemes },
    { to: '/profile', label: t.nav.profile },
    { to: '/documents', label: t.nav.documents },
    { to: '/applications', label: t.nav.applications },
    { to: '/followup', label: t.nav.followup },
    { to: '/privacy', label: t.nav.privacy },
  ];


  return (
    <header className="bg-stone-900 text-stone-100 shadow-md border-b-2 border-emerald-600 sticky top-0 z-50">
      {/* Top Utility Ribbon */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-1.5 flex flex-wrap justify-between items-center text-xs text-stone-300 border-b border-stone-800">
        <div className="flex items-center space-x-2">
          <span className="font-semibold text-emerald-400">{t.hackathonTag}</span>
          <span className="hidden sm:inline text-stone-500">•</span>
          <span className="hidden sm:inline">{t.tagline}</span>
        </div>
        <div className="flex items-center space-x-4">
          {/* Health Indicator */}
          <div className="flex items-center space-x-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                health?.database_connected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
              }`}
            />
            <span className="text-[11px]">
              {health?.database_connected
                ? t.systemStatus.online
                : t.systemStatus.offline}
            </span>
          </div>

          {/* Language Toggle */}
          <button
            onClick={() => setLanguage(language === 'hi' ? 'en' : 'hi')}
            className="flex items-center space-x-1 bg-stone-800 hover:bg-stone-700 text-stone-200 px-2.5 py-1 rounded transition border border-stone-700"
            title="भाषा बदलें / Switch Language"
          >
            <GlobeIcon size={14} />
            <span className="font-medium">{language === 'hi' ? 'English' : 'हिन्दी'}</span>
          </button>

          {/* Kiosk Purge / End Session */}
          {session.isActive && (
            <button
              onClick={wipeAndEndSession}
              className="flex items-center space-x-1 bg-rose-900/80 hover:bg-rose-800 text-rose-200 px-2.5 py-1 rounded transition border border-rose-700 text-[11px]"
              title={t.nav.endSession}
            >
              <Trash2Icon size={13} />
              <span className="hidden md:inline">{t.nav.endSession}</span>
              <span className="md:hidden">सत्र समाप्त</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Nav Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap justify-between items-center">
        <Link to="/" className="flex items-center space-x-3 group">
          <div className="w-10 h-10 rounded-lg bg-emerald-700 flex items-center justify-center text-white font-bold text-xl shadow border border-emerald-500">
            स
          </div>
          <div>
            <div className="text-xl font-bold tracking-tight text-white flex items-center space-x-1.5">
              <span>{t.appName}</span>
              <ShieldCheckIcon size={18} className="text-emerald-400" />
            </div>
            <div className="text-[11px] text-stone-400">सार्वजनिक सेवा कल्याण मंच</div>
          </div>
        </Link>

        {/* Navigation Links */}
        <nav className="flex flex-wrap items-center gap-1 sm:gap-2 mt-2 sm:mt-0">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.to;
            return (
              <Link
                key={link.to}
                to={link.to}
                className={`px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition ${
                  isActive
                    ? 'bg-emerald-800 text-white shadow-inner font-semibold'
                    : 'text-stone-300 hover:bg-stone-800 hover:text-white'
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
