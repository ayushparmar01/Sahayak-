import React, { useState, useEffect, useRef } from 'react';
import { useSession } from '../context/SessionContext';
import { translations } from '../i18n/translations';
import { Card } from '../components/Card';
import { FileTextIcon, ShieldCheckIcon } from '../components/Icons';
import {
  uploadDocument,
  fetchDocuments,
  fetchDocumentDetail,
  confirmDocument,
  deleteDocument,
  fetchConsistencyReport,
} from '../services/api';
import type { DocumentRecordDTO, ConsistencyReport } from '../types';

export const DocumentsPage: React.FC = () => {
  const { language, session, refreshProfile } = useSession();
  const sessionId = session.sessionId;
  const citizenId = session.citizenId;
  const t = translations[language];


  const [documents, setDocuments] = useState<DocumentRecordDTO[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedDocType, setSelectedDocType] = useState<string>('');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // Review modal state
  const [activeDoc, setActiveDoc] = useState<DocumentRecordDTO | null>(null);
  const [activePageTab, setActivePageTab] = useState<number>(1);
  const [corrections, setCorrections] = useState<Record<string, any>>({});
  const [applyToProfile, setApplyToProfile] = useState<boolean>(false);
  const [isSavingReview, setIsSavingReview] = useState<boolean>(false);
  const [reviewMessage, setReviewMessage] = useState<string | null>(null);

  // Consistency audit state
  const [consistencyReport, setConsistencyReport] = useState<ConsistencyReport | null>(null);
  const [isLoadingConsistency, setIsLoadingConsistency] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load documents on mount or citizen change
  useEffect(() => {
    if (citizenId) {
      loadDocuments();
    }
  }, [citizenId, sessionId]);

  const loadDocuments = async () => {
    if (!citizenId) return;
    try {
      const data = await fetchDocuments(citizenId, sessionId);
      setDocuments(data);
    } catch (err: any) {
      console.error('Failed to load documents:', err);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadError(null);
      setUploadSuccess(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!citizenId) {
      setUploadError(language === 'hi' ? 'कृपया पहले सत्र प्रारंभ करें।' : 'Please start a session first.');
      return;
    }
    if (!selectedFile) {
      setUploadError(language === 'hi' ? 'कृपया अपलोड करने हेतु फ़ाइल चुनें।' : 'Please select a file to upload.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const res = await uploadDocument(
        citizenId,
        selectedFile,
        selectedDocType || undefined,
        sessionId
      );
      setUploadSuccess(res.message || 'दस्तावेज़ सफलतापूर्वक अपलोड हुआ');
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      await loadDocuments();
      // Auto open review modal for newly uploaded document
      handleOpenReview(res);
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleOpenReview = async (doc: DocumentRecordDTO) => {
    try {
      const detail = await fetchDocumentDetail(doc.id, sessionId);
      setActiveDoc(detail);
      setActivePageTab(1);
      setCorrections(detail.user_corrections || {});
      setApplyToProfile(false);
      setReviewMessage(null);
    } catch (err: any) {
      console.error('Failed to load document detail:', err);
    }
  };

  const handleSaveReview = async (confirmed: boolean) => {
    if (!activeDoc) return;
    setIsSavingReview(true);
    setReviewMessage(null);

    try {
      const res = await confirmDocument(
        activeDoc.id,
        {
          confirmed,
          corrections,
          apply_to_profile: applyToProfile,
        },
        sessionId
      );
      setReviewMessage(res.message);
      await loadDocuments();
      if (applyToProfile) {
        await refreshProfile();
      }
      setTimeout(() => {
        setActiveDoc(null);
      }, 1000);
    } catch (err: any) {
      setReviewMessage(`Error: ${err.message}`);
    } finally {
      setIsSavingReview(false);
    }
  };

  const handleDelete = async (docId: string) => {
    if (!window.confirm(language === 'hi' ? 'क्या आप इस दस्तावेज़ को हटाना चाहते हैं?' : 'Delete this document?')) {
      return;
    }
    try {
      await deleteDocument(docId, sessionId);
      await loadDocuments();
      if (activeDoc?.id === docId) {
        setActiveDoc(null);
      }
    } catch (err: any) {
      alert(`Error deleting document: ${err.message}`);
    }
  };

  const handleRunConsistency = async () => {
    if (!citizenId) return;
    setIsLoadingConsistency(true);
    try {
      const report = await fetchConsistencyReport(citizenId, sessionId);
      setConsistencyReport(report);
    } catch (err: any) {
      console.error('Failed to run consistency report:', err);
    } finally {
      setIsLoadingConsistency(false);
    }
  };

  const formatDocType = (typeStr: string) => {
    const map = t.documentsPage.docTypes as Record<string, string>;
    return map[typeStr] || typeStr.replace(/_/g, ' ').toUpperCase();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-stone-900">{t.documentsPage.title}</h1>
        <p className="text-stone-600 text-xs sm:text-sm mt-1">{t.documentsPage.subtitle}</p>
      </div>

      {/* Security Banner */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-xs text-emerald-950 flex items-start space-x-3">
        <ShieldCheckIcon size={20} className="text-emerald-700 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold block mb-0.5">
            {language === 'hi' ? 'शून्य-आधार भंडारण एवं डेटा गोपनीयता (Privacy Assurance):' : 'Zero Aadhaar Storage & Privacy Assurance:'}
          </span>
          <p>{t.documentsPage.securityBanner}</p>
        </div>
      </div>

      {/* Upload Box */}
      <Card className="p-6">
        <h2 className="text-base font-bold text-stone-900 mb-2">{t.documentsPage.uploadZoneTitle}</h2>
        <p className="text-xs text-stone-500 mb-4">{t.documentsPage.uploadZoneSubtitle}</p>

        <form onSubmit={handleUpload} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                {language === 'hi' ? 'फ़ाइल चुनें (Choose File)' : 'Choose File'}
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={handleFileChange}
                className="w-full text-xs text-stone-700 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-emerald-50 file:text-emerald-800 hover:file:bg-emerald-100 cursor-pointer border border-stone-300 rounded-lg p-1.5"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                {t.documentsPage.selectDocType}
              </label>
              <select
                value={selectedDocType}
                onChange={(e) => setSelectedDocType(e.target.value)}
                className="w-full text-xs bg-white border border-stone-300 rounded-lg p-2 text-stone-800 focus:ring-2 focus:ring-emerald-600 focus:outline-none"
              >
                <option value="">{t.documentsPage.autoDetect}</option>
                <option value="land_khatauni">{t.documentsPage.docTypes.land_khatauni}</option>
                <option value="aadhaar_card_masked">{t.documentsPage.docTypes.aadhaar_card_masked}</option>
                <option value="ration_card">{t.documentsPage.docTypes.ration_card}</option>
                <option value="income_certificate">{t.documentsPage.docTypes.income_certificate}</option>
                <option value="bank_passbook">{t.documentsPage.docTypes.bank_passbook}</option>
                <option value="birth_certificate">{t.documentsPage.docTypes.birth_certificate}</option>
                <option value="crop_sowing_record">{t.documentsPage.docTypes.crop_sowing_record}</option>
                <option value="bpl_certificate">{t.documentsPage.docTypes.bpl_certificate}</option>
                <option value="other">{t.documentsPage.docTypes.other}</option>
              </select>
            </div>
          </div>

          {selectedFile && (
            <div className="text-xs text-stone-600 bg-stone-50 p-2.5 rounded-lg border border-stone-200">
              <span className="font-semibold text-stone-800">{selectedFile.name}</span>{' '}
              ({(selectedFile.size / 1024).toFixed(1)} KB) • {selectedFile.type || 'unknown type'}
            </div>
          )}

          {uploadError && (
            <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 p-3 rounded-lg font-medium">
              {uploadError}
            </div>
          )}

          {uploadSuccess && (
            <div className="text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 p-3 rounded-lg font-medium">
              {uploadSuccess}
            </div>
          )}

          <div className="flex items-center space-x-3">
            <button
              type="submit"
              disabled={isUploading || !selectedFile}
              className={`px-4 py-2.5 rounded-lg text-xs font-bold transition flex items-center space-x-2 ${
                isUploading || !selectedFile
                  ? 'bg-stone-200 text-stone-400 cursor-not-allowed'
                  : 'bg-emerald-800 hover:bg-emerald-900 text-white shadow-sm'
              }`}
            >
              {isUploading ? (
                <>
                  <span className="animate-spin inline-block w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full" />
                  <span>{t.documentsPage.uploading}</span>
                </>
              ) : (
                <>
                  <FileTextIcon size={14} />
                  <span>{t.documentsPage.uploadBtn}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </Card>

      {/* Uploaded Documents List */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-stone-900">{t.documentsPage.myDocuments}</h2>
          <span className="text-xs text-stone-500 font-medium">
            {documents.length} {language === 'hi' ? 'दस्तावेज़ उपलब्ध' : 'documents recorded'}
          </span>
        </div>

        {documents.length === 0 ? (
          <div className="text-center py-8 text-xs text-stone-500 bg-stone-50 rounded-lg border border-dashed border-stone-200">
            {t.documentsPage.noDocs}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {documents.map((doc) => {
              const isConfirmed = doc.citizen_confirmed;
              return (
                <div
                  key={doc.id}
                  className="bg-stone-50 border border-stone-200 rounded-xl p-4 flex flex-col justify-between space-y-3"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-bold text-sm text-stone-900">{formatDocType(doc.document_type)}</h3>
                        <p className="text-[11px] text-stone-500 truncate max-w-xs">{doc.file_name || doc.id}</p>
                      </div>

                      {/* Status Chip */}
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          isConfirmed
                            ? 'bg-emerald-100 text-emerald-800'
                            : doc.review_status === 'REJECTED'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {isConfirmed
                          ? t.documentsPage.statusConfirmed
                          : doc.review_status === 'REJECTED'
                          ? t.documentsPage.statusRejected
                          : t.documentsPage.statusUnreviewed}
                      </span>
                    </div>

                    {/* Metadata tags */}
                    <div className="flex flex-wrap gap-1.5 text-[10px]">
                      <span className="bg-stone-200 text-stone-700 px-2 py-0.5 rounded">
                        {doc.page_count} {t.documentsPage.pageLabel}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded font-medium ${
                          doc.is_mock
                            ? 'bg-purple-100 text-purple-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {doc.is_mock ? t.documentsPage.mockOcrBadge : t.documentsPage.localPdfBadge}
                      </span>
                      {doc.masked_identifier && (
                        <span className="bg-stone-200 text-stone-800 px-2 py-0.5 rounded font-mono">
                          {doc.masked_identifier}
                        </span>
                      )}
                    </div>

                    {/* Extracted preview */}
                    {doc.extracted_fields && Object.keys(doc.extracted_fields).length > 0 && (
                      <div className="bg-white p-2.5 rounded-lg border border-stone-200 text-xs space-y-1">
                        {Object.entries(doc.extracted_fields)
                          .slice(0, 3)
                          .map(([k, v]) => (
                            <div key={k} className="flex justify-between text-[11px]">
                              <span className="text-stone-500">{k}:</span>
                              <span className="font-medium text-stone-800">{String(v)}</span>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>

                  <div className="pt-2 border-t border-stone-200 flex items-center justify-between">
                    <button
                      onClick={() => handleOpenReview(doc)}
                      className="px-3 py-1.5 bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg text-xs font-semibold transition"
                    >
                      {language === 'hi' ? 'समीक्षा एवं पुष्टि करें' : 'Review & Confirm'}
                    </button>
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="px-2.5 py-1 text-rose-600 hover:text-rose-800 text-xs font-medium transition"
                    >
                      {t.documentsPage.deleteDocBtn}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* Cross-Document Consistency Audit Panel */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-stone-900">{t.documentsPage.consistencyTitle}</h2>
            <p className="text-xs text-stone-500 mt-0.5">{t.documentsPage.consistencySubtitle}</p>
          </div>
          <button
            onClick={handleRunConsistency}
            disabled={isLoadingConsistency || documents.length === 0}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition ${
              documents.length === 0
                ? 'bg-stone-100 text-stone-400 cursor-not-allowed'
                : 'bg-blue-700 hover:bg-blue-800 text-white'
            }`}
          >
            {isLoadingConsistency ? '...' : t.documentsPage.runConsistencyBtn}
          </button>
        </div>

        {consistencyReport && (
          <div className="space-y-3 pt-2">
            <div
              className={`p-3 rounded-lg text-xs font-medium border ${
                consistencyReport.has_variations
                  ? 'bg-amber-50 text-amber-900 border-amber-200'
                  : 'bg-emerald-50 text-emerald-900 border-emerald-200'
              }`}
            >
              {language === 'hi' ? consistencyReport.summary_hi : consistencyReport.summary_en}
            </div>

            {consistencyReport.checks.length > 0 && (
              <div className="space-y-2">
                {consistencyReport.checks.map((chk) => {
                  const isMatch = chk.status === 'MATCH';
                  const isVar = chk.status === 'VARIATION';
                  return (
                    <div
                      key={chk.check_id}
                      className="bg-stone-50 p-3 rounded-lg border border-stone-200 text-xs flex items-start justify-between space-x-3"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              isMatch
                                ? 'bg-emerald-100 text-emerald-800'
                                : isVar
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-rose-100 text-rose-800'
                            }`}
                          >
                            {chk.status}
                          </span>
                          <span className="font-semibold text-stone-800">{chk.field_name}</span>
                          <span className="text-[10px] text-stone-400">({chk.document_type})</span>
                        </div>
                        <p className="text-stone-600">
                          {language === 'hi' ? chk.message_hi : chk.message_en}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Review & Confirmation Modal */}
      {activeDoc && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-5 my-8">
            <div className="flex items-start justify-between border-b border-stone-200 pb-3">
              <div>
                <h3 className="font-bold text-lg text-stone-900">{t.documentsPage.reviewModalTitle}</h3>
                <p className="text-xs text-stone-500">{formatDocType(activeDoc.document_type)}</p>
              </div>
              <button
                onClick={() => setActiveDoc(null)}
                className="text-stone-400 hover:text-stone-700 text-sm font-bold p-1"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-stone-600">{t.documentsPage.reviewModalDesc}</p>

            {/* Provider and Masked info banner */}
            <div className="bg-stone-50 p-3 rounded-lg border border-stone-200 text-xs flex items-center justify-between">
              <div>
                <span className="text-stone-400">प्रदाता (Provider): </span>
                <span className="font-semibold text-stone-800">{activeDoc.ocr_provider}</span>{' '}
                <span className="text-[10px] text-purple-700 font-bold">
                  ({activeDoc.is_mock ? 'सिम्युलेटेड मॉक' : 'लोकल डिजिटल'})
                </span>
              </div>
              {activeDoc.masked_identifier && (
                <div>
                  <span className="text-stone-400">पहचानकर्ता: </span>
                  <span className="font-mono font-bold text-stone-800">{activeDoc.masked_identifier}</span>
                </div>
              )}
            </div>

            {/* Simulated Mock OCR Warning Banner */}
            {activeDoc.is_mock && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-900 flex items-start space-x-2">
                <span className="font-bold text-amber-700 text-sm">⚠️</span>
                <div>
                  <span className="font-bold block">
                    {language === 'hi' ? 'सिम्युलेटेड मॉक ओसीआर (Demo Simulation Only):' : 'Simulated Mock OCR (Demo Simulation Only):'}
                  </span>
                  <span>
                    {language === 'hi'
                      ? 'यह दस्तावेज़ एक सिमुलेटेड मॉक टेम्पलेट द्वारा संसाधित किया गया है। निष्कर्षित मान वास्तविक स्कैन से नहीं हैं। कृपया पुष्टि करने से पहले मूल दस्तावेज़ से मिलान करें।'
                      : 'This document was processed using a deterministic simulated mock template. Values are demonstration data and must be verified against physical originals.'}
                  </span>
                </div>
              </div>
            )}

            {/* Multi-Page Tabs */}
            {activeDoc.page_extractions && activeDoc.page_extractions.length > 1 && (
              <div className="space-y-2">
                <span className="text-xs font-bold text-stone-700">{t.documentsPage.pageExtractions}</span>
                <div className="flex space-x-1.5 border-b border-stone-200 pb-1">
                  {activeDoc.page_extractions.map((p) => (
                    <button
                      key={p.page_number}
                      onClick={() => setActivePageTab(p.page_number)}
                      className={`px-3 py-1 text-xs font-semibold rounded-t-lg transition ${
                        activePageTab === p.page_number
                          ? 'bg-emerald-800 text-white'
                          : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                      }`}
                    >
                      {t.documentsPage.pageLabel} {p.page_number}
                    </button>
                  ))}
                </div>

                {/* Page raw text */}
                {activeDoc.page_extractions.find((p) => p.page_number === activePageTab)?.raw_text && (
                  <div className="bg-stone-900 text-stone-200 font-mono text-[11px] p-3 rounded-lg max-h-32 overflow-y-auto whitespace-pre-wrap">
                    {activeDoc.page_extractions.find((p) => p.page_number === activePageTab)?.raw_text}
                  </div>
                )}
              </div>
            )}

            {/* Extracted Fields Editor */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-stone-800">{t.documentsPage.extractedFields}</h4>
              <div className="bg-stone-50 p-3 rounded-lg border border-stone-200 space-y-2 max-h-52 overflow-y-auto">
                {Object.entries(activeDoc.extracted_fields || {}).map(([key, origVal]) => {
                  const currentVal = corrections[key] !== undefined ? corrections[key] : origVal;
                  return (
                    <div key={key} className="grid grid-cols-1 sm:grid-cols-3 gap-2 items-center text-xs">
                      <span className="font-medium text-stone-700 truncate">{key}:</span>
                      <input
                        type="text"
                        value={String(currentVal ?? '')}
                        onChange={(e) => {
                          const val = e.target.value;
                          setCorrections((prev) => ({
                            ...prev,
                            [key]: val === '' ? null : !isNaN(Number(val)) && !key.includes('number') && !key.includes('code') ? Number(val) : val,
                          }));
                        }}
                        className="sm:col-span-2 text-xs bg-white border border-stone-300 rounded px-2.5 py-1 text-stone-900 focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                      />
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Profile Sync Checkbox */}
            <label className="flex items-start space-x-2.5 text-xs text-stone-700 bg-emerald-50 p-3 rounded-lg border border-emerald-200 cursor-pointer">
              <input
                type="checkbox"
                checked={applyToProfile}
                onChange={(e) => setApplyToProfile(e.target.checked)}
                className="mt-0.5 rounded text-emerald-700 focus:ring-emerald-600"
              />
              <span className="font-medium">{t.documentsPage.applyToProfileLabel}</span>
            </label>

            {reviewMessage && (
              <div className="text-xs p-3 rounded-lg bg-emerald-100 text-emerald-900 font-semibold">
                {reviewMessage}
              </div>
            )}

            {/* Modal Actions */}
            <div className="flex items-center justify-end space-x-3 pt-3 border-t border-stone-200">
              <button
                type="button"
                onClick={() => handleSaveReview(false)}
                disabled={isSavingReview}
                className="px-3.5 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50 rounded-lg transition"
              >
                {t.documentsPage.rejectDocBtn}
              </button>
              <button
                type="button"
                onClick={() => handleSaveReview(true)}
                disabled={isSavingReview}
                className="px-4 py-2 text-xs font-bold bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg transition shadow-sm"
              >
                {isSavingReview ? '...' : t.documentsPage.confirmDocBtn}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
