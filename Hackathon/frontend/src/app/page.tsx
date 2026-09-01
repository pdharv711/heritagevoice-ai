"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Camera,
  Volume2,
  MessageSquare,
  RefreshCw,
  Landmark,
  Info,
} from "lucide-react";

import LanguageSelector, {
  getBcp47,
} from "@/components/LanguageSelector";

import CameraFeed from "@/components/CameraFeed";
import ChatWindow from "@/components/ChatWindow";
import Footer from "@/components/Footer";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://heritagevoice-ai.onrender.com";

type ActiveTab = "camera" | "audio" | "chat";

interface MonumentDetails {
  location?: string;
  built_by?: string;
  construction_year?: string;
  theme?: string;
  key_facts?: string[];
  [key: string]: any;
}

export default function Home() {
  // ---------------------------------------------------------
  // APP STATE
  // ---------------------------------------------------------

  const [language, setLanguage] = useState("English");

  const [monumentId, setMonumentId] = useState<string | null>(
    null
  );

  const [monumentName, setMonumentName] = useState<string | null>(
    null
  );

  const [narration, setNarration] = useState<string | null>(
    null
  );

  const [details, setDetails] =
    useState<MonumentDetails | null>(null);

  const [loading, setLoading] = useState(false);

  const [languageLoading, setLanguageLoading] =
    useState(false);

  const [activeTab, setActiveTab] =
    useState<ActiveTab>("camera");

  // ---------------------------------------------------------
  // SPEECH STATE
  // ---------------------------------------------------------

  const [isSpeaking, setIsSpeaking] = useState(false);

  const [voicesReady, setVoicesReady] =
    useState(false);

  const [activeVoiceName, setActiveVoiceName] =
    useState<string | null>(null);

  const synthRef =
    useRef<SpeechSynthesis | null>(null);

  const utteranceRef =
    useRef<SpeechSynthesisUtterance | null>(null);

  // ---------------------------------------------------------
  // INITIALIZE SPEECH SYNTHESIS
  // ---------------------------------------------------------

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    if (!("speechSynthesis" in window)) {
      console.warn(
        "Speech synthesis is not supported."
      );

      setVoicesReady(false);
      return;
    }

    const synth = window.speechSynthesis;

    synthRef.current = synth;

    const loadVoices = () => {
      const voices = synth.getVoices();

      console.log(
        "Browser voices:",
        voices.map(
          (voice) =>
            `${voice.name} (${voice.lang})`
        )
      );

      if (voices.length > 0) {
        setVoicesReady(true);
      }
    };

    // Initial attempt.
    loadVoices();

    // Chrome often loads voices asynchronously.
    synth.addEventListener(
      "voiceschanged",
      loadVoices
    );

    // Extra retry for browsers that don't fire
    // voiceschanged immediately.
    const timer1 = window.setTimeout(
      loadVoices,
      500
    );

    const timer2 = window.setTimeout(
      loadVoices,
      1500
    );

    const timer3 = window.setTimeout(
      loadVoices,
      3000
    );

    return () => {
      synth.removeEventListener(
        "voiceschanged",
        loadVoices
      );

      window.clearTimeout(timer1);
      window.clearTimeout(timer2);
      window.clearTimeout(timer3);

      synth.cancel();
    };
  }, []);

  // ---------------------------------------------------------
  // STOP NARRATION
  // ---------------------------------------------------------

  const stopNarration = useCallback(() => {
    const synth = synthRef.current;

    if (synth) {
      synth.cancel();
    }

    utteranceRef.current = null;
    setIsSpeaking(false);
  }, []);

  // ---------------------------------------------------------
  // VOICE SEARCH
  // ---------------------------------------------------------

  const findVoice = useCallback(
    (languageCode: string): SpeechSynthesisVoice | null => {
      const synth = synthRef.current;

      if (!synth) {
        return null;
      }

      const voices = synth.getVoices();

      if (!voices.length) {
        return null;
      }

      const bcp47 = getBcp47(languageCode);

      const target = bcp47.toLowerCase();

      const prefix = target
        .split("-")[0]
        .toLowerCase();

      console.log(
        `Looking for voice: ${languageCode} / ${bcp47}`
      );

      // -----------------------------------------------------
      // 1. EXACT BCP-47 MATCH
      // -----------------------------------------------------

      const exact = voices.find(
        (voice) =>
          voice.lang.toLowerCase() === target
      );

      if (exact) {
        console.log(
          "Exact voice found:",
          exact.name,
          exact.lang
        );

        return exact;
      }

      // -----------------------------------------------------
      // 2. LANGUAGE FAMILY MATCH
      // -----------------------------------------------------

      const family = voices.find(
        (voice) =>
          voice.lang
            .toLowerCase()
            .split("-")[0] === prefix
      );

      if (family) {
        console.log(
          "Language-family voice found:",
          family.name,
          family.lang
        );

        return family;
      }

      // -----------------------------------------------------
      // 3. SEARCH VOICE NAME
      // -----------------------------------------------------

      const languageNames: Record<
        string,
        string[]
      > = {
        en: [
          "english",
          "google us english",
          "microsoft david",
          "microsoft mark",
          "microsoft zira",
        ],

        hi: [
          "hindi",
          "हिन्दी",
          "google hindi",
          "microsoft hemant",
        ],

        gu: [
          "gujarati",
          "ગુજરાતી",
          "google gujarati",
        ],

        ta: [
          "tamil",
          "தமிழ்",
          "google tamil",
        ],

        te: [
          "telugu",
          "తెలుగు",
          "google telugu",
        ],

        bn: [
          "bengali",
          "বাংলা",
          "google bengali",
        ],

        mr: [
          "marathi",
          "मराठी",
          "google marathi",
        ],

        kn: [
          "kannada",
          "ಕನ್ನಡ",
          "google kannada",
        ],

        pa: [
          "punjabi",
          "ਪੰਜਾਬੀ",
          "google punjabi",
        ],

        fr: [
          "french",
          "français",
        ],

        es: [
          "spanish",
          "español",
        ],

        de: [
          "german",
          "deutsch",
        ],

        ar: [
          "arabic",
          "العربية",
        ],

        ja: [
          "japanese",
          "日本語",
        ],

        ko: [
          "korean",
          "한국어",
        ],

        pt: [
          "portuguese",
          "português",
        ],

        ru: [
          "russian",
          "русский",
        ],

        it: [
          "italian",
          "italiano",
        ],
      };

      const possibleNames =
        languageNames[prefix] || [];

      for (const name of possibleNames) {
        const found = voices.find((voice) =>
          voice.name
            .toLowerCase()
            .includes(name.toLowerCase())
        );

        if (found) {
          console.log(
            "Voice-name match:",
            found.name,
            found.lang
          );

          return found;
        }
      }

      return null;
    },
    []
  );

  // ---------------------------------------------------------
  // SPLIT TEXT INTO SAFE SPEECH CHUNKS
  // ---------------------------------------------------------

  const splitTextForSpeech = (
    text: string
  ): string[] => {
    const cleanText = text
      .replace(/[\*#`_]/g, "")
      .replace(/\s+/g, " ")
      .trim();

    if (!cleanText) {
      return [];
    }

    // First split by sentence punctuation.
    const sentences =
      cleanText.match(
        /[^.!?।！？]+[.!?।！？]?/g
      ) || [cleanText];

    const chunks: string[] = [];

    for (const sentence of sentences) {
      const trimmed = sentence.trim();

      if (!trimmed) {
        continue;
      }

      // Keep individual utterances reasonably short.
      if (trimmed.length <= 220) {
        chunks.push(trimmed);
        continue;
      }

      const words = trimmed.split(" ");

      let current = "";

      for (const word of words) {
        const candidate = current
          ? `${current} ${word}`
          : word;

        if (candidate.length > 180) {
          if (current) {
            chunks.push(current);
          }

          current = word;
        } else {
          current = candidate;
        }
      }

      if (current) {
        chunks.push(current);
      }
    }

    return chunks;
  };

  // ---------------------------------------------------------
  // SPEAK TEXT
  // ---------------------------------------------------------

  const speakText = useCallback(
    (
      text: string,
      languageCode: string
    ) => {
      if (typeof window === "undefined") {
        return;
      }

      const synth = synthRef.current;

      if (!synth) {
        console.warn(
          "Speech synthesis unavailable."
        );
        return;
      }

      if (!text || !text.trim()) {
        return;
      }

      // Stop current speech.
      synth.cancel();

      setIsSpeaking(false);

      const bcp47 =
        getBcp47(languageCode);

      const chunks =
        splitTextForSpeech(text);

      if (!chunks.length) {
        return;
      }

      const startSpeech = () => {
        const voice =
          findVoice(languageCode);

        console.log(
          "--------------------------------"
        );

        console.log(
          "Speech language:",
          languageCode
        );

        console.log(
          "BCP-47:",
          bcp47
        );

        console.log(
          "Voice:",
          voice
            ? `${voice.name} (${voice.lang})`
            : "NOT FOUND"
        );

        console.log(
          "--------------------------------"
        );

        // IMPORTANT:
        // Never use an unrelated language voice.
        if (!voice) {
          setActiveVoiceName(
            `No ${languageCode} voice available`
          );

          setIsSpeaking(false);

          console.warn(
            `No browser voice found for ${languageCode} (${bcp47}).`
          );

          return;
        }

        let index = 0;
        let cancelled = false;

        const speakNext = () => {
          if (cancelled) {
            return;
          }

          if (index >= chunks.length) {
            setIsSpeaking(false);
            utteranceRef.current = null;

            console.log(
              "Speech completed:",
              languageCode
            );

            return;
          }

          const chunk = chunks[index];

          const utterance =
            new SpeechSynthesisUtterance(
              chunk
            );

          utteranceRef.current =
            utterance;

          // Use the actual selected voice language.
          utterance.voice = voice;

          utterance.lang =
            voice.lang || bcp47;

          utterance.rate = 0.9;
          utterance.pitch = 1;
          utterance.volume = 1;

          utterance.onstart = () => {
            setIsSpeaking(true);

            setActiveVoiceName(
              `${voice.name} (${voice.lang})`
            );
          };

          utterance.onend = () => {
            index += 1;

            window.setTimeout(
              speakNext,
              60
            );
          };

          utterance.onerror = (event) => {
            console.error(
              "Speech synthesis error:",
              event
            );

            setIsSpeaking(false);

            utteranceRef.current =
              null;
          };

          try {
            synth.speak(utterance);
          } catch (error) {
            console.error(
              "Could not start speech:",
              error
            );

            setIsSpeaking(false);
          }
        };

        speakNext();
      };

      // Give Chrome time to populate its voice list.
      const voices = synth.getVoices();

      if (voices.length > 0) {
        window.setTimeout(
          startSpeech,
          100
        );

        return;
      }

      let finished = false;

      const handleVoicesChanged = () => {
        if (finished) {
          return;
        }

        const loaded =
          synth.getVoices();

        if (!loaded.length) {
          return;
        }

        finished = true;

        synth.removeEventListener(
          "voiceschanged",
          handleVoicesChanged
        );

        setVoicesReady(true);

        window.setTimeout(
          startSpeech,
          100
        );
      };

      synth.addEventListener(
        "voiceschanged",
        handleVoicesChanged
      );

      // Final retry.
      window.setTimeout(() => {
        if (finished) {
          return;
        }

        finished = true;

        synth.removeEventListener(
          "voiceschanged",
          handleVoicesChanged
        );

        const loaded =
          synth.getVoices();

        if (loaded.length > 0) {
          setVoicesReady(true);
          startSpeech();
        } else {
          setActiveVoiceName(
            `No browser voices available`
          );

          console.warn(
            "Browser did not provide any TTS voices."
          );
        }
      }, 3000);
    },
    [findVoice]
  );

  // ---------------------------------------------------------
  // LANGUAGE CHANGE
  // ---------------------------------------------------------

  const handleLanguageChange =
    async (
      newLanguage: string
    ) => {
      if (
        newLanguage === language
      ) {
        return;
      }

      stopNarration();

      // If no monument has been identified,
      // only change the selected language.
      if (
        !monumentId ||
        !monumentName ||
        !details
      ) {
        setLanguage(newLanguage);
        setActiveVoiceName(null);
        return;
      }

      setLanguageLoading(true);

      try {
        const response =
          await fetch(
            `${API_BASE_URL}/api/narrate`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body: JSON.stringify({
                monument_name:
                  monumentName,

                language:
                  newLanguage,

                details,
              }),
            }
          );

        if (!response.ok) {
          const errorText =
            await response.text();

          throw new Error(
            `Language change failed (${response.status}): ${errorText}`
          );
        }

        const data =
          await response.json();

        if (
          !data.narration
        ) {
          throw new Error(
            "Backend returned no narration."
          );
        }

        setLanguage(
          newLanguage
        );

        setNarration(
          data.narration
        );

        setActiveVoiceName(null);

        setActiveTab("audio");

        // Wait for React state/UI update.
        window.setTimeout(() => {
          speakText(
            data.narration,
            newLanguage
          );
        }, 300);
      } catch (error) {
        console.error(
          "Language change error:",
          error
        );

        // Keep the selected language.
        setLanguage(
          newLanguage
        );

        alert(
          "The language changed, but the new narration could not be generated. Please try again."
        );
      } finally {
        setLanguageLoading(
          false
        );
      }
    };

  // ---------------------------------------------------------
  // IMAGE IDENTIFICATION
  // ---------------------------------------------------------

  const handleImageCapture =
    async (
      base64Image: string
    ) => {
      setLoading(true);

      stopNarration();

      try {
        const response =
          await fetch(
            `${API_BASE_URL}/api/identify`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body: JSON.stringify({
                image:
                  base64Image,

                language:
                  language,
              }),
            }
          );

        if (!response.ok) {
          const errorText =
            await response.text();

          throw new Error(
            `Backend error ${response.status}: ${errorText}`
          );
        }

        const data =
          await response.json();

        console.log(
          "Identification response:",
          data
        );

        if (
          data.monument_id ===
            "unknown" ||
          !data.details
        ) {
          alert(
            "Monument not recognized. Please try a clearer photo with the monument prominently visible."
          );

          return;
        }

        setMonumentId(
          data.monument_id
        );

        setMonumentName(
          data.canonical_name
        );

        setNarration(
          data.narration
        );

        setDetails(
          data.details
        );

        setActiveTab(
          "audio"
        );

        setActiveVoiceName(
          null
        );

        // Give browser time to update the UI
        // before starting audio.
        window.setTimeout(() => {
          speakText(
            data.narration,
            language
          );
        }, 500);
      } catch (error) {
        console.error(
          "Identification error:",
          error
        );

        alert(
          `Could not connect to the AI backend.

API: ${API_BASE_URL}

${String(error)}`
        );
      } finally {
        setLoading(false);
      }
    };

  // ---------------------------------------------------------
  // RESET APP
  // ---------------------------------------------------------

  const resetApp = () => {
    stopNarration();

    setMonumentId(null);
    setMonumentName(null);
    setNarration(null);
    setDetails(null);

    setActiveVoiceName(null);

    setActiveTab("camera");
  };

  // ---------------------------------------------------------
  // UI
  // ---------------------------------------------------------

  return (
    <main className="min-h-screen bg-slate-50 text-gray-900">

      {/* HEADER */}

      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-md mx-auto px-4 py-3 flex items-center justify-between">

          <div className="flex items-center space-x-2.5">

            <div className="w-9 h-9 bg-rose-500 rounded-xl flex items-center justify-center text-white font-bold shadow-md shadow-rose-200">
              HV
            </div>

            <div>
              <h1 className="font-extrabold text-base tracking-tight text-gray-900 leading-tight">
                HeritageVoice{" "}
                <span className="text-rose-500">
                  AI
                </span>
              </h1>

              <p className="text-[10px] text-gray-500 font-semibold tracking-wider uppercase">
                OMNIKON Hackathon 2026
              </p>
            </div>

          </div>

          <div className="text-right flex flex-col items-end gap-1">

            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold bg-gray-100 text-gray-700 border border-gray-200">
              Tech Sparker
            </span>

            <span
              className={`inline-flex items-center gap-1 text-[9px] font-semibold ${
                voicesReady
                  ? "text-green-600"
                  : "text-amber-500"
              }`}
            >

              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  voicesReady
                    ? "bg-green-500"
                    : "bg-amber-400 animate-pulse"
                }`}
              />

              {voicesReady
                ? "Voice Ready"
                : "Loading voices…"}

            </span>

          </div>

        </div>
      </header>

      {/* MAIN */}

      <div className="max-w-md mx-auto px-4 pt-4 space-y-4">

        {/* LANGUAGE */}

        <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm">

          <LanguageSelector
            selectedLanguage={language}
            onChange={
              handleLanguageChange
            }
          />

          {languageLoading &&
            monumentId && (
              <p className="mt-2 text-[10px] text-rose-500 font-semibold">
                Generating{" "}
                {language}{" "}
                narration…
              </p>
            )}

        </div>

        {/* TABS */}

        <div className="grid grid-cols-3 bg-white p-1 rounded-2xl border border-gray-200 shadow-sm">

          <button
            onClick={() =>
              setActiveTab("camera")
            }
            className={`flex flex-col items-center py-2 px-1 rounded-xl transition-all ${
              activeTab === "camera"
                ? "bg-rose-500 text-white font-bold shadow-sm"
                : "text-gray-500 hover:text-gray-800 font-medium"
            }`}
          >
            <Camera className="w-5 h-5 mb-0.5" />

            <span className="text-[11px]">
              1. Scan
            </span>
          </button>

          <button
            onClick={() =>
              monumentId &&
              setActiveTab("audio")
            }
            disabled={!monumentId}
            className={`flex flex-col items-center py-2 px-1 rounded-xl transition-all ${
              activeTab === "audio"
                ? "bg-rose-500 text-white font-bold shadow-sm"
                : monumentId
                ? "text-gray-500 hover:text-gray-800 font-medium"
                : "text-gray-300 cursor-not-allowed"
            }`}
          >
            <Volume2 className="w-5 h-5 mb-0.5" />

            <span className="text-[11px]">
              2. Listen
            </span>
          </button>

          <button
            onClick={() =>
              monumentId &&
              setActiveTab("chat")
            }
            disabled={!monumentId}
            className={`flex flex-col items-center py-2 px-1 rounded-xl transition-all ${
              activeTab === "chat"
                ? "bg-rose-500 text-white font-bold shadow-sm"
                : monumentId
                ? "text-gray-500 hover:text-gray-800 font-medium"
                : "text-gray-300 cursor-not-allowed"
            }`}
          >
            <MessageSquare className="w-5 h-5 mb-0.5" />

            <span className="text-[11px]">
              3. Discuss
            </span>
          </button>

        </div>

        {/* CONTENT */}

        <div className="transition-all duration-200">

          {/* CAMERA */}

          {activeTab ===
            "camera" && (
            <div className="space-y-4">

              <CameraFeed
                onCapture={
                  handleImageCapture
                }
                isLoading={
                  loading
                }
              />

              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-2xl p-4 flex gap-3 text-blue-900 shadow-sm">

                <Info className="w-5 h-5 shrink-0 text-blue-600 mt-0.5" />

                <div className="text-xs space-y-1">

                  <h4 className="font-bold">
                    How to use HeritageVoice AI:
                  </h4>

                  <ul className="list-disc pl-4 space-y-1 text-blue-800/90 font-medium">

                    <li>
                      Select your preferred guide language.
                    </li>

                    <li>
                      Point your camera at any monument and tap Identify Monument.
                    </li>

                    <li>
                      Or upload / drag-and-drop a monument photo.
                    </li>

                    <li>
                      The AI identifies the monument and speaks its story in your chosen language.
                    </li>

                    <li>
                      After identification, changing language does not require another scan.
                    </li>

                  </ul>

                </div>
              </div>

            </div>
          )}

          {/* AUDIO */}

          {activeTab ===
            "audio" &&
            monumentName &&
            narration && (
              <div className="space-y-4">

                <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm space-y-4">

                  <div className="flex justify-between items-start">

                    <div>

                      <span className="text-[10px] text-rose-500 font-bold uppercase tracking-wider">
                        Identified Structure
                      </span>

                      <h2 className="font-extrabold text-xl text-gray-900 leading-tight">
                        {monumentName}
                      </h2>

                    </div>

                    <button
                      onClick={
                        resetApp
                      }
                      className="p-2 text-gray-400 hover:text-rose-500 hover:bg-rose-50 rounded-xl transition-all border border-gray-200"
                      title="Scan another monument"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>

                  </div>

                  {/* AUDIO CONTROL */}

                  <div className="bg-slate-50 border border-slate-100 rounded-xl p-3.5 flex items-center justify-between gap-4">

                    <div className="flex items-center gap-3">

                      <div
                        className={`p-2 rounded-lg ${
                          isSpeaking
                            ? "bg-rose-500 text-white animate-pulse"
                            : "bg-gray-200 text-gray-600"
                        }`}
                      >
                        <Volume2 className="w-5 h-5" />
                      </div>

                      <div>

                        <h4 className="font-bold text-xs">
                          Audio Guide Playback
                        </h4>

                        <p className="text-[10px] text-gray-500 font-medium">
                          Language:{" "}
                          {language}
                        </p>

                        {activeVoiceName && (
                          <p
                            className="text-[9px] text-gray-400 font-medium truncate max-w-[180px]"
                            title={
                              activeVoiceName
                            }
                          >
                            🔊{" "}
                            {
                              activeVoiceName
                            }
                          </p>
                        )}

                      </div>

                    </div>

                    <button
                      onClick={() =>
                        isSpeaking
                          ? stopNarration()
                          : speakText(
                              narration,
                              language
                            )
                      }
                      disabled={
                        languageLoading
                      }
                      className={`py-2 px-4 font-bold text-xs rounded-lg transition-all ${
                        isSpeaking
                          ? "bg-gray-800 text-white hover:bg-gray-900"
                          : "bg-rose-500 text-white hover:bg-rose-600 shadow-md shadow-rose-100"
                      }`}
                    >
                      {isSpeaking
                        ? "⏹ Stop"
                        : "▶ Listen"}
                    </button>

                  </div>

                  {/* STORY */}

                  <div className="border-t border-gray-100 pt-4">

                    <h4 className="font-bold text-xs text-gray-500 mb-2 uppercase tracking-wide">
                      Historical Story
                    </h4>

                    <div className="bg-slate-50/50 rounded-xl p-3.5 border border-slate-100/50">

                      <p className="text-sm font-medium leading-relaxed text-gray-800 whitespace-pre-wrap italic">
                        &ldquo;
                        {narration}
                        &rdquo;
                      </p>

                    </div>

                  </div>

                </div>

                {/* DETAILS */}

                {details && (
                  <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm space-y-3">

                    <div className="flex items-center space-x-2 border-b border-gray-100 pb-2">

                      <Landmark className="w-4 h-4 text-rose-500" />

                      <h3 className="font-bold text-sm text-gray-800">
                        Historical Record
                      </h3>

                    </div>

                    <div className="grid grid-cols-2 gap-3.5 text-xs">

                      <div>
                        <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">
                          Location
                        </p>

                        <p className="font-bold text-gray-800 leading-snug">
                          {details.location ||
                            "—"}
                        </p>
                      </div>

                      <div>
                        <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">
                          Built By
                        </p>

                        <p className="font-bold text-gray-800 leading-snug">
                          {details.built_by ||
                            "—"}
                        </p>
                      </div>

                      <div>
                        <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">
                          Construction Era
                        </p>

                        <p className="font-bold text-gray-800 leading-snug">
                          {details.construction_year ||
                            "—"}
                        </p>
                      </div>

                      <div>
                        <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">
                          Architectural Style
                        </p>

                        <p className="font-bold text-gray-800 leading-snug">
                          {details.theme ||
                            "—"}
                        </p>
                      </div>

                    </div>

                    {Array.isArray(
                      details.key_facts
                    ) &&
                      details.key_facts
                        .length >
                        0 && (
                        <div className="border-t border-gray-100 pt-3 space-y-1.5">

                          <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">
                            Key Highlights
                          </p>

                          <ul className="space-y-1.5">

                            {details.key_facts.map(
                              (
                                fact,
                                index
                              ) => (
                                <li
                                  key={
                                    index
                                  }
                                  className="flex gap-2 text-xs font-semibold text-gray-700 leading-normal"
                                >
                                  <span className="text-rose-500">
                                    •
                                  </span>

                                  <span>
                                    {
                                      fact
                                    }
                                  </span>
                                </li>
                              )
                            )}

                          </ul>

                        </div>
                      )}

                    <button
                      onClick={() =>
                        setActiveTab(
                          "chat"
                        )
                      }
                      className="w-full py-2.5 bg-gray-900 hover:bg-black text-white font-bold rounded-xl text-xs flex items-center justify-center gap-2 shadow-sm transition-colors"
                    >
                      <MessageSquare className="w-4 h-4" />

                      Ask Follow-up Questions
                    </button>

                  </div>
                )}

              </div>
            )}

          {/* CHAT */}

          {activeTab ===
            "chat" &&
            monumentId &&
            monumentName && (
              <ChatWindow
                monumentId={
                  monumentId
                }
                monumentName={
                  monumentName
                }
                monumentDetails={
                  details
                }
                language={
                  language
                }
              />
            )}

        </div>
      </div>

      <Footer />

    </main>
  );
}
