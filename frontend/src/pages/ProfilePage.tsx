import React, { useState } from 'react';
import { useSession } from '../context/SessionContext';
import { translations } from '../i18n/translations';
import { Card } from '../components/Card';
import { ShieldCheckIcon, CheckCircleIcon } from '../components/Icons';

export const ProfilePage: React.FC = () => {
  const { language, profile, saveProfile } = useSession();
  const t = translations[language];
  const p = t.profilePage;

  const [formData, setFormData] = useState({
    age: profile.age ?? '',
    state: profile.state ?? 'Uttar Pradesh',
    district: profile.district ?? 'Mathura',
    landAcres: profile.landAcres ?? '',
    landType: profile.landType ?? 'irrigated',
    annualIncome: profile.annualIncome ?? '',
    rationCardType: profile.rationCardType ?? 'BPL',
    occupation: profile.occupation ?? 'farmer',
    socialCategory: profile.socialCategory ?? 'OBC',
    gender: profile.gender ?? 'female',
    isIncomeTaxPayer: profile.isIncomeTaxPayer ?? false,
    hasPuccaHouse: profile.hasPuccaHouse ?? false,
    residenceType: profile.residenceType ?? 'RURAL',
    ownsAgriculturalLand: profile.ownsAgriculturalLand ?? true,
    hasGirlChildUnder10: profile.hasGirlChildUnder10 ?? false,
    hasExistingLpg: profile.hasExistingLpg ?? false,
  });

  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccess(false);

    try {
      await saveProfile({
        age: formData.age ? Number(formData.age) : null,
        state: formData.state,
        district: formData.district,
        landAcres: formData.landAcres ? Number(formData.landAcres) : null,
        landType: formData.landType,
        annualIncome: formData.annualIncome ? Number(formData.annualIncome) : null,
        rationCardType: formData.rationCardType,
        occupation: formData.occupation,
        socialCategory: formData.socialCategory,
        gender: formData.gender,
        isIncomeTaxPayer: formData.isIncomeTaxPayer,
        hasPuccaHouse: formData.hasPuccaHouse,
        residenceType: formData.residenceType,
        ownsAgriculturalLand: formData.ownsAgriculturalLand,
        hasGirlChildUnder10: formData.hasGirlChildUnder10,
        hasExistingLpg: formData.hasExistingLpg,
        isConfirmed: true,
      });
      setSuccess(true);
    } finally {
      setSaving(false);
    }
  };

  // Dynamic readiness score calculation
  const totalFields = 12;
  let filledFields = 0;
  if (formData.age) filledFields++;
  if (formData.state) filledFields++;
  if (formData.district) filledFields++;
  if (formData.occupation) filledFields++;
  if (formData.rationCardType) filledFields++;
  if (formData.socialCategory) filledFields++;
  if (formData.gender) filledFields++;
  if (formData.ownsAgriculturalLand !== null && formData.ownsAgriculturalLand !== undefined) filledFields++;
  if (formData.isIncomeTaxPayer !== null && formData.isIncomeTaxPayer !== undefined) filledFields++;
  if (formData.hasPuccaHouse !== null && formData.hasPuccaHouse !== undefined) filledFields++;
  if (formData.residenceType) filledFields++;
  if (formData.annualIncome) filledFields++;

  const readinessPercent = Math.min(100, Math.round((filledFields / totalFields) * 100));

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-stone-900">{p.title}</h1>
        <p className="text-stone-600 text-xs sm:text-sm mt-1">{p.subtitle}</p>
      </div>

      {/* Privacy Notice Card */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900 flex items-start space-x-3">
        <ShieldCheckIcon size={20} className="text-amber-700 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold block">{p.privacyReminder}</span>
          <p className="mt-0.5">{p.phase2VoiceNotice}</p>
        </div>
      </div>

      {/* Dynamic Profile Readiness Meter */}
      <div className="bg-white rounded-xl border border-stone-200 p-4 shadow-sm space-y-2">
        <div className="flex justify-between items-center text-xs">
          <span className="font-bold text-stone-800">
            योजना पात्रता तत्परता स्कोर (Profile Completeness)
          </span>
          <span className="font-mono font-bold text-emerald-700">{readinessPercent}%</span>
        </div>
        <div className="w-full bg-stone-100 rounded-full h-2.5 overflow-hidden border border-stone-200">
          <div
            className="bg-emerald-600 h-2.5 rounded-full transition-all duration-500"
            style={{ width: `${readinessPercent}%` }}
          ></div>
        </div>
        <p className="text-[11px] text-stone-500">
          जितने अधिक फ़ील्ड सत्यापित होंगे, 8 योजनाओं में आपकी पात्रता का आकलन उतना ही सटीक व पूर्ण होगा।
        </p>
      </div>

      {success && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-xs text-emerald-900 flex items-center space-x-2">
          <CheckCircleIcon size={18} className="text-emerald-700 shrink-0" />
          <span className="font-semibold">{p.savedSuccess}</span>
        </div>
      )}

      {/* Form */}
      <Card className="p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Age */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                {p.age} *
              </label>
              <input
                type="number"
                min="0"
                max="120"
                value={formData.age}
                onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                placeholder="उदा. 42"
                className="w-full px-3 py-2 text-xs sm:text-sm border border-stone-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
              />
            </div>

            {/* Gender */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                {p.gender} *
              </label>
              <select
                value={formData.gender}
                onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                className="w-full px-3 py-2 text-xs sm:text-sm border border-stone-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none bg-white"
              >
                <option value="female">{p.genderFemale}</option>
                <option value="male">{p.genderMale}</option>
                <option value="other">{p.genderOther}</option>
              </select>
              <span className="text-[10px] text-stone-500 mt-0.5 block">{p.genderHint}</span>
            </div>

            {/* State */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                {p.state} *
              </label>
              <input
                type="text"
                value={formData.state}
                onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                className="w-full px-3 py-2 text-xs sm:text-sm border border-stone-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
              />
            </div>

            {/* District */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                {p.district} *
              </label>
              <input
                type="text"
                value={formData.district}
                onChange={(e) => setFormData({ ...formData, district: e.target.value })}
                className="w-full px-3 py-2 text-xs sm:text-sm border border-stone-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
              />
            </div>

            {/* Occupation */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                {p.occupation} *
              </label>
              <select
                value={formData.occupation}
                onChange={(e) => setFormData({ ...formData, occupation: e.target.value })}
                className="w-full px-3 py-2 text-xs sm:text-sm border border-stone-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none bg-white"
              >
                <option value="farmer">किसान (Farmer)</option>
                <option value="artisan">कारीगर / शिल्पकार (Artisan)</option>
                <option value="laborer">श्रमिक / मजदूर (Laborer)</option>
                <option value="student">विद्यार्थी (Student)</option>
                <option value="homemaker">गृहणी (Homemaker)</option>
                <option value="self_employed">स्वरोजगार (Self-employed)</option>
                <option value="other">अन्य (Other)</option>
              </select>
            </div>

            {/* Ration Card */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                {p.rationCard} *
              </label>
              <select
                value={formData.rationCardType}
                onChange={(e) => setFormData({ ...formData, rationCardType: e.target.value })}
                className="w-full px-3 py-2 text-xs sm:text-sm border border-stone-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none bg-white"
              >
                <option value="BPL">बीपीएल (BPL - गरीबी रेखा से नीचे)</option>
                <option value="Antyodaya">अंत्योदय (AAY - अत्यंत निर्धन)</option>
                <option value="APL">एपीएल (APL - सामान्य)</option>
                <option value="None">कोई राशन कार्ड नहीं (None)</option>
              </select>
            </div>

            {/* Social Category */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                {p.socialCategory} *
              </label>
              <select
                value={formData.socialCategory}
                onChange={(e) => setFormData({ ...formData, socialCategory: e.target.value })}
                className="w-full px-3 py-2 text-xs sm:text-sm border border-stone-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none bg-white"
              >
                <option value="OBC">अन्य पिछड़ा वर्ग (OBC)</option>
                <option value="SC">अनुसूचित जाति (SC)</option>
                <option value="ST">अनुसूचित जनजाति (ST)</option>
                <option value="General">सामान्य वर्ग (General)</option>
              </select>
            </div>

            {/* Annual Income */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                {p.annualIncome}
              </label>
              <input
                type="number"
                min="0"
                value={formData.annualIncome}
                onChange={(e) => setFormData({ ...formData, annualIncome: e.target.value })}
                placeholder="उदा. 85000"
                className="w-full px-3 py-2 text-xs sm:text-sm border border-stone-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
              />
            </div>
          </div>

          {/* Agricultural Details Section */}
          <div className="pt-3 border-t border-stone-200 space-y-4">
            <h3 className="font-bold text-xs uppercase tracking-wider text-stone-800">
              कृषि व भूमि विवरण (Agricultural Information)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-stone-700 mb-1">
                  {p.ownsLand}
                </label>
                <select
                  value={formData.ownsAgriculturalLand ? 'yes' : 'no'}
                  onChange={(e) =>
                    setFormData({ ...formData, ownsAgriculturalLand: e.target.value === 'yes' })
                  }
                  className="w-full px-3 py-2 text-xs sm:text-sm border border-stone-300 rounded-lg focus:ring-2 focus:ring-emerald-600 bg-white"
                >
                  <option value="yes">{p.ownsLandYes}</option>
                  <option value="no">{p.ownsLandNo}</option>
                </select>
                <span className="text-[10px] text-stone-500 mt-0.5 block">{p.ownsLandHint}</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700 mb-1">
                  {p.landAcres}
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={formData.landAcres}
                  onChange={(e) => setFormData({ ...formData, landAcres: e.target.value })}
                  placeholder="उदा. 2.0"
                  className="w-full px-3 py-2 text-xs sm:text-sm border border-stone-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700 mb-1">
                  {p.landType}
                </label>
                <select
                  value={formData.landType}
                  onChange={(e) => setFormData({ ...formData, landType: e.target.value })}
                  className="w-full px-3 py-2 text-xs sm:text-sm border border-stone-300 rounded-lg focus:ring-2 focus:ring-emerald-600 bg-white"
                >
                  <option value="irrigated">सिंचित (Irrigated)</option>
                  <option value="rainfed">असिंचित / बारानी (Rainfed)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Household & Welfare Criteria Section */}
          <div className="pt-3 border-t border-stone-200 space-y-4">
            <h3 className="font-bold text-xs uppercase tracking-wider text-stone-800">
              योजना अपवर्जन व पारिवारिक पात्रता शर्तें (Eligibility Criteria & Safeguards)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Income Tax */}
              <div className="bg-stone-50 p-3 rounded-lg border border-stone-200 space-y-1">
                <label className="block text-xs font-semibold text-stone-800">
                  {p.incomeTax}
                </label>
                <select
                  value={formData.isIncomeTaxPayer ? 'yes' : 'no'}
                  onChange={(e) =>
                    setFormData({ ...formData, isIncomeTaxPayer: e.target.value === 'yes' })
                  }
                  className="w-full px-2.5 py-1.5 text-xs border border-stone-300 rounded focus:ring-2 focus:ring-emerald-600 bg-white"
                >
                  <option value="no">{p.incomeTaxNo}</option>
                  <option value="yes">{p.incomeTaxYes}</option>
                </select>
                <span className="text-[10px] text-stone-500 block">{p.incomeTaxHint}</span>
              </div>

              {/* Pucca House */}
              <div className="bg-stone-50 p-3 rounded-lg border border-stone-200 space-y-1">
                <label className="block text-xs font-semibold text-stone-800">
                  {p.puccaHouse}
                </label>
                <select
                  value={formData.hasPuccaHouse ? 'yes' : 'no'}
                  onChange={(e) =>
                    setFormData({ ...formData, hasPuccaHouse: e.target.value === 'yes' })
                  }
                  className="w-full px-2.5 py-1.5 text-xs border border-stone-300 rounded focus:ring-2 focus:ring-emerald-600 bg-white"
                >
                  <option value="no">{p.puccaHouseNo}</option>
                  <option value="yes">{p.puccaHouseYes}</option>
                </select>
                <span className="text-[10px] text-stone-500 block">{p.puccaHouseHint}</span>
              </div>

              {/* Residence Type (Rural / Urban) */}
              <div className="bg-stone-50 p-3 rounded-lg border border-stone-200 space-y-1">
                <label className="block text-xs font-semibold text-stone-800">
                  {p.residenceType}
                </label>
                <select
                  value={formData.residenceType}
                  onChange={(e) =>
                    setFormData({ ...formData, residenceType: e.target.value })
                  }
                  className="w-full px-2.5 py-1.5 text-xs border border-stone-300 rounded focus:ring-2 focus:ring-emerald-600 bg-white"
                >
                  <option value="RURAL">{p.residenceRural}</option>
                  <option value="URBAN">{p.residenceUrban}</option>
                </select>
                <span className="text-[10px] text-stone-500 block">{p.residenceHint}</span>
              </div>

              {/* Girl child <= 10 */}
              <div className="bg-stone-50 p-3 rounded-lg border border-stone-200 space-y-1">
                <label className="block text-xs font-semibold text-stone-800">
                  {p.girlChild}
                </label>
                <select
                  value={formData.hasGirlChildUnder10 ? 'yes' : 'no'}
                  onChange={(e) =>
                    setFormData({ ...formData, hasGirlChildUnder10: e.target.value === 'yes' })
                  }
                  className="w-full px-2.5 py-1.5 text-xs border border-stone-300 rounded focus:ring-2 focus:ring-emerald-600 bg-white"
                >
                  <option value="no">{p.girlChildNo}</option>
                  <option value="yes">{p.girlChildYes}</option>
                </select>
                <span className="text-[10px] text-stone-500 block">{p.girlChildHint}</span>
              </div>

              {/* Existing LPG */}
              <div className="bg-stone-50 p-3 rounded-lg border border-stone-200 space-y-1">
                <label className="block text-xs font-semibold text-stone-800">
                  {p.existingLpg}
                </label>
                <select
                  value={formData.hasExistingLpg ? 'yes' : 'no'}
                  onChange={(e) =>
                    setFormData({ ...formData, hasExistingLpg: e.target.value === 'yes' })
                  }
                  className="w-full px-2.5 py-1.5 text-xs border border-stone-300 rounded focus:ring-2 focus:ring-emerald-600 bg-white"
                >
                  <option value="no">{p.existingLpgNo}</option>
                  <option value="yes">{p.existingLpgYes}</option>
                </select>
                <span className="text-[10px] text-stone-500 block">{p.existingLpgHint}</span>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-stone-200 flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 bg-emerald-700 hover:bg-emerald-800 disabled:bg-stone-300 text-white rounded-lg text-xs sm:text-sm font-semibold transition shadow-sm"
            >
              {saving ? 'सुरक्षित हो रहा है...' : p.saveProfile}
            </button>
          </div>
        </form>
      </Card>
    </div>
  );
};
