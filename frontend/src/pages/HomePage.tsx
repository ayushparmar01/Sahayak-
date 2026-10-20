import React from 'react';

import { useNavigate } from 'react-router-dom';
import { useSession } from '../context/SessionContext';
import { translations } from '../i18n/translations';
import { Card } from '../components/Card';
import {
  MicIcon,
  GlobeIcon,
  UserCheckIcon,
  FileTextIcon,
  ShieldCheckIcon,
  ArrowRightIcon,
} from '../components/Icons';

export const HomePage: React.FC = () => {
  const { language } = useSession();
  const t = translations[language];
  const navigate = useNavigate();


  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Hero Section */}
      <div className="bg-gradient-to-br from-emerald-900 via-stone-900 to-emerald-950 text-white rounded-2xl p-6 sm:p-10 shadow-lg border border-emerald-700/40 relative overflow-hidden">
        <div className="max-w-3xl space-y-4">
          <div className="inline-flex items-center space-x-2 bg-emerald-800/80 text-emerald-200 px-3 py-1 rounded-full text-xs font-semibold border border-emerald-600/50">
            <span>{t.hackathonTag}</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-bold tracking-tight">
            {t.home.heroHeading}
          </h1>
          <p className="text-stone-300 text-sm sm:text-base leading-relaxed">
            {t.home.heroSubheading}
          </p>

          {/* Voice Interaction Box */}
          <div className="bg-stone-900/90 border border-emerald-500/40 rounded-xl p-4 sm:p-5 mt-6 shadow-inner space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="text-xs sm:text-sm text-stone-300">
                <span className="text-emerald-400 font-semibold block mb-0.5">
                  आवाज आधारित सहायक (AI Voice Assistant)
                </span>
                {t.home.voicePrompt}
              </div>
              <button
                onClick={() => navigate('/assistant')}
                className="flex items-center justify-center space-x-2 px-5 py-2.5 rounded-xl font-semibold text-xs sm:text-sm transition shrink-0 bg-emerald-600 hover:bg-emerald-500 text-white shadow-md"
              >
                <MicIcon size={18} />
                <span>{language === 'hi' ? 'वॉइस सहायक प्रारंभ करें' : 'Launch Voice Assistant'}</span>
              </button>
            </div>
          </div>

        </div>
      </div>

      {/* Phase 1 Foundation Notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 sm:p-5 text-blue-950 flex items-start space-x-3.5">
        <ShieldCheckIcon size={24} className="text-blue-700 shrink-0 mt-0.5" />
        <div className="text-xs sm:text-sm">
          <h2 className="font-bold text-blue-900">{t.home.foundationNoticeTitle}</h2>
          <p className="mt-1 leading-relaxed text-blue-900/90">
            {t.home.foundationNoticeBody}
          </p>
        </div>
      </div>

      {/* Core Public Service Cards */}
      <div>
        <h2 className="text-lg font-bold text-stone-900 mb-4">{t.home.quickTitle}</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card onClick={() => navigate('/schemes')} className="p-5 flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center mb-3">
                <GlobeIcon size={20} />
              </div>
              <h3 className="font-bold text-sm text-stone-900">{t.home.cards.schemesTitle}</h3>
              <p className="text-xs text-stone-600 mt-1 leading-relaxed">
                {t.home.cards.schemesDesc}
              </p>
            </div>
            <div className="mt-4 flex items-center text-xs font-semibold text-emerald-700">
              <span>{t.common.learnMore}</span>
              <ArrowRightIcon size={14} className="ml-1" />
            </div>
          </Card>

          <Card onClick={() => navigate('/profile')} className="p-5 flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-800 flex items-center justify-center mb-3">
                <UserCheckIcon size={20} />
              </div>
              <h3 className="font-bold text-sm text-stone-900">{t.home.cards.profileTitle}</h3>
              <p className="text-xs text-stone-600 mt-1 leading-relaxed">
                {t.home.cards.profileDesc}
              </p>
            </div>
            <div className="mt-4 flex items-center text-xs font-semibold text-blue-700">
              <span>दर्ज करें</span>
              <ArrowRightIcon size={14} className="ml-1" />
            </div>
          </Card>

          <Card onClick={() => navigate('/documents')} className="p-5 flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center mb-3">
                <FileTextIcon size={20} />
              </div>
              <h3 className="font-bold text-sm text-stone-900">{t.home.cards.documentsTitle}</h3>
              <p className="text-xs text-stone-600 mt-1 leading-relaxed">
                {t.home.cards.documentsDesc}
              </p>
            </div>
            <div className="mt-4 flex items-center text-xs font-semibold text-amber-700">
              <span>चेकलिस्ट देखें</span>
              <ArrowRightIcon size={14} className="ml-1" />
            </div>
          </Card>

          <Card onClick={() => navigate('/applications')} className="p-5 flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-lg bg-purple-100 text-purple-800 flex items-center justify-center mb-3">
                <ShieldCheckIcon size={20} />
              </div>
              <h3 className="font-bold text-sm text-stone-900">{t.home.cards.applicationsTitle}</h3>
              <p className="text-xs text-stone-600 mt-1 leading-relaxed">
                {t.home.cards.applicationsDesc}
              </p>
            </div>
            <div className="mt-4 flex items-center text-xs font-semibold text-purple-700">
              <span>ड्राफ्ट देखें</span>
              <ArrowRightIcon size={14} className="ml-1" />
            </div>
          </Card>
        </div>
      </div>

      {/* Public Service Disclaimer */}
      <div className="bg-stone-100 border border-stone-200 rounded-xl p-4 sm:p-5 text-stone-700 text-xs leading-relaxed">
        <span className="font-bold text-stone-900 block mb-1">
          {t.home.disclaimerTitle}
        </span>
        <p>{t.home.disclaimerBody}</p>
      </div>
    </div>
  );
};
