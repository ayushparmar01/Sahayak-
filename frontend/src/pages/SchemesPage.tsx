import React, { useEffect, useState } from 'react';
import { useSession } from '../context/SessionContext';
import { translations } from '../i18n/translations';
import { Scheme } from '../types/index.ts';
import { fetchSchemes } from '../services/api';
import { Card } from '../components/Card';
import { StatusPill } from '../components/StatusPill';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorAlert } from '../components/ErrorAlert';
import { EmptyState } from '../components/EmptyState';
import { ExternalLinkIcon, ClockIcon } from '../components/Icons';
import { SchemeDetailModal } from '../components/SchemeDetailModal';

export const SchemesPage: React.FC = () => {
  const { language } = useSession();
  const t = translations[language];
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<string>('ALL');
  const [activeModalSchemeId, setActiveModalSchemeId] = useState<string | null>(null);

  const loadSchemes = async () => {
    setLoading(true);
    setError(null);
    try {
      const filters: Record<string, string> = {};
      if (selectedCategory !== 'ALL') filters.category = selectedCategory;
      if (selectedJurisdiction !== 'ALL') filters.jurisdiction = selectedJurisdiction;

      const data = await fetchSchemes(filters);
      setSchemes(data.schemes);
    } catch (err) {
      setError((err as Error).message || 'Failed to fetch schemes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSchemes();
  }, [selectedCategory, selectedJurisdiction]);

  const filtered = schemes.filter((s) => {
    const q = searchTerm.toLowerCase();
    return (
      s.name_hi.toLowerCase().includes(q) ||
      s.name_en.toLowerCase().includes(q) ||
      s.ministry.toLowerCase().includes(q) ||
      s.code.toLowerCase().includes(q)
    );
  });

  const categories = [
    { id: 'ALL', label: t.schemesPage.allCategories },
    { id: 'AGRICULTURE', label: t.schemesPage.agriculture },
    { id: 'HEALTHCARE', label: t.schemesPage.healthcare },
    { id: 'HOUSING', label: t.schemesPage.housing },
    { id: 'WOMEN_CHILD', label: t.schemesPage.womenChild },
    { id: 'FINANCIAL_SECURITY', label: t.schemesPage.financialSecurity },
    { id: 'SOCIAL_WELFARE', label: t.schemesPage.socialWelfare },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-stone-900">{t.schemesPage.title}</h1>
        <p className="text-stone-600 text-xs sm:text-sm mt-1">{t.schemesPage.subtitle}</p>
      </div>

      {/* Phase 2 Operational Callout */}
      <div className="bg-emerald-50 border border-emerald-300 rounded-xl p-3.5 text-xs text-emerald-950 flex items-start space-x-2.5">
        <span className="text-emerald-700 font-bold shrink-0 mt-0.5">✓</span>
        <div>
          <span className="font-bold block mb-0.5">
            चरण 2 सक्रिय: सत्यापित ज्ञान आधार एवं पात्रता निर्धारण इंजन (Deterministic Engine Active)
          </span>
          <p className="leading-relaxed">
            प्रत्येक योजना पर क्लिक करके उसके प्राथमिक स्रोत, 13-सूत्रीय अपवर्जन और आधिकारिक दिशानिर्देश देखें
            तथा अपनी प्रोफ़ाइल के अनुसार निष्पक्ष पात्रता जांचें।
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="space-y-3">
        {/* Category Pills */}
        <div className="flex flex-wrap gap-1.5 sm:gap-2">
          {categories.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelectedCategory(c.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                selectedCategory === c.id
                  ? 'bg-emerald-800 text-white shadow-sm'
                  : 'bg-stone-100 hover:bg-stone-200 text-stone-700 border border-stone-200'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Search & Jurisdiction Row */}
        <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
          <div className="max-w-md w-full">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={t.schemesPage.searchPlaceholder}
              className="w-full px-3.5 py-2 text-xs sm:text-sm rounded-lg border border-stone-300 focus:outline-none focus:ring-2 focus:ring-emerald-600 bg-white"
            />
          </div>

          <div className="flex items-center space-x-2">
            <select
              value={selectedJurisdiction}
              onChange={(e) => setSelectedJurisdiction(e.target.value)}
              className="px-3 py-2 text-xs border border-stone-300 rounded-lg focus:ring-2 focus:ring-emerald-600 bg-white"
            >
              <option value="ALL">{t.schemesPage.allJurisdictions}</option>
              <option value="CENTRAL_SECTOR">{t.schemesPage.centralSector}</option>
              <option value="CENTRALLY_SPONSORED">{t.schemesPage.centrallySponsored}</option>
            </select>
          </div>
        </div>
      </div>

      {/* Body States */}
      {loading && <LoadingSpinner label={t.common.loading} />}
      {error && <ErrorAlert message={error} onRetry={loadSchemes} />}

      {!loading && !error && filtered.length === 0 && (
        <EmptyState
          title={t.common.empty}
          description="आपकी खोज या चयनित फिल्टर के अनुसार कोई योजना नहीं मिली।"
          actionText="सभी योजनाएं देखें"
          onAction={() => {
            setSearchTerm('');
            setSelectedCategory('ALL');
            setSelectedJurisdiction('ALL');
          }}
        />
      )}

      {/* Schemes Grid */}
      {!loading && !error && filtered.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((s) => {
            const name = language === 'hi' ? s.name_hi : s.name_en;
            const benefit = language === 'hi' ? s.benefit_summary_hi : s.benefit_summary_en;

            return (
              <Card key={s.id} className="p-5 flex flex-col justify-between hover:border-emerald-500 transition-colors">
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-[11px] font-mono font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        {s.code}
                      </span>
                      <span className="text-[10px] font-medium text-stone-600 bg-stone-100 px-1.5 py-0.5 rounded border border-stone-200 ml-1.5">
                        {s.jurisdiction === 'CENTRAL_SECTOR'
                          ? t.schemesPage.centralSector
                          : t.schemesPage.centrallySponsored}
                      </span>
                      {s.benefit_type === 'CONCESSIONAL_CREDIT_LIMIT' && (
                        <span className="text-[10px] font-semibold text-amber-800 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 ml-1.5">
                          {language === 'hi' ? 'साख ऋण' : 'Credit Limit'}
                        </span>
                      )}
                      {s.benefit_type === 'SMALL_SAVINGS_DEPOSIT_LIMIT' && (
                        <span className="text-[10px] font-semibold text-purple-800 bg-purple-50 px-1.5 py-0.5 rounded border border-purple-200 ml-1.5">
                          {language === 'hi' ? 'बचत जमा' : 'Small Savings'}
                        </span>
                      )}
                      {s.benefit_type === 'HEALTH_INSURANCE_COVER' && (
                        <span className="text-[10px] font-semibold text-blue-800 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200 ml-1.5">
                          {language === 'hi' ? 'स्वास्थ्य बीमा' : 'Health Cover'}
                        </span>
                      )}
                      {s.benefit_type === 'CROP_INSURANCE_COVER' && (
                        <span className="text-[10px] font-semibold text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200 ml-1.5">
                          {language === 'hi' ? 'फसल बीमा' : 'Crop Insurance'}
                        </span>
                      )}
                      {s.benefit_type === 'ONE_TIME_ASSISTANCE' && (
                        <span className="text-[10px] font-semibold text-teal-800 bg-teal-50 px-1.5 py-0.5 rounded border border-teal-200 ml-1.5">
                          {language === 'hi' ? 'एकमुश्त सहायता' : 'One-Time Aid'}
                        </span>
                      )}
                      {s.benefit_type === 'SOCIAL_PENSION' && (
                        <span className="text-[10px] font-semibold text-indigo-800 bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-200 ml-1.5">
                          {language === 'hi' ? 'मासिक पेंशन' : 'Pension'}
                        </span>
                      )}
                      {s.benefit_type === 'DIRECT_CASH_TRANSFER' && (
                        <span className="text-[10px] font-semibold text-green-800 bg-green-50 px-1.5 py-0.5 rounded border border-green-200 ml-1.5">
                          {language === 'hi' ? 'प्रत्यक्ष नकद (DBT)' : 'DBT Cash'}
                        </span>
                      )}
                      <h3 className="font-bold text-base text-stone-900 mt-1">{name}</h3>
                      <p className="text-xs text-stone-500 mt-0.5">{s.ministry}</p>
                    </div>
                    <StatusPill status={s.verification_status} label={t.schemesPage.verifiedBadge} />
                  </div>

                  <p className="text-xs sm:text-sm text-stone-700 leading-relaxed bg-stone-50 p-3 rounded-lg border border-stone-200">
                    {benefit}
                  </p>

                  <div className="grid grid-cols-2 gap-2 text-xs text-stone-600 pt-1">
                    <div>
                      <span className="text-stone-400 block text-[11px]">
                        {language === 'hi'
                          ? (s.benefit_metric_label_hi || t.schemesPage.annualBenefit)
                          : (s.benefit_metric_label_en || 'Benefit / Facility')}
                      </span>
                      <span className="font-bold text-stone-900">
                        {language === 'hi'
                          ? (s.benefit_amount_display_hi || `₹${s.max_annual_benefit_inr.toLocaleString('en-IN')}`)
                          : (s.benefit_amount_display_en || `₹${s.max_annual_benefit_inr.toLocaleString('en-IN')}`)}
                      </span>
                    </div>
                    <div>
                      <span className="text-stone-400 block text-[11px]">{t.schemesPage.lastVerified}</span>
                      <span className="font-medium text-stone-700 flex items-center space-x-1">
                        <ClockIcon size={12} className="text-stone-400" />
                        <span>{s.last_verified_date}</span>
                      </span>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-stone-100 flex items-center justify-between gap-2">
                  <button
                    onClick={() => setActiveModalSchemeId(s.id)}
                    className="px-3.5 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-semibold transition shadow-sm"
                  >
                    🔍 {t.schemesPage.viewDetailsBtn}
                  </button>

                  <a
                    href={s.official_portal_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center space-x-1 text-xs font-semibold text-stone-600 hover:text-emerald-800 hover:underline"
                  >
                    <span>{t.schemesPage.viewOfficial}</span>
                    <ExternalLinkIcon size={13} />
                  </a>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Scheme Detail & Assessment Modal */}
      {activeModalSchemeId && (
        <SchemeDetailModal
          schemeId={activeModalSchemeId}
          onClose={() => setActiveModalSchemeId(null)}
        />
      )}
    </div>
  );
};
