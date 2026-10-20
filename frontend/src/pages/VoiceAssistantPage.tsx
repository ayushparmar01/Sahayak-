import React, { useState, useEffect, useRef } from 'react';
import { useSession } from '../context/SessionContext';
import { translations } from '../i18n/translations';
import {
  fetchVoiceProviders,
  sendVoiceTurn,
} from '../services/api';
import type {
  VoiceTurnResponse,
  VoiceProvidersInfo,
  EligibilityAssessment,
} from '../types/index.ts';
import {
  MicIcon,
  ShieldCheckIcon,
  CheckCircleIcon,
  AlertTriangleIcon,
  Volume2Icon,
  SquareIcon,
  RefreshCwIcon,
  SendIcon,
} from '../components/Icons';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  audioBase64?: string | null;
  timestamp: string;
  turnResponse?: VoiceTurnResponse;
}

export const VoiceAssistantPage: React.FC = () => {
  const { session, language, giveConsent } = useSession();
  const t = translations[language];


  // Conversation & Audio State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [turnCount, setTurnCount] = useState(0);
  const [maxTurns, setMaxTurns] = useState(15);
  const [latestResponse, setLatestResponse] = useState<VoiceTurnResponse | null>(null);
  const [providersInfo, setProvidersInfo] = useState<VoiceProvidersInfo | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Audio References
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  // Load provider capability info on mount
  useEffect(() => {
    fetchVoiceProviders()
      .then((info) => {
        setProvidersInfo(info);
        if (info.audio_limits?.max_conversation_turns) {
          setMaxTurns(info.audio_limits.max_conversation_turns);
        }
      })
      .catch((err) => console.warn('Could not load voice provider info:', err));

    // Initial greeting if no messages
    if (messages.length === 0) {
      const greetingText =
        language === 'hi'
          ? 'नमस्ते! मैं आपका सहायक हूँ। आप बोलकर या लिखकर अपनी जानकारी बता सकते हैं, जैसे: "मैं किसान हूँ और मेरे पास 2 एकड़ जमीन है"। मैं आपके लिए उपयुक्त सरकारी योजनाएं खोजूंगा।'
          : 'Namaste! I am your SAHAYAK assistant. You can speak or type your details, such as: "I am a farmer with 2 acres of land". I will find the right welfare schemes for you.';
      setMessages([
        {
          id: 'msg-initial',
          sender: 'assistant',
          text: greetingText,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    }
  }, [language]);

  // Scroll to bottom on new message
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, latestResponse]);

  // Play audio response (Base64 WAV or Web Speech API fallback)
  const handlePlayAudio = (text: string, audioBase64?: string | null) => {
    if (isPlayingAudio) {
      if (audioElementRef.current) {
        audioElementRef.current.pause();
        audioElementRef.current.currentTime = 0;
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      setIsPlayingAudio(false);
      return;
    }

    if (audioBase64) {
      try {
        const audioUrl = `data:audio/wav;base64,${audioBase64}`;
        if (!audioElementRef.current) {
          audioElementRef.current = new Audio(audioUrl);
        } else {
          audioElementRef.current.src = audioUrl;
        }
        audioElementRef.current.onended = () => setIsPlayingAudio(false);
        audioElementRef.current.onerror = () => {
          setIsPlayingAudio(false);
          fallbackBrowserTTS(text);
        };
        setIsPlayingAudio(true);
        audioElementRef.current.play().catch(() => fallbackBrowserTTS(text));
        return;
      } catch (e) {
        console.warn('Backend audio play error, falling back to browser TTS:', e);
      }
    }

    fallbackBrowserTTS(text);
  };

  const fallbackBrowserTTS = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
      utterance.rate = 0.95;
      utterance.onend = () => setIsPlayingAudio(false);
      utterance.onerror = () => setIsPlayingAudio(false);
      setIsPlayingAudio(true);
      window.speechSynthesis.speak(utterance);
    }
  };

  // Start voice recording with browser MediaRecorder
  const handleStartRecording = async () => {
    setErrorMessage(null);
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setErrorMessage(
        language === 'hi'
          ? 'आपके ब्राउज़र में माइक्रोफ़ोन रिकॉर्डिंग समर्थित नहीं है। कृपया नीचे लिखकर बताएं।'
          : 'Microphone recording not supported in this browser. Please type below.'
      );
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mimeType = MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : MediaRecorder.isTypeSupported('audio/mp4')
        ? 'audio/mp4'
        : 'audio/wav';

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        if (audioBlob.size > 0) {
          await processRecordedAudio(audioBlob, mimeType);
        }
      };

      mediaRecorder.start(250);
      setIsRecording(true);
    } catch (err: any) {
      console.error('Microphone access denied:', err);
      setErrorMessage(
        language === 'hi'
          ? 'माइक्रोफ़ोन की अनुमति अस्वीकृत या अनुपलब्ध है। कृपया ब्राउज़र सेटिंग्स में अनुमति दें या नीचे लिखें।'
          : 'Microphone permission denied or unavailable. Please enable in browser settings or type below.'
      );
      setIsRecording(false);
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // Convert audio blob to base64 and execute voice turn
  const processRecordedAudio = async (blob: Blob, mimeType: string) => {
    setIsProcessing(true);
    setErrorMessage(null);

    const reader = new FileReader();
    reader.readAsDataURL(blob);
    reader.onloadend = async () => {
      try {
        const base64Data = (reader.result as string).split(',')[1];
        await executeVoiceTurn({
          audio_base64: base64Data,
          audio_mime_type: mimeType,
          preferred_language: language,
        });
      } catch (err: any) {
        setErrorMessage(err.message || 'वॉइस प्रोसेसिंग में त्रुटि');
      } finally {
        setIsProcessing(false);
      }
    };
  };

  // Execute conversational turn
  const executeVoiceTurn = async (payload: {
    text?: string | null;
    audio_base64?: string | null;
    audio_mime_type?: string;
    confirmed_by_user?: boolean | null;
    preferred_language?: string;
  }) => {
    if (!session.sessionId) {
      setErrorMessage(
        language === 'hi'
          ? 'सत्र सक्रिय नहीं है। कृपया पहले सहमति देकर सत्र प्रारंभ करें।'
          : 'Session not active. Please grant consent to start.'
      );
      return;
    }

    setIsProcessing(true);
    setErrorMessage(null);

    try {
      const response = await sendVoiceTurn(
        {
          text: payload.text,
          audio_base64: payload.audio_base64,
          audio_mime_type: payload.audio_mime_type,
          confirmed_by_user: payload.confirmed_by_user,
          preferred_language: language,
          request_tts: true,
        },
        session.sessionId
      );

      setLatestResponse(response);
      setTurnCount(response.turn_count);

      // Record citizen message in chat
      const citizenText = response.transcript || payload.text;
      if (citizenText) {
        setMessages((prev) => [
          ...prev,
          {
            id: `usr-${Date.now()}`,
            sender: 'user',
            text: citizenText,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }

      // Record assistant reply in chat
      const replyText =
        language === 'hi' ? response.response_text_hi : response.response_text_en;
      setMessages((prev) => [
        ...prev,
        {
          id: `asst-${Date.now()}`,
          sender: 'assistant',
          text: replyText,
          audioBase64: response.audio_base64,
          turnResponse: response,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);

      // Auto-play speech if available
      if (response.audio_base64) {
        handlePlayAudio(replyText, response.audio_base64);
      }
    } catch (err: any) {
      console.error('Turn error:', err);
      setErrorMessage(err.message || 'त्रुटि हुई। कृपया पुनः प्रयास करें।');
    } finally {
      setIsProcessing(false);
      setInputText('');
    }
  };

  // Text input submit handler
  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isProcessing) return;
    executeVoiceTurn({ text: inputText.trim() });
  };

  // Quick chips click
  const handleQuickPrompt = (promptText: string) => {
    setInputText(promptText);
    executeVoiceTurn({ text: promptText });
  };

  // Explicit confirmation button handlers
  const handleConfirmProfile = () => {
    executeVoiceTurn({
      text: language === 'hi' ? 'हाँ, यह जानकारी बिल्कुल सही है।' : 'Yes, this information is correct.',
      confirmed_by_user: true,
    });
  };

  const handleCancelProfile = () => {
    executeVoiceTurn({
      text: language === 'hi' ? 'नहीं, यह जानकारी गलत है। इसे रद्द करें।' : 'No, this is incorrect. Discard it.',
      confirmed_by_user: false,
    });
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Page Header */}
      <div className="bg-gradient-to-r from-emerald-900 via-stone-900 to-stone-900 text-white rounded-2xl p-6 sm:p-8 shadow-md border border-emerald-700/40 relative">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 bg-emerald-800/80 text-emerald-200 px-3 py-1 rounded-full text-xs font-semibold mb-2">
              <MicIcon size={14} className="text-emerald-300" />
              <span>{t.voiceAssistant.title}</span>
            </div>
            <h1 className="text-xl sm:text-3xl font-bold tracking-tight">
              {t.appName}
            </h1>
            <p className="text-stone-300 text-xs sm:text-sm mt-1 max-w-2xl leading-relaxed">
              {t.voiceAssistant.subtitle}
            </p>
          </div>

          {/* Loop Guard Turn Counter */}
          <div className="bg-stone-800/90 border border-stone-700 px-4 py-2.5 rounded-xl text-center">
            <span className="text-[11px] text-stone-400 block">{t.voiceAssistant.turnsLeft}</span>
            <span className="text-base sm:text-lg font-bold text-emerald-400">
              {Math.max(0, maxTurns - turnCount)} / {maxTurns}
            </span>
          </div>
        </div>

        {/* Provider Transparency Strip */}
        <div className="mt-4 pt-3 border-t border-stone-800 flex flex-wrap items-center gap-3 text-[11px] text-stone-400">
          <span className="flex items-center space-x-1">
            <ShieldCheckIcon size={13} className="text-emerald-400" />
            <strong className="text-stone-300">{t.voiceAssistant.rulesEngine}</strong>
          </span>
          <span className="text-stone-600">•</span>
          <span>
            {t.voiceAssistant.sttEngine}{' '}
            <span className="text-emerald-300 font-mono">
              {providersInfo?.stt_provider || 'Mock / Sarvam / Bhashini'}
            </span>
          </span>
          <span className="text-stone-600">•</span>
          <span>
            {t.voiceAssistant.ttsEngine}{' '}
            <span className="text-emerald-300 font-mono">
              {providersInfo?.tts_provider || 'Browser WebSpeech / Pyttsx3'}
            </span>
          </span>
          {providersInfo?.is_mock && (
            <>
              <span className="text-stone-600">•</span>
              <span className="bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded text-[10px] font-semibold tracking-wide">
                {language === 'hi' ? 'सिम्युलेटेड (Mock Mode)' : 'Simulated (Mock Mode)'}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Voice Consent Gate Modal/Banner */}
      {(!session.isActive || !session.consentGrantedAt) && (
        <div className="bg-amber-900/30 border-2 border-amber-600/70 rounded-2xl p-6 sm:p-8 space-y-4">
          <div className="flex items-start space-x-3">
            <AlertTriangleIcon size={28} className="text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-2">
              <h2 className="text-lg font-bold text-amber-200">
                {t.voiceAssistant.consentRequiredTitle}
              </h2>
              <p className="text-sm text-stone-300 leading-relaxed">
                {t.voiceAssistant.consentRequiredBody}
              </p>
              <div className="pt-2 flex flex-wrap gap-3">
                <button
                  onClick={() => giveConsent()}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm px-5 py-2.5 rounded-xl shadow-md transition flex items-center space-x-2"
                >
                  <CheckCircleIcon size={16} />
                  <span>{t.voiceAssistant.grantVoiceConsent}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Conversation Stream */}
      <div className="bg-white rounded-2xl shadow-sm border border-stone-200 overflow-hidden flex flex-col h-[520px]">
        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-stone-50/50">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${
                msg.sender === 'user' ? 'items-end' : 'items-start'
              }`}
            >
              <div
                className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 shadow-sm text-sm sm:text-base leading-relaxed ${
                  msg.sender === 'user'
                    ? 'bg-emerald-700 text-white rounded-tr-none'
                    : 'bg-white text-stone-900 border border-stone-200 rounded-tl-none'
                }`}
              >
                <div className="whitespace-pre-line">{msg.text}</div>

                {/* Assistant controls: Audio speaker button */}
                {msg.sender === 'assistant' && (
                  <div className="mt-3 pt-2 border-t border-stone-100 flex items-center justify-between text-xs text-stone-500">
                    <button
                      onClick={() => handlePlayAudio(msg.text, msg.audioBase64)}
                      className="inline-flex items-center space-x-1.5 text-emerald-700 hover:text-emerald-800 font-semibold bg-emerald-50 hover:bg-emerald-100 px-3 py-1 rounded-lg transition"
                    >
                      {isPlayingAudio ? (
                        <>
                          <SquareIcon size={14} className="text-rose-600" />
                          <span>{t.voiceAssistant.stopSpeaking}</span>
                        </>
                      ) : (
                        <>
                          <Volume2Icon size={14} />
                          <span>{t.voiceAssistant.speakReply}</span>
                        </>
                      )}
                    </button>
                    <span className="text-[11px] text-stone-400">{msg.timestamp}</span>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Assistant Processing Spinner */}
          {isProcessing && (
            <div className="flex items-center space-x-3 text-stone-500 text-sm bg-white border border-stone-200 rounded-2xl p-3 w-fit">
              <RefreshCwIcon size={16} className="animate-spin text-emerald-600" />
              <span>{t.voiceAssistant.micButtonProcessing}</span>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Profile Confirmation Gating Card */}
        {latestResponse?.status === 'needs_confirmation' &&
          latestResponse.proposed_profile_updates &&
          Object.keys(latestResponse.proposed_profile_updates).length > 0 && (
            <div className="bg-amber-50 border-t-2 border-amber-500 p-4 sm:p-5 space-y-3">
              <div className="flex items-center space-x-2 text-amber-900 font-bold text-sm">
                <AlertTriangleIcon size={18} className="text-amber-600" />
                <span>{t.voiceAssistant.confirmProfileTitle}</span>
              </div>
              <p className="text-xs sm:text-sm text-stone-700">
                {t.voiceAssistant.confirmProfileDesc}
              </p>

              {/* Proposed updates chip list */}
              <div className="bg-white rounded-xl p-3 border border-amber-200 flex flex-wrap gap-2 text-xs">
                {Object.entries(latestResponse.proposed_profile_updates).map(([k, v]) => (
                  <div
                    key={k}
                    className="bg-stone-100 text-stone-800 px-2.5 py-1 rounded-md font-medium border border-stone-200"
                  >
                    <span className="text-stone-500">{k}:</span>{' '}
                    <strong className="text-emerald-700">
                      {v === true ? 'हाँ / Yes' : v === false ? 'नहीं / No' : String(v)}
                    </strong>
                  </div>
                ))}
              </div>

              {/* Two-Button Confirmation Controls */}
              <div className="flex flex-wrap gap-3 pt-1">
                <button
                  onClick={handleConfirmProfile}
                  disabled={isProcessing}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs sm:text-sm px-4 py-2 rounded-xl transition flex items-center space-x-1.5 shadow"
                >
                  <CheckCircleIcon size={16} />
                  <span>{t.voiceAssistant.confirmBtn}</span>
                </button>
                <button
                  onClick={handleCancelProfile}
                  disabled={isProcessing}
                  className="bg-stone-200 hover:bg-stone-300 text-stone-800 font-semibold text-xs sm:text-sm px-4 py-2 rounded-xl transition"
                >
                  <span>{t.voiceAssistant.cancelBtn}</span>
                </button>
              </div>
            </div>
          )}

        {/* Follow-up Question Quick Chips */}
        {latestResponse?.status === 'needs_follow_up' && latestResponse.follow_up_field && (
          <div className="bg-emerald-50 border-t border-emerald-200 p-3 sm:p-4 space-y-2">
            <div className="text-xs font-semibold text-emerald-900">
              {t.voiceAssistant.followUpTitle}
            </div>
            <div className="text-sm font-medium text-stone-800">
              {language === 'hi'
                ? latestResponse.follow_up_question_hi
                : latestResponse.follow_up_question_en}
            </div>
            <div className="flex flex-wrap gap-2 pt-1">
              <button
                onClick={() => handleQuickPrompt(language === 'hi' ? 'हाँ' : 'Yes')}
                className="bg-white hover:bg-emerald-100 text-emerald-800 text-xs font-semibold px-3 py-1.5 rounded-lg border border-emerald-300 transition"
              >
                {language === 'hi' ? 'हाँ' : 'Yes'}
              </button>
              <button
                onClick={() => handleQuickPrompt(language === 'hi' ? 'नहीं' : 'No')}
                className="bg-white hover:bg-emerald-100 text-emerald-800 text-xs font-semibold px-3 py-1.5 rounded-lg border border-emerald-300 transition"
              >
                {language === 'hi' ? 'नहीं' : 'No'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Evaluated Scheme Recommendations (Deterministic Engine Results) */}
      {latestResponse?.evaluated_schemes && latestResponse.evaluated_schemes.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-stone-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base sm:text-lg font-bold text-stone-900 flex items-center space-x-2">
              <CheckCircleIcon size={20} className="text-emerald-600" />
              <span>{t.voiceAssistant.recommendedSchemesTitle}</span>
            </h2>
            <span className="text-xs text-stone-500 font-mono">
              {latestResponse.evaluated_schemes.length} योजनाएं जांची गईं
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {latestResponse.evaluated_schemes.map((scheme: EligibilityAssessment) => {
              const isEligible = scheme.status === 'ELIGIBLE';
              const isPotential = scheme.status === 'POTENTIALLY_ELIGIBLE';
              const isNeedsMore = scheme.status === 'NEEDS_MORE_INFO';

              const badgeColor = isEligible
                ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                : isPotential
                ? 'bg-amber-100 text-amber-800 border-amber-300'
                : isNeedsMore
                ? 'bg-sky-100 text-sky-800 border-sky-300'
                : 'bg-stone-100 text-stone-700 border-stone-300';

              return (
                <div
                  key={scheme.scheme_id}
                  className="rounded-xl border border-stone-200 p-4 space-y-3 hover:shadow-md transition bg-stone-50/30"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-bold text-stone-900 text-sm sm:text-base">
                        {language === 'hi' ? scheme.scheme_name_hi : scheme.scheme_name_en}
                      </h3>
                      <span className="text-[11px] text-stone-500 font-mono">
                        Rule v{scheme.rule_version}
                      </span>
                    </div>
                    <span
                      className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${badgeColor}`}
                    >
                      {language === 'hi' ? scheme.status_label_hi : scheme.status_label_en}
                    </span>
                  </div>

                  {/* Benefit details */}
                  {scheme.benefit_summary && (
                    <div className="bg-emerald-50/70 border border-emerald-200/60 rounded-lg p-2.5 text-xs text-emerald-950">
                      <span className="font-bold text-emerald-900 block">
                        {language === 'hi'
                          ? scheme.benefit_summary.benefit_amount_display_hi ||
                            `₹${scheme.benefit_summary.amount_inr.toLocaleString('en-IN')}`
                          : scheme.benefit_summary.benefit_amount_display_en ||
                            `₹${scheme.benefit_summary.amount_inr.toLocaleString('en-IN')}`}
                      </span>
                      <p className="text-[11px] text-emerald-800 mt-0.5">
                        {language === 'hi'
                          ? scheme.benefit_summary.description_hi
                          : scheme.benefit_summary.description_en}
                      </p>
                    </div>
                  )}

                  {/* Deterministic Explanation */}
                  <p className="text-xs text-stone-600 line-clamp-3">
                    {language === 'hi'
                      ? scheme.summary_explanation_hi
                      : scheme.summary_explanation_en}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Input Interaction Dock: Big Microphone + Text Fallback */}
      <div className="bg-stone-900 rounded-2xl p-4 sm:p-6 text-white shadow-xl space-y-4 border border-stone-800">
        {/* Error Notification */}
        {errorMessage && (
          <div className="bg-rose-900/70 border border-rose-600 text-rose-200 text-xs sm:text-sm p-3 rounded-xl flex items-center space-x-2">
            <AlertTriangleIcon size={16} className="shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          {/* Large Central Microphone Action */}
          <div className="flex items-center space-x-4">
            <button
              onClick={isRecording ? handleStopRecording : handleStartRecording}
              disabled={isProcessing || turnCount >= maxTurns}
              className={`w-16 h-16 sm:w-20 sm:h-20 rounded-full flex items-center justify-center transition shadow-lg relative ${
                isRecording
                  ? 'bg-rose-600 hover:bg-rose-700 animate-pulse ring-4 ring-rose-400/50'
                  : 'bg-emerald-600 hover:bg-emerald-500 ring-4 ring-emerald-500/30'
              } ${isProcessing || turnCount >= maxTurns ? 'opacity-50 cursor-not-allowed' : ''}`}
              title={isRecording ? 'रिकॉर्डिंग रोकें' : 'बोलने के लिए दबाएं'}
            >
              {isRecording ? (
                <SquareIcon size={28} className="text-white" />
              ) : (
                <MicIcon size={32} className="text-white" />
              )}
            </button>

            <div>
              <div className="font-bold text-sm sm:text-base text-white">
                {isRecording
                  ? t.voiceAssistant.micButtonListening
                  : isProcessing
                  ? t.voiceAssistant.micButtonProcessing
                  : t.voiceAssistant.micButtonStart}
              </div>
              <div className="text-xs text-stone-400">
                {language === 'hi'
                  ? 'माइक दबाकर स्वाभाविक रूप से बोलें'
                  : 'Tap mic and speak naturally'}
              </div>
            </div>
          </div>

          {/* Text Input Fallback Bar */}
          <form
            onSubmit={handleTextSubmit}
            className="w-full sm:w-auto flex-1 max-w-lg flex items-center space-x-2"
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isProcessing || isRecording || turnCount >= maxTurns}
              placeholder={t.voiceAssistant.textFallbackPlaceholder}
              className="flex-1 bg-stone-800 border border-stone-700 text-stone-100 placeholder-stone-400 text-xs sm:text-sm px-4 py-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isProcessing || isRecording || turnCount >= maxTurns}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white px-4 py-3 rounded-xl transition flex items-center justify-center font-semibold text-xs sm:text-sm"
            >
              <SendIcon size={16} />
            </button>
          </form>
        </div>

        {/* Quick Suggestion Prompts */}
        <div className="pt-2 border-t border-stone-800 space-y-1.5">
          <div className="text-[11px] text-stone-400 font-semibold">
            {t.voiceAssistant.quickSuggestionsTitle}
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <button
              onClick={() => handleQuickPrompt(t.voiceAssistant.suggestion1)}
              className="bg-stone-800 hover:bg-stone-700 text-stone-300 px-3 py-1.5 rounded-lg border border-stone-700 transition"
            >
              "{t.voiceAssistant.suggestion1}"
            </button>
            <button
              onClick={() => handleQuickPrompt(t.voiceAssistant.suggestion2)}
              className="bg-stone-800 hover:bg-stone-700 text-stone-300 px-3 py-1.5 rounded-lg border border-stone-700 transition"
            >
              "{t.voiceAssistant.suggestion2}"
            </button>
            <button
              onClick={() => handleQuickPrompt(t.voiceAssistant.suggestion3)}
              className="bg-stone-800 hover:bg-stone-700 text-stone-300 px-3 py-1.5 rounded-lg border border-stone-700 transition"
            >
              "{t.voiceAssistant.suggestion3}"
            </button>
            <button
              onClick={() => handleQuickPrompt(t.voiceAssistant.suggestion4)}
              className="bg-stone-800 hover:bg-stone-700 text-stone-300 px-3 py-1.5 rounded-lg border border-stone-700 transition"
            >
              "{t.voiceAssistant.suggestion4}"
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
export default VoiceAssistantPage;
