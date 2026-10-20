import React, { useState, useEffect } from 'react';
import { useSession } from '../context/SessionContext';
import { translations } from '../i18n/translations';
import { Card } from '../components/Card';
import { FileTextIcon, ShieldCheckIcon, CheckCircleIcon } from '../components/Icons';
import {
  fetchSchemes,
  fetchSchemeChecklist,
  generateCSCPackage,
  fetchCitizenDrafts,
  getCSCPackagePdfUrl,
} from '../services/api';
import type {
  Scheme,
  SchemeChecklistResponse,
  CSCPackageResponse,
  ApplicationDraftListItem,
} from '../types';

export const ApplicationsPage: React.FC = () => {
  const { language, session } = useSession();
  const sessionId = session.sessionId;
  const citizenId = session.citizenId;
  const t = translations[language];


  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [selectedSchemeId, setSelectedSchemeId] = useState<string>('pm-kisan');
  const [checklist, setChecklist] = useState<SchemeChecklistResponse | null>(null);
  const [isLoadingChecklist, setIsLoadingChecklist] = useState<boolean>(false);

  const [operatorNotes, setOperatorNotes] = useState<string>('');
  const [disclaimerAck, setDisclaimerAck] = useState<boolean>(true);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [generatedPackage, setGeneratedPackage] = useState<CSCPackageResponse | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const [drafts, setDrafts] = useState<ApplicationDraftListItem[]>([]);

  useEffect(() => {
    loadSchemes();
  }, []);

  useEffect(() => {
    if (selectedSchemeId) {
      loadChecklist(selectedSchemeId);
    }
  }, [selectedSchemeId, citizenId, sessionId]);

  useEffect(() => {
    if (citizenId) {
      loadDrafts();
    }
  }, [citizenId, sessionId]);

  const loadSchemes = async () => {
    try {
      const data = await fetchSchemes();
      setSchemes(data.schemes || []);
    } catch (err: any) {
      console.error('Failed to load schemes:', err);
    }
  };

  const loadChecklist = async (schemeId: string) => {
    setIsLoadingChecklist(true);
    try {
      const data = await fetchSchemeChecklist(schemeId, citizenId, sessionId);
      setChecklist(data);
    } catch (err: any) {
      console.error('Failed to load checklist:', err);
    } finally {
      setIsLoadingChecklist(false);
    }
  };

  const loadDrafts = async () => {
    if (!citizenId) return;
    try {
      const data = await fetchCitizenDrafts(citizenId, sessionId);
      setDrafts(data);
    } catch (err: any) {
      console.error('Failed to load drafts:', err);
    }
  };

  const handleGeneratePackage = async () => {
    if (!citizenId) {
      setGenerateError(language === 'hi' ? 'कृपया पहले सत्र प्रारंभ करें।' : 'Please start a session first.');
      return;
    }
    if (!disclaimerAck) {
      setGenerateError(language === 'hi' ? 'कृपया अस्वीकरण स्वीकार करें।' : 'Please acknowledge the disclaimer.');
      return;
    }

    setIsGenerating(true);
    setGenerateError(null);

    try {
      const res = await generateCSCPackage(
        {
          citizen_id: citizenId,
          scheme_id: selectedSchemeId,
          operator_notes: operatorNotes || undefined,
          disclaimer_acknowledged: disclaimerAck,
        },
        sessionId
      );
      setGeneratedPackage(res);
      await loadDrafts();
    } catch (err: any) {
      setGenerateError(err.message || 'Package generation failed');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-stone-900">{t.applicationsPage.title}</h1>
        <p className="text-stone-600 text-xs sm:text-sm mt-1">{t.applicationsPage.subtitle}</p>
      </div>

      {/* Prominent Statutory Disclaimer Banner */}
      <div className="bg-rose-50 border-2 border-rose-300 rounded-xl p-4 text-xs text-rose-950 flex items-start space-x-3">
        <ShieldCheckIcon size={22} className="text-rose-700 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold block mb-1 text-sm text-rose-900">
            {language === 'hi' ? 'वैधानिक प्रकटीकरण (Statutory Preparation Aid Disclaimer):' : 'Statutory Preparation Aid Disclaimer:'}
          </span>
          <p className="leading-relaxed">{t.applicationsPage.disclaimerBanner}</p>
        </div>
      </div>

      {/* Scheme Picker & Checklist Hub */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scheme Selector & Action Card */}
        <Card className="p-6 lg:col-span-1 space-y-5 flex flex-col justify-between">
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-stone-700 mb-1.5">
                {t.applicationsPage.selectScheme}
              </label>
              <select
                value={selectedSchemeId}
                onChange={(e) => setSelectedSchemeId(e.target.value)}
                className="w-full text-xs font-semibold bg-white border border-stone-300 rounded-lg p-2.5 text-stone-900 focus:ring-2 focus:ring-emerald-600 focus:outline-none"
              >
                {schemes.map((s) => (
                  <option key={s.id} value={s.id}>
                    {language === 'hi' ? s.name_hi : s.name_en} ({s.code})
                  </option>
                ))}
              </select>
            </div>

            {/* Readiness Gauge */}
            {checklist && (
              <div className="bg-stone-50 p-4 rounded-xl border border-stone-200 space-y-3">
                <div className="flex items-end justify-between">
                  <span className="text-xs font-bold text-stone-700">{t.applicationsPage.readinessScore}</span>
                  <span className="text-2xl font-extrabold text-emerald-700">
                    {checklist.readiness_percentage}%
                  </span>
                </div>

                <div className="w-full bg-stone-200 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-emerald-600 h-2.5 rounded-full transition-all duration-500"
                    style={{ width: `${checklist.readiness_percentage}%` }}
                  />
                </div>

                <div className="flex justify-between text-[11px] text-stone-500 font-medium">
                  <span>
                    {t.applicationsPage.requiredDocs} {checklist.total_required}
                  </span>
                  <span>
                    {t.applicationsPage.presentDocs} {checklist.total_present}
                  </span>
                </div>

                {checklist.is_ready_for_packaging ? (
                  <div className="text-[11px] font-semibold text-emerald-800 bg-emerald-100 p-2 rounded">
                    ✓ {t.applicationsPage.readyToPackage}
                  </div>
                ) : (
                  <div className="text-[11px] font-medium text-amber-800 bg-amber-100 p-2 rounded">
                    ⚠ {t.applicationsPage.missingNotice}
                  </div>
                )}
              </div>
            )}

            {/* Operator Notes Input */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                {t.applicationsPage.operatorNotesLabel}
              </label>
              <textarea
                value={operatorNotes}
                onChange={(e) => setOperatorNotes(e.target.value)}
                rows={2}
                placeholder={language === 'hi' ? 'जैसे: खतौनी 142/1 सत्यापित, सीएससी केंद्र 4192' : 'e.g., Khatauni verified, CSC Centre 4192'}
                className="w-full text-xs border border-stone-300 rounded-lg p-2 focus:ring-1 focus:ring-emerald-600 focus:outline-none"
              />
            </div>

            {/* Disclaimer Ack Checkbox */}
            <label className="flex items-start space-x-2 text-xs text-stone-700 cursor-pointer">
              <input
                type="checkbox"
                checked={disclaimerAck}
                onChange={(e) => setDisclaimerAck(e.target.checked)}
                className="mt-0.5 rounded text-emerald-700 focus:ring-emerald-600"
              />
              <span className="font-medium text-[11px]">{t.applicationsPage.disclaimerCheckbox}</span>
            </label>

            {generateError && (
              <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 p-2.5 rounded-lg">
                {generateError}
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-stone-100">
            <button
              onClick={handleGeneratePackage}
              disabled={isGenerating || !citizenId}
              className={`w-full py-2.5 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 ${
                isGenerating || !citizenId
                  ? 'bg-stone-200 text-stone-400 cursor-not-allowed'
                  : 'bg-emerald-800 hover:bg-emerald-900 text-white shadow-sm'
              }`}
            >
              {isGenerating ? (
                <>
                  <span className="animate-spin inline-block w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full" />
                  <span>{t.applicationsPage.generating}</span>
                </>
              ) : (
                <>
                  <FileTextIcon size={14} />
                  <span>{t.applicationsPage.generatePackageBtn}</span>
                </>
              )}
            </button>
          </div>
        </Card>

        {/* Scheme Checklist Items Table */}
        <Card className="p-6 lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm sm:text-base font-bold text-stone-900">
              {t.applicationsPage.checklistTitle}
            </h2>
            {checklist && (
              <span className="text-xs text-stone-500 font-semibold">
                {language === 'hi' ? checklist.scheme_name_hi : checklist.scheme_name_en}
              </span>
            )}
          </div>

          {isLoadingChecklist ? (
            <div className="py-8 text-center text-xs text-stone-500">
              <span className="animate-spin inline-block w-4 h-4 border-2 border-emerald-700 border-t-transparent rounded-full mr-2" />
              {language === 'hi' ? 'चेकलिस्ट लोड हो रही है...' : 'Loading checklist...'}
            </div>
          ) : checklist && checklist.checklist.length > 0 ? (
            <div className="space-y-3">
              {checklist.checklist.map((item) => {
                const isPresent = item.status === 'PRESENT';
                const isPending = item.status === 'PENDING_CONFIRMATION';
                return (
                  <div
                    key={item.document_code}
                    className="bg-stone-50 p-3.5 rounded-xl border border-stone-200 flex items-start justify-between space-x-3 text-xs"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <CheckCircleIcon
                          size={16}
                          className={isPresent ? 'text-emerald-600' : isPending ? 'text-amber-500' : 'text-stone-300'}
                        />
                        <span className="font-bold text-stone-900">
                          {language === 'hi' ? item.document_title_hi : item.document_title_en}
                        </span>
                        <span className="text-[10px] bg-stone-200 text-stone-700 px-1.5 py-0.5 rounded">
                          {item.is_mandatory ? (language === 'hi' ? 'अनिवार्य' : 'Mandatory') : 'वैकल्पिक'}
                        </span>
                      </div>
                      <p className="text-[11px] text-stone-500 pl-6">
                        {language === 'hi' ? 'वैधानिक नियम: ' : 'Statutory citation: '}
                        <span className="text-stone-700 font-medium">{item.statutory_citation}</span>
                      </p>
                    </div>

                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded whitespace-nowrap ${
                        isPresent
                          ? 'bg-emerald-100 text-emerald-800'
                          : isPending
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {isPresent
                        ? language === 'hi' ? 'सत्यापित संलग्न' : 'ATTACHED & CONFIRMED'
                        : isPending
                        ? language === 'hi' ? 'समीक्षा लंबित' : 'PENDING REVIEW'
                        : language === 'hi' ? 'अनुपलब्ध' : 'MISSING'}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-xs text-stone-500 text-center py-6">
              {language === 'hi' ? 'कोई आवश्यकता नहीं मिली।' : 'No checklist requirements found.'}
            </div>
          )}

          {/* Guideline note */}
          {checklist && (
            <div className="pt-3 border-t border-stone-100 text-[11px] text-stone-600">
              <span className="font-semibold text-stone-800">
                {language === 'hi' ? 'आवेदन प्रक्रिया दिशा-निर्देश: ' : 'Application Guidelines: '}
              </span>
              {language === 'hi' ? checklist.guideline_notes_hi : checklist.guideline_notes_en}
            </div>
          )}
        </Card>
      </div>

      {/* Generated Package Banner (if just generated) */}
      {generatedPackage && (
        <Card className="p-6 bg-emerald-50 border-2 border-emerald-300 space-y-4">
          <div className="flex items-center space-x-2 text-emerald-800">
            <CheckCircleIcon size={20} />
            <h3 className="font-bold text-sm sm:text-base">
              {generatedPackage.message || (language === 'hi' ? 'सीएससी आवेदन पैकेज तैयार!' : 'CSC Package Ready!')}
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs bg-white p-3.5 rounded-xl border border-emerald-200">
            <div>
              <span className="text-stone-400 block">{t.applicationsPage.schemeName}:</span>
              <span className="font-bold text-stone-800">
                {language === 'hi' ? generatedPackage.scheme_name_hi : generatedPackage.scheme_name_en}
              </span>
            </div>
            <div>
              <span className="text-stone-400 block">{t.applicationsPage.completeness}:</span>
              <span className="font-extrabold text-emerald-700 text-sm">
                {generatedPackage.completeness_percentage}%
              </span>
            </div>
            <div>
              <span className="text-stone-400 block">{t.applicationsPage.draftId}:</span>
              <span className="font-mono text-stone-700 text-[11px]">
                {generatedPackage.draft_id.slice(0, 16)}...
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-3 pt-1">
            <a
              href={getCSCPackagePdfUrl(generatedPackage.draft_id, sessionId)}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-emerald-800 hover:bg-emerald-900 text-white text-xs font-bold rounded-lg transition shadow flex items-center space-x-2"
            >

              <FileTextIcon size={14} />
              <span>{t.applicationsPage.downloadPdfBtn}</span>
            </a>
          </div>
        </Card>
      )}

      {/* Prepared Drafts Table */}
      <Card className="p-6 space-y-4">
        <h2 className="text-base font-bold text-stone-900">{t.applicationsPage.previousDraftsTitle}</h2>

        {drafts.length === 0 ? (
          <div className="text-center py-8 text-xs text-stone-500 bg-stone-50 rounded-lg border border-dashed border-stone-200">
            {t.applicationsPage.noDrafts}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-stone-50 text-stone-600 border-b border-stone-200">
                <tr>
                  <th className="py-2.5 px-3 font-semibold">{t.applicationsPage.schemeName}</th>
                  <th className="py-2.5 px-3 font-semibold">{t.applicationsPage.status}</th>
                  <th className="py-2.5 px-3 font-semibold">{t.applicationsPage.completeness}</th>
                  <th className="py-2.5 px-3 font-semibold text-right">{t.applicationsPage.action}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {drafts.map((d) => (
                  <tr key={d.id} className="hover:bg-stone-50">
                    <td className="py-2.5 px-3 font-medium text-stone-900">
                      {language === 'hi' ? d.scheme_name_hi : d.scheme_name_en}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded text-[10px]">
                        {d.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-bold text-stone-800">
                      {d.completeness_percentage}%
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {d.has_pdf && (
                        <a
                          href={getCSCPackagePdfUrl(d.id, sessionId)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center space-x-1 px-2.5 py-1 bg-stone-100 hover:bg-stone-200 text-stone-800 rounded font-semibold text-[11px] transition"
                        >

                          <FileTextIcon size={12} />
                          <span>{t.applicationsPage.download}</span>
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
