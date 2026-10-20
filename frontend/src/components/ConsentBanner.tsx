import React from 'react';
import { useSession } from '../context/SessionContext';
import { translations } from '../i18n/translations';
import { ShieldCheckIcon } from './Icons';

export const ConsentBanner: React.FC = () => {
  const { language, session, giveConsent, declineConsent } = useSession();
  const t = translations[language];

  if (session.consentGrantedAt) {
    return null;
  }

  return (
    <div className="bg-amber-50 border-b border-amber-200 px-4 py-3 shadow-sm">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <div className="flex items-start space-x-3">
          <ShieldCheckIcon size={22} className="text-amber-700 shrink-0 mt-0.5" />
          <div className="text-xs sm:text-sm text-amber-950">
            <span className="font-semibold block">{t.consent.title}</span>
            <p className="mt-0.5">{t.consent.description}</p>
            <p className="text-[11px] text-amber-800/80 mt-1">{t.consent.dpdpNotice}</p>
          </div>
        </div>
        <div className="flex items-center space-x-2 shrink-0 self-end md:self-center">
          <button
            onClick={giveConsent}
            disabled={session.isLoading}
            className="bg-emerald-700 hover:bg-emerald-800 text-white font-medium px-4 py-1.5 rounded-md text-xs transition shadow-sm"
          >
            {session.isLoading ? t.common.loading : t.consent.accept}
          </button>
          <button
            onClick={declineConsent}
            className="bg-stone-200 hover:bg-stone-300 text-stone-700 px-3 py-1.5 rounded-md text-xs transition"
          >
            {t.consent.decline}
          </button>
        </div>
      </div>
    </div>
  );
};
