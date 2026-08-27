"use client";

import React from "react";

export interface Language {
  code: string;       // Used as the language name sent to backend & TTS
  name: string;       // English display name
  nativeName: string; // Native script display name
  bcp47: string;      // BCP-47 code for Web Speech API voice matching
}

export const LANGUAGES: Language[] = [
  { code: "English",    name: "English",    nativeName: "English",    bcp47: "en-US" },
  { code: "Hindi",      name: "Hindi",      nativeName: "हिन्दी",      bcp47: "hi-IN" },
  { code: "Tamil",      name: "Tamil",      nativeName: "தமிழ்",      bcp47: "ta-IN" },
  { code: "Telugu",     name: "Telugu",     nativeName: "తెలుగు",     bcp47: "te-IN" },
  { code: "Bengali",    name: "Bengali",    nativeName: "বাংলা",      bcp47: "bn-IN" },
  { code: "Marathi",    name: "Marathi",    nativeName: "मराठी",      bcp47: "mr-IN" },
  { code: "Gujarati",   name: "Gujarati",   nativeName: "ગુજરાતી",   bcp47: "gu-IN" },
  { code: "Kannada",    name: "Kannada",    nativeName: "ಕನ್ನಡ",     bcp47: "kn-IN" },
  { code: "Punjabi",    name: "Punjabi",    nativeName: "ਪੰਜਾਬੀ",    bcp47: "pa-IN" },
  { code: "French",     name: "French",     nativeName: "Français",   bcp47: "fr-FR" },
  { code: "Spanish",    name: "Spanish",    nativeName: "Español",    bcp47: "es-ES" },
  { code: "German",     name: "German",     nativeName: "Deutsch",    bcp47: "de-DE" },
  { code: "Arabic",     name: "Arabic",     nativeName: "العربية",    bcp47: "ar-SA" },
  { code: "Japanese",   name: "Japanese",   nativeName: "日本語",      bcp47: "ja-JP" },
  { code: "Korean",     name: "Korean",     nativeName: "한국어",      bcp47: "ko-KR" },
  { code: "Portuguese", name: "Portuguese", nativeName: "Português",  bcp47: "pt-BR" },
  { code: "Russian",    name: "Russian",    nativeName: "Русский",    bcp47: "ru-RU" },
  { code: "Italian",    name: "Italian",    nativeName: "Italiano",   bcp47: "it-IT" },
];

/** Quick lookup: language code → BCP-47 */
export function getBcp47(langCode: string): string {
  return LANGUAGES.find((l) => l.code === langCode)?.bcp47 ?? "en-US";
}

interface LanguageSelectorProps {
  selectedLanguage: string;
  onChange: (language: string) => void;
}

export default function LanguageSelector({
  selectedLanguage,
  onChange,
}: LanguageSelectorProps) {
  return (
    <div className="flex flex-col space-y-1.5 w-full">
      <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
        Guide Language
      </label>
      <select
        value={selectedLanguage}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-white border border-gray-300 text-gray-800 py-2.5 px-3 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500 transition-all duration-200 font-medium"
      >
        {LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.nativeName} — {lang.name}
          </option>
        ))}
      </select>
    </div>
  );
}
