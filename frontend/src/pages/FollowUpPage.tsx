import React from 'react';
import { useSession } from '../context/SessionContext';
import { translations } from '../i18n/translations';
import { Card } from '../components/Card';
import { StatusPill } from '../components/StatusPill';
import { ClockIcon } from '../components/Icons';

export const FollowUpPage: React.FC = () => {
  const { language } = useSession();
  const t = translations[language];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-stone-900">{t.followupPage.title}</h1>
        <p className="text-stone-600 text-xs sm:text-sm mt-1">{t.followupPage.subtitle}</p>
      </div>

      {/* Honest Status Categories Explanation */}
      <div className="bg-stone-100 border border-stone-200 rounded-xl p-4 text-xs space-y-2 text-stone-700">
        <span className="font-bold text-stone-900 block">{t.followupPage.statusDistinction}</span>
        <ul className="space-y-1.5 list-disc pl-5">
          <li>{t.followupPage.statusCitizenReported}</li>
          <li>{t.followupPage.statusSimulated}</li>
          <li>{t.followupPage.statusOfficial}</li>
        </ul>
      </div>

      {/* Reminders List */}
      <div>
        <h2 className="text-sm font-bold text-stone-900 mb-3">{t.followupPage.remindersTitle}</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="p-5 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-start justify-between">
                <span className="text-[11px] font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  PM-KISAN
                </span>
                <StatusPill status="ACTIVE" label="सक्रिय अनुस्मारक" />
              </div>
              <h3 className="font-bold text-sm text-stone-900">{t.followupPage.pmKisanEkyc}</h3>
              <p className="text-xs text-stone-600 leading-relaxed">
                आगामी 4-मासिक किस्त प्राप्त करने हेतु बायोमेट्रिक ई-केवाईसी या फेस ऑथेंटिकेशन पूरा करें।
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-stone-100 flex items-center justify-between text-xs text-stone-500">
              <span className="flex items-center space-x-1 text-amber-700 font-semibold">
                <ClockIcon size={13} />
                <span>{t.followupPage.dueIn}</span>
              </span>
              <span className="text-[11px] text-stone-400">स्थिति: नागरिक द्वारा दर्ज</span>
            </div>
          </Card>

          <Card className="p-5 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-start justify-between">
                <span className="text-[11px] font-semibold text-blue-800 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                  AYUSHMAN BHARAT
                </span>
                <StatusPill status="DRAFT" label="वार्षिक नवीनीकरण" />
              </div>
              <h3 className="font-bold text-sm text-stone-900">आयुष्मान गोल्डन कार्ड पात्रता नवीनीकरण</h3>
              <p className="text-xs text-stone-600 leading-relaxed">
                पारिवारिक समग्र आईडी अथवा राशन कार्ड विवरण अद्यतन होने पर कार्ड पुनः सत्यापित करें।
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-stone-100 flex items-center justify-between text-xs text-stone-500">
              <span className="flex items-center space-x-1 text-stone-600">
                <ClockIcon size={13} />
                <span>नियत समय: आगामी 90 दिन</span>
              </span>
              <span className="text-[11px] text-stone-400">स्थिति: परीक्षण सिमुलेशन</span>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
