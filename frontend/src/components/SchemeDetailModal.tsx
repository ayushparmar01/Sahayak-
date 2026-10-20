import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { useSession } from '../context/SessionContext';
import { translations } from '../i18n/translations';
import { SchemeDetail, EligibilityAssessment } from '../types/index.ts';
import { fetchSchemeDetail, assessEligibility } from '../services/api';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorAlert } from './ErrorAlert';
import {
  ExternalLinkIcon,
  ClockIcon,
  ShieldCheckIcon,
  CheckCircleIcon,
  AlertTriangleIcon,
} from './Icons';

interface SchemeDetailModalProps {
  schemeId: string;
  onClose: () => void;
}

export const SchemeDetailModal: React.FC<SchemeDetailModalProps> = ({ schemeId, onClose }) => {
  const { language, session } = useSession();
  const t = translations[language];
  const m = t.schemesPage.modal;
  const navigate = useNavigate();

  const [detail, setDetail] = useState<SchemeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<'overview' | 'rules' | 'assess'>('overview');
  const [assessment, setAssessment] = useState<EligibilityAssessment | null>(null);
  const [assessing, setAssessing] = useState(false);
  const [assessError, setAssessError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const loadDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchSchemeDetail(schemeId);
        if (isMounted) setDetail(data);
      } catch (err) {
        if (isMounted) setError((err as Error).message || 'Failed to load scheme details');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadDetail();
    return () => {
      isMounted = false;
    };
  }, [schemeId]);

  const handleRunAssessment = async () => {
    if (!detail) return;
    setAssessing(true);
    setAssessError(null);
    try {
      const res = await assessEligibility(detail.id, undefined, session.sessionId);
      setAssessment(res);
      setActiveTab('assess');
    } catch (err) {
      setAssessError((err as Error).message || 'Assessment failed');
    } finally {
      setAssessing(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ELIGIBLE':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
            <CheckCircleIcon size={14} className="text-emerald-700" />
            <span>{m.statusEligible}</span>
          </span>
        );
      case 'POTENTIALLY_ELIGIBLE':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
            <AlertTriangleIcon size={14} className="text-amber-700" />
            <span>{m.statusPotentiallyEligible}</span>
          </span>
        );
      case 'INELIGIBLE':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-900 border border-rose-300">
            <ShieldCheckIcon size={14} className="text-rose-700" />
            <span>{m.statusIneligible}</span>
          </span>
        );
      case 'NEEDS_MORE_INFO':
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-900 border border-blue-300">
            <ShieldCheckIcon size={14} className="text-blue-700" />
            <span>{m.statusNeedsMoreInfo}</span>
          </span>
        );
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-stone-900/60 backdrop-blur-sm overflow-y-auto"
    >
      <div className="bg-white rounded-2xl shadow-2xl border border-stone-200 max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden my-auto">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-stone-200 bg-stone-50 flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-mono font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                {detail?.code || schemeId}
              </span>
              <span className="text-[11px] font-medium text-stone-600 bg-stone-200 px-2 py-0.5 rounded">
                {detail?.jurisdiction === 'CENTRAL_SECTOR'
                  ? t.schemesPage.centralSector
                  : t.schemesPage.centrallySponsored}
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-stone-900 mt-1">
              {language === 'hi' ? detail?.name_hi : detail?.name_en}
            </h2>
            <p className="text-xs text-stone-500 mt-0.5">{detail?.ministry}</p>
          </div>
          <button
            onClick={onClose}
            className="text-stone-400 hover:text-stone-700 p-1.5 rounded-lg hover:bg-stone-200 transition text-sm font-semibold"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Tab Bar */}
        <div className="flex border-b border-stone-200 px-6 bg-white gap-2 sm:gap-6 text-xs sm:text-sm font-medium">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-3 border-b-2 transition ${
              activeTab === 'overview'
                ? 'border-emerald-600 text-emerald-800 font-bold'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            {m.overview}
          </button>
          <button
            onClick={() => setActiveTab('rules')}
            className={`py-3 border-b-2 transition ${
              activeTab === 'rules'
                ? 'border-emerald-600 text-emerald-800 font-bold'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            {m.rulesAndCriteria} ({detail?.rules.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('assess')}
            className={`py-3 border-b-2 transition flex items-center space-x-1.5 ${
              activeTab === 'assess'
                ? 'border-emerald-600 text-emerald-800 font-bold'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <span>{m.assessmentTab}</span>
            {assessment && (
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            )}
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs sm:text-sm text-stone-700">
          {loading && <LoadingSpinner label={t.common.loading} />}
          {error && <ErrorAlert message={error} />}

          {!loading && !error && detail && (
            <>
              {/* TAB 1: OVERVIEW */}
              {activeTab === 'overview' && (
                <div className="space-y-5">
                  {/* Benefit Card */}
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 space-y-2">
                    <span className="text-xs font-bold text-emerald-900 block">
                      {language === 'hi'
                        ? (detail.benefit_metric_label_hi || t.schemesPage.annualBenefit)
                        : (detail.benefit_metric_label_en || 'Benefit / Facility')}{': '}
                      <span className="text-sm font-extrabold text-emerald-950">
                        {language === 'hi'
                          ? (detail.benefit_amount_display_hi || `₹${detail.max_annual_benefit_inr.toLocaleString('en-IN')}`)
                          : (detail.benefit_amount_display_en || `₹${detail.max_annual_benefit_inr.toLocaleString('en-IN')}`)}
                      </span>
                    </span>
                    <p className="text-xs leading-relaxed text-emerald-900">
                      {language === 'hi' ? detail.benefit_summary_hi : detail.benefit_summary_en}
                    </p>
                  </div>

                  {/* Target Beneficiary */}
                  <div>
                    <h3 className="font-bold text-stone-900 text-xs uppercase tracking-wider mb-1">
                      {m.targetBeneficiary}
                    </h3>
                    <p className="bg-stone-50 p-3 rounded-lg border border-stone-200">
                      {language === 'hi' ? detail.target_group_hi : detail.target_group_en}
                    </p>
                  </div>

                  {/* Application Process */}
                  {detail.application_process_hi && (
                    <div>
                      <h3 className="font-bold text-stone-900 text-xs uppercase tracking-wider mb-1">
                        {m.applicationProcess}
                      </h3>
                      <p className="bg-stone-50 p-3 rounded-lg border border-stone-200 leading-relaxed">
                        {language === 'hi'
                          ? detail.application_process_hi
                          : detail.application_process_en}
                      </p>
                    </div>
                  )}

                  {/* Required Documents */}
                  {detail.documents_required && detail.documents_required.length > 0 && (
                    <div>
                      <h3 className="font-bold text-stone-900 text-xs uppercase tracking-wider mb-1">
                        {m.requiredDocs}
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {detail.documents_required.map((doc, idx) => (
                          <span
                            key={idx}
                            className="bg-stone-100 text-stone-800 border border-stone-300 px-2.5 py-1 rounded-lg text-xs font-medium"
                          >
                            📄 {doc}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Caveats & Exclusions */}
                  {detail.caveats_hi && (
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-xs text-amber-950">
                      <span className="font-bold block mb-1">⚠️ {m.caveats}</span>
                      <p className="leading-relaxed">
                        {language === 'hi' ? detail.caveats_hi : detail.caveats_en}
                      </p>
                    </div>
                  )}

                  {/* Sourced Reference */}
                  <div className="pt-3 border-t border-stone-200 flex flex-wrap items-center justify-between text-xs text-stone-500 gap-2">
                    <span className="flex items-center space-x-1">
                      <ClockIcon size={13} className="text-stone-400" />
                      <span>
                        {t.schemesPage.lastVerified} {detail.last_verified_date} (v{detail.rule_version})
                      </span>
                    </span>
                    <a
                      href={detail.official_portal_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center space-x-1 font-semibold text-emerald-700 hover:text-emerald-900 hover:underline"
                    >
                      <span>{t.schemesPage.viewOfficial}</span>
                      <ExternalLinkIcon size={13} />
                    </a>
                  </div>
                </div>
              )}

              {/* TAB 2: RULES & CRITERIA */}
              {activeTab === 'rules' && (
                <div className="space-y-4">
                  <div className="text-xs text-stone-600 bg-stone-50 p-3 rounded-lg border border-stone-200">
                    आधिकारिक दिशानिर्देशों से संकलित एवं तिथि-सत्यापित पात्रता नियम। प्रत्येक नियम का स्रोत
                    प्रमाणित है।
                  </div>

                  <div className="space-y-3">
                    {detail.rules.map((rule) => (
                      <div
                        key={rule.id}
                        className="p-4 rounded-xl border border-stone-200 bg-white shadow-sm space-y-2"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              rule.rule_type === 'EXCLUSION'
                                ? 'bg-rose-100 text-rose-800 border border-rose-200'
                                : rule.rule_type === 'EXTERNAL_VERIFICATION'
                                ? 'bg-blue-100 text-blue-800 border border-blue-200'
                                : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            }`}
                          >
                            {rule.rule_type}
                          </span>
                          <span className="text-[11px] font-mono text-stone-400">
                            {rule.rule_code}
                          </span>
                        </div>
                        <p className="font-semibold text-stone-900 text-xs sm:text-sm">
                          {language === 'hi' ? rule.description_hi : rule.description_en}
                        </p>
                        <p className="text-[11px] text-stone-500 italic">
                          स्रोत प्रमाण: {rule.source_citation}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 3: LIVE ASSESSMENT */}
              {activeTab === 'assess' && (
                <div className="space-y-5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-stone-50 p-4 rounded-xl border border-stone-200">
                    <div>
                      <span className="font-bold text-stone-900 text-xs block">
                        सत्यापित नियम इंजन (Deterministic Engine v{detail.rule_version})
                      </span>
                      <p className="text-xs text-stone-600 mt-0.5">
                        आपकी दर्ज जनसांख्यिकीय प्रोफ़ाइल का आधिकारिक नियमों से सीधा मिलान किया जाता है।
                      </p>
                    </div>
                    <button
                      onClick={handleRunAssessment}
                      disabled={assessing}
                      className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 disabled:bg-stone-300 text-white rounded-lg text-xs font-semibold transition shrink-0 shadow-sm"
                    >
                      {assessing ? m.assessing : m.runAssessmentBtn}
                    </button>
                  </div>

                  {assessError && <ErrorAlert message={assessError} />}

                  {/* Assessment Results Card */}
                  {assessment && (
                    <div className="space-y-5 pt-2">
                      {/* Status Banner */}
                      <div className="p-4 rounded-xl border border-stone-200 bg-white shadow-sm space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-stone-500 uppercase">
                            आकलन परिणाम (Evaluation Result)
                          </span>
                          {getStatusBadge(assessment.status)}
                        </div>

                        <p className="text-xs sm:text-sm font-medium leading-relaxed bg-stone-50 p-3 rounded-lg border border-stone-200 text-stone-800">
                          {language === 'hi'
                            ? assessment.summary_explanation_hi
                            : assessment.summary_explanation_en}
                        </p>
                      </div>

                      {/* Satisfied Conditions */}
                      {assessment.conditions_satisfied.length > 0 && (
                        <div>
                          <h4 className="text-xs font-bold text-emerald-900 uppercase tracking-wider mb-2">
                            ✓ {m.satisfiedConditions} ({assessment.conditions_satisfied.length})
                          </h4>
                          <div className="space-y-2">
                            {assessment.conditions_satisfied.map((cond) => (
                              <div
                                key={cond.id}
                                className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-lg text-xs space-y-1"
                              >
                                <div className="font-semibold text-emerald-950">
                                  {language === 'hi' ? cond.title_hi : cond.title_en}
                                </div>
                                <div className="text-stone-700">
                                  {language === 'hi' ? cond.outcome_detail_hi : cond.outcome_detail_en}
                                </div>
                                <div className="text-[11px] text-stone-400 italic">
                                  {cond.source_citation}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Failed Conditions */}
                      {assessment.conditions_failed.length > 0 && (
                        <div>
                          <h4 className="text-xs font-bold text-rose-900 uppercase tracking-wider mb-2">
                            ✗ {m.failedConditions} ({assessment.conditions_failed.length})
                          </h4>
                          <div className="space-y-2">
                            {assessment.conditions_failed.map((cond) => (
                              <div
                                key={cond.id}
                                className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs space-y-1"
                              >
                                <div className="font-semibold text-rose-950">
                                  {language === 'hi' ? cond.title_hi : cond.title_en}
                                </div>
                                <div className="text-rose-900">
                                  {language === 'hi' ? cond.outcome_detail_hi : cond.outcome_detail_en}
                                </div>
                                <div className="text-[11px] text-stone-400 italic">
                                  {cond.source_citation}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Missing Information */}
                      {assessment.missing_information.length > 0 && (
                        <div>
                          <h4 className="text-xs font-bold text-blue-900 uppercase tracking-wider mb-2">
                            ℹ {m.missingFields} ({assessment.missing_information.length})
                          </h4>
                          <div className="space-y-2">
                            {assessment.missing_information.map((miss, idx) => (
                              <div
                                key={idx}
                                className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                              >
                                <div>
                                  <span className="font-bold text-blue-950 block">
                                    {language === 'hi' ? miss.label_hi : miss.label_en}
                                  </span>
                                  <span className="text-blue-900 text-[11px]">
                                    {language === 'hi' ? miss.reason_hi : miss.reason_en}
                                  </span>
                                </div>
                                <button
                                  onClick={() => {
                                    onClose();
                                    navigate('/profile');
                                  }}
                                  className="px-3 py-1 bg-blue-700 hover:bg-blue-800 text-white rounded text-[11px] font-semibold transition shrink-0"
                                >
                                  {m.updateProfilePrompt}
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Pending External Verifications */}
                      {assessment.pending_verifications.length > 0 && (
                        <div>
                          <h4 className="text-xs font-bold text-stone-700 uppercase tracking-wider mb-2">
                            ⏳ {m.pendingVerifications} ({assessment.pending_verifications.length})
                          </h4>
                          <div className="space-y-2">
                            {assessment.pending_verifications.map((cond) => (
                              <div
                                key={cond.id}
                                className="p-3 bg-stone-50 border border-stone-200 rounded-lg text-xs space-y-1"
                              >
                                <div className="font-semibold text-stone-900">
                                  {language === 'hi' ? cond.title_hi : cond.title_en}
                                </div>
                                <div className="text-stone-600">
                                  {language === 'hi' ? cond.outcome_detail_hi : cond.outcome_detail_en}
                                </div>
                                <div className="text-[11px] text-stone-400 italic">
                                  {cond.source_citation}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Next Steps */}
                      <div className="bg-emerald-50/50 border border-emerald-300 rounded-xl p-3.5 space-y-1">
                        <span className="font-bold text-xs text-emerald-950 block">
                          👉 {m.nextSteps}
                        </span>
                        <p className="text-xs text-emerald-900 leading-relaxed">
                          {language === 'hi'
                            ? assessment.next_recommended_action_hi
                            : assessment.next_recommended_action_en}
                        </p>
                      </div>

                      {/* Disclaimer */}
                      <div className="text-[11px] text-stone-500 bg-stone-100 p-3 rounded-lg border border-stone-200 leading-relaxed">
                        <span className="font-semibold block mb-0.5">{m.disclaimerTitle}</span>
                        {language === 'hi' ? assessment.disclaimer_hi : assessment.disclaimer_en}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-stone-200 bg-stone-50 flex justify-between items-center text-xs">
          <span className="text-stone-500">
            SAHAYAK • Deviathon 2.0 • Deterministic Rules Engine
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-stone-200 hover:bg-stone-300 text-stone-800 rounded-lg font-medium transition"
          >
            {m.close}
          </button>
        </div>
      </div>
    </div>
  );
};
