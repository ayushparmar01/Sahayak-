import React, { useState } from 'react';
import { useSession } from '../context/SessionContext';
import { translations } from '../i18n/translations';
import { Card } from '../components/Card';
import { ShieldCheckIcon, Trash2Icon, CheckCircleIcon } from '../components/Icons';

export const PrivacyPage: React.FC = () => {
  const { language, wipeAndEndSession } = useSession();
  const t = translations[language];
  const [purged, setPurged] = useState(false);

  const handlePurge = async () => {
    await wipeAndEndSession();
    setPurged(true);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-stone-900">{t.privacyPage.title}</h1>
        <p className="text-stone-600 text-xs sm:text-sm mt-1">{t.privacyPage.subtitle}</p>
      </div>

      {purged && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-xs text-emerald-900 flex items-center space-x-2">
          <CheckCircleIcon size={18} className="text-emerald-700 shrink-0" />
          <span className="font-semibold">{t.privacyPage.wipeSuccess}</span>
        </div>
      )}

      {/* Zero Aadhaar Storage Card */}
      <Card className="p-6 space-y-3">
        <div className="flex items-center space-x-3 text-emerald-800">
          <ShieldCheckIcon size={24} />
          <h2 className="font-bold text-base text-stone-900">{t.privacyPage.zeroAadhaarTitle}</h2>
        </div>
        <p className="text-xs sm:text-sm text-stone-700 leading-relaxed">
          {t.privacyPage.zeroAadhaarBody}
        </p>
      </Card>

      {/* Shared Device & Kiosk Card */}
      <Card className="p-6 space-y-3">
        <div className="flex items-center space-x-3 text-amber-800">
          <ShieldCheckIcon size={24} />
          <h2 className="font-bold text-base text-stone-900">{t.privacyPage.sharedDeviceTitle}</h2>
        </div>
        <p className="text-xs sm:text-sm text-stone-700 leading-relaxed">
          {t.privacyPage.sharedDeviceBody}
        </p>

        <div className="pt-4 border-t border-stone-200 flex items-center justify-between">
          <span className="text-xs text-stone-500">
            कियोस्क ऑपरेटर अथवा साझा फोन उपयोगकर्ता हेतु त्वरित नियंत्रण:
          </span>
          <button
            onClick={handlePurge}
            className="flex items-center space-x-1.5 bg-rose-700 hover:bg-rose-800 text-white font-semibold px-4 py-2 rounded-lg text-xs transition shadow-sm"
          >
            <Trash2Icon size={14} />
            <span>{t.privacyPage.wipeDataBtn}</span>
          </button>
        </div>
      </Card>

      {/* DPDP Act Architecture Alignment Checklist */}
      <Card className="p-6 space-y-3 bg-stone-50 border-stone-200">
        <h2 className="font-bold text-sm text-stone-900">
          वास्तुशिल्प सुरक्षा एवं सत्यापन गेट्स (Security Architecture Gates):
        </h2>
        <ul className="text-xs text-stone-700 space-y-2">
          <li className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-600" />
            <span>गेट 6.1: डेटाबेस और डिस्क पर शून्य आधार भंडारण (सत्यापन परीक्षण शामिल)</span>
          </li>
          <li className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-600" />
            <span>गेट 6.2: इन-मेमोरी आधार मास्किंग (XXXX-XXXX-Last4)</span>
          </li>
          <li className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-600" />
            <span>गेट 6.3: साझा ब्राउज़र सुरक्षा (लोकल स्टोरेज में शून्य व्यक्तिगत डेटा)</span>
          </li>
          <li className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-600" />
            <span>गेट 6.4: फ्रंटएंड बंडल में सर्वर कुंजियों का पूर्ण अभाव</span>
          </li>
        </ul>
      </Card>
    </div>
  );
};
