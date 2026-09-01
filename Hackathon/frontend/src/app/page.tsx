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
import LanguageSelector, { getBcp47 } from "@/components/LanguageSelector";
import CameraFeed from "@/components/CameraFeed";
import ChatWindow from "@/components/ChatWindow";
import Footer from "@/components/Footer";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://heritagevoice-ai.onrender.com";

export default function Home() {
  const [language, setLanguage] = useState("English");
  const [monumentId, setMonumentId] = useState<string | null>(null);
  const [monumentName, setMonumentName] = useState<string | null>(null);
  const [narration, setNarration] = useState<string | null>(null);
  const [details, setDetails] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [languageLoading, setLanguageLoading] = useState(false);
  const [activeTab, setActiveTab] =
    useState<"camera" | "audio" | "chat">("camera");

  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voicesReady, setVoicesReady] = useState(false);
  const [activeVoiceName, setActiveVoiceName] = useState<string | null>(null);

  const synthRef = useRef<SpeechSynthesis | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // ---------------------------------------------------------
  // INITIALIZE BROWSER SPEECH SYNTHESIS
  // ---------------------------------------------------------
  useEffect(() => {
    if (typeof window === "undefined") return;

    const synth = window.speechSynthesis;
    synthRef.current = synth;

    const loadVoices = () => {
      const voices = synth.getVoices();

      if (voices.length > 0) {
        setVoicesReady(true);

        console.log(
          "Available browser voices:",
          voices.map((v) => `${v.name} (${v.lang})`)
        );
      }
    };

    loadVoices();

    synth.addEventListener("voiceschanged", loadVoices);

    return () => {
      synth.removeEventListener("voiceschanged", loadVoices);
      synth.cancel();
    };
  }, []);

  // ---------------------------------------------------------
  // STOP SPEECH
  // ---------------------------------------------------------
  const stopNarration = useCallback(() => {
    if (synthRef.current) {
      synthRef.current.cancel();
    }

    setIsSpeaking(false);
  }, []);

  // ---------------------------------------------------------
  // FIND BEST VOICE FOR LANGUAGE
  // ---------------------------------------------------------
  const pickVoice = useCallback((bcp47: string) => {
    if (!synthRef.current) return null;

    const voices = synthRef.current.getVoices();

    if (!voices.length) {
      return null;
    }

    const target = bcp47.toLowerCase();
    const prefix = target.split("-")[0];

    // 1. Exact language match
    const exact = voices.find(
      (voice) => voice.lang.toLowerCase() === target
    );

    if (exact) {
      return exact;
    }

    // 2. Language prefix match
    const prefixMatch = voices.find((voice) =>
      voice.lang.toLowerCase().startsWith(prefix)
    );

    if (prefixMatch) {
      return prefixMatch;
    }

    // 3. Search voice name for language
    const languageNames: Record<string, string[]> = {
      en: ["english", "united states", "uk"],
      hi: ["hindi", "हिन्दी", "google hindi"],
      ta: ["tamil", "தமிழ்", "google tamil"],
      gu: ["gujarati", "ગુજરાતી", "google gujarati"],
      te: ["telugu", "తెలుగు"],
      bn: ["bengali", "বাংলা"],
      mr: ["marathi", "मराठी"],
      kn: ["kannada", "ಕನ್ನಡ"],
      pa: ["punjabi", "ਪੰਜਾਬੀ"],
      fr: ["french", "français"],
      es: ["spanish", "español"],
      de: ["german", "deutsch"],
      ar: ["arabic", "العربية"],
      ja: ["japanese", "日本語"],
      ko: ["korean", "한국어"],
      pt: ["portuguese", "português"],
      ru: ["russian", "русский"],
      it: ["italian", "italiano"],
    };

    const preferredNames = languageNames[prefix] || [];

    for (const name of preferredNames) {
      const found = voices.find((voice) =>
        voice.name.toLowerCase().includes(name.toLowerCase())
      );

      if (found) {
        return found;
      }
    }

    return null;
  }, []);

  // ---------------------------------------------------------
  // SPEAK TEXT
  // ---------------------------------------------------------
  const speakText = useCallback(
    (text: string, languageCode: string) => {
      if (typeof window === "undefined") return;

      const synth = synthRef.current;

      if (!synth || !text) {
        console.warn("Speech synthesis is not available.");
        return;
      }

      // Stop any previous narration.
      synth.cancel();
      setIsSpeaking(false);

      const cleanText = text
        .replace(/[*#`_]/g, "")
        .replace(/\s+/g, " ")
        .trim();

      if (!cleanText) return;

      const bcp47 = getBcp47(languageCode);
      const languagePrefix = bcp47.split("-")[0].toLowerCase();

      const speak = () => {
        const voices = synth.getVoices();

        console.log(
          "Available voices:",
          voices.map((v) => `${v.name} (${v.lang})`)
        );

        const voice = pickVoice(bcp47);

        console.log("Requested language:", languageCode);
        console.log("Requested BCP-47:", bcp47);
        console.log(
          "Selected voice:",
          voice ? `${voice.name} (${voice.lang})` : "NONE"
        );

        // Important: do not silently use an unrelated language voice.
        // If Tamil/Gujarati/etc. is unavailable, the user gets a clear
        // status instead of hearing the wrong language.
        if (!voice) {
          setActiveVoiceName(`No ${languageCode} voice installed`);
          console.warn(
            `No browser TTS voice is available for ${languageCode} (${bcp47}).`
          );
          return;
        }

        // Long browser utterances can fail or stop unexpectedly.
        // Split narration into small sentence-based chunks.
        const chunks = cleanText
          .match(/[^.!?。！？।]+[.!?。！？।]*/g)
          ?.map((part) => part.trim())
          .filter(Boolean) ?? [cleanText];

        let index = 0;
        let started = false;

        const speakNext = () => {
          if (index >= chunks.length) {
            setIsSpeaking(false);
            console.log("Speech finished:", languageCode);
            return;
          }

          const utterance = new SpeechSynthesisUtterance(chunks[index]);
          utteranceRef.current = utterance;

          utterance.lang = bcp47;
          utterance.voice = voice;
          utterance.rate = 0.90;
          utterance.pitch = 1;
          utterance.volume = 1;

          utterance.onstart = () => {
            started = true;
            setIsSpeaking(true);
            setActiveVoiceName(`${voice.name} (${voice.lang})`);
            console.log(
              `Speech started: ${languageCode} using ${voice.name}`
            );
          };

          utterance.onend = () => {
            index += 1;
            window.setTimeout(speakNext, 40);
          };

          utterance.onerror = (event) => {
            console.error("Speech error:", event);

            if (
              event.error !== "canceled" &&
              event.error !== "interrupted"
            ) {
              setIsSpeaking(false);

              if (!started) {
                setActiveVoiceName(
                  `${voice.name} could not speak ${languageCode}`
                );
              }
            }
          };

          try {
            synth.speak(utterance);
          } catch (error) {
            console.error("Speech synthesis failed:", error);
            setIsSpeaking(false);
          }
        };

        speakNext();
      };

      // Chrome can return an empty voice list on the first call.
      if (synth.getVoices().length > 0) {
        window.setTimeout(speak, 100);
      } else {
        const onVoicesChanged = () => {
          synth.removeEventListener("voiceschanged", onVoicesChanged);
          window.setTimeout(speak, 100);
        };

        synth.addEventListener("voiceschanged", onVoicesChanged);

        // Final fallback if Chrome does not fire voiceschanged.
        window.setTimeout(() => {
          synth.removeEventListener("voiceschanged", onVoicesChanged);
          if (!synth.getVoices().length) {
            setActiveVoiceName(
              `No browser voices available for ${languageCode}`
            );
            console.warn(
              `No browser voices loaded for ${languageCode} (${languagePrefix}).`
            );
            return;
          }
          speak();
        }, 2500);
      }
    },
    [pickVoice]
  );

  // ---------------------------------------------------------
  // LANGUAGE CHANGE
  // ---------------------------------------------------------
  const handleLanguageChange = async (newLanguage: string) => {
    if (newLanguage === language) return;

    stopNarration();

    // No monument yet
    if (!monumentId || !monumentName || !details) {
      setLanguage(newLanguage);
      return;
    }

    setLanguageLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/narrate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          monument_name: monumentName,
          language: newLanguage,
          details,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();

        throw new Error(
          `Language change failed (${response.status}): ${errorText}`
        );
      }

      const data = await response.json();

      setLanguage(newLanguage);
      setNarration(data.narration);
      setActiveTab("audio");

      setTimeout(() => {
        speakText(data.narration, newLanguage);
      }, 300);
    } catch (error) {
      console.error("Language change error:", error);

      setLanguage(newLanguage);

      alert(
        "The language changed, but the new narration could not be generated. Please try the language again."
      );
    } finally {
      setLanguageLoading(false);
    }
  };

  // ---------------------------------------------------------
  // IMAGE IDENTIFICATION
  // ---------------------------------------------------------
  const handleImageCapture = async (base64Image: string) => {
    setLoading(true);
    stopNarration();

    try {
      const response = await fetch(`${API_BASE_URL}/api/identify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          image: base64Image,
          language,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();

        throw new Error(
          `Backend error ${response.status}: ${errorText}`
        );
      }

      const data = await response.json();

      if (data.monument_id === "unknown" || !data.details) {
        alert(
          "Monument not recognized. Please try a clearer photo with the monument prominently visible."
        );
        return;
      }

      setMonumentId(data.monument_id);
      setMonumentName(data.canonical_name);
      setNarration(data.narration);
      setDetails(data.details);
      setActiveTab("audio");

      const autoPlay = () => {
        speakText(data.narration, language);
      };

      // Wait for browser voices
      if (voicesReady) {
        setTimeout(autoPlay, 300);
      } else {
        const synth = synthRef.current;

        if (synth) {
          const onReady = () => {
            setVoicesReady(true);

            setTimeout(autoPlay, 300);

            synth.removeEventListener("voiceschanged", onReady);
          };

          synth.addEventListener("voiceschanged", onReady);

          // Fallback if voiceschanged never fires
          setTimeout(() => {
            synth.removeEventListener("voiceschanged", onReady);
            autoPlay();
          }, 3000);
        } else {
          autoPlay();
        }
      }
    } catch (error) {
      console.error("Identification error:", error);

      alert(
        `Could not connect to the AI backend.\n\nAPI: ${API_BASE_URL}\n\n${String(
          error
        )}`
      );
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------------------------------------
  // RESET
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
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-md mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 bg-rose-500 rounded-xl flex items-center justify-center text-white font-bold shadow-md shadow-rose-200">
              HV
            </div>

            <div>
              <h1 className="font-extrabold text-base tracking-tight text-gray-900 leading-tight">
                HeritageVoice{" "}
                <span className="text-rose-500">AI</span>
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
                voicesReady ? "text-green-600" : "text-amber-500"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  voicesReady
                    ? "bg-green-500"
                    : "bg-amber-400 animate-pulse"
                }`}
              />

              {voicesReady ? "Voice Ready" : "Loading voices…"}
            </span>
          </div>
        </div>
      </header>

      <div className="max-w-md mx-auto px-4 pt-4 space-y-4">
        <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm">
          <LanguageSelector
            selectedLanguage={language}
            onChange={handleLanguageChange}
          />

          {languageLoading && monumentId && (
            <p className="mt-2 text-[10px] text-rose-500 font-semibold">
              Generating {language} narration…
            </p>
          )}
        </div>

        <div className="grid grid-cols-3 bg-white p-1 rounded-2xl border border-gray-200 shadow-sm">
          <button
            onClick={() => setActiveTab("camera")}
            className={`flex flex-col items-center py-2 px-1 rounded-xl transition-all ${
              activeTab === "camera"
                ? "bg-rose-500 text-white font-bold shadow-sm"
                : "text-gray-500 hover:text-gray-800 font-medium"
            }`}
          >
            <Camera className="w-5 h-5 mb-0.5" />
            <span className="text-[11px]">1. Scan</span>
          </button>

          <button
            onClick={() => monumentId && setActiveTab("audio")}
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
            <span className="text-[11px]">2. Listen</span>
          </button>

          <button
            onClick={() => monumentId && setActiveTab("chat")}
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
            <span className="text-[11px]">3. Discuss</span>
          </button>
        </div>

        <div className="transition-all duration-200">
          {activeTab === "camera" && (
            <div className="space-y-4">
              <CameraFeed
                onCapture={handleImageCapture}
                isLoading={loading}
              />

              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-2xl p-4 flex gap-3 text-blue-900 shadow-sm">
                <Info className="w-5 h-5 shrink-0 text-blue-600 mt-0.5" />

                <div className="text-xs space-y-1">
                  <h4 className="font-bold">
                    How to use HeritageVoice AI:
                  </h4>

                  <ul className="list-disc pl-4 space-y-1 text-blue-800/90 font-medium">
                    <li>Select your preferred guide language.</li>

                    <li>
                      Point your camera at any monument and tap Identify
                      Monument.
                    </li>

                    <li>
                      Or upload / drag-and-drop a monument photo.
                    </li>

                    <li>
                      The AI identifies the monument and speaks its story in
                      your chosen language.
                    </li>

                    <li>
                      After identification, changing language does not require
                      another scan.
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {activeTab === "audio" && monumentName && narration && (
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
                    onClick={resetApp}
                    className="p-2 text-gray-400 hover:text-rose-500 hover:bg-rose-50 rounded-xl transition-all border border-gray-200"
                    title="Scan another monument"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>

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
                        Language: {language}
                      </p>

                      {activeVoiceName && (
                        <p
                          className="text-[9px] text-gray-400 font-medium truncate max-w-[170px]"
                          title={activeVoiceName}
                        >
                          🔊 {activeVoiceName}
                        </p>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={
                      isSpeaking
                        ? stopNarration
                        : () => speakText(narration, language)
                    }
                    disabled={languageLoading}
                    className={`py-2 px-4 font-bold text-xs rounded-lg transition-all ${
                      isSpeaking
                        ? "bg-gray-800 text-white hover:bg-gray-900"
                        : "bg-rose-500 text-white hover:bg-rose-600 shadow-md shadow-rose-100"
                    }`}
                  >
                    {isSpeaking ? "⏹ Stop" : "▶ Listen"}
                  </button>
                </div>

                <div className="border-t border-gray-100 pt-4">
                  <h4 className="font-bold text-xs text-gray-500 mb-2 uppercase tracking-wide">
                    Historical Story
                  </h4>

                  <div className="bg-slate-50/50 rounded-xl p-3.5 border border-slate-100/50">
                    <p className="text-sm font-medium leading-relaxed text-gray-800 whitespace-pre-wrap italic">
                      &ldquo;{narration}&rdquo;
                    </p>
                  </div>
                </div>
              </div>

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
                        {details.location}
                      </p>
                    </div>

                    <div>
                      <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">
                        Built By
                      </p>

                      <p className="font-bold text-gray-800 leading-snug">
                        {details.built_by}
                      </p>
                    </div>

                    <div>
                      <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">
                        Construction Era
                      </p>

                      <p className="font-bold text-gray-800 leading-snug">
                        {details.construction_year}
                      </p>
                    </div>

                    <div>
                      <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">
                        Architectural Style
                      </p>

                      <p className="font-bold text-gray-800 leading-snug">
                        {details.theme}
                      </p>
                    </div>
                  </div>

                  {Array.isArray(details.key_facts) &&
                    details.key_facts.length > 0 && (
                      <div className="border-t border-gray-100 pt-3 space-y-1.5">
                        <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">
                          Key Highlights
                        </p>

                        <ul className="space-y-1.5">
                          {details.key_facts.map(
                            (fact: string, index: number) => (
                              <li
                                key={index}
                                className="flex gap-2 text-xs font-semibold text-gray-700 leading-normal"
                              >
                                <span className="text-rose-500">•</span>
                                <span>{fact}</span>
                              </li>
                            )
                          )}
                        </ul>
                      </div>
                    )}

                  <button
                    onClick={() => setActiveTab("chat")}
                    className="w-full py-2.5 bg-gray-900 hover:bg-black text-white font-bold rounded-xl text-xs flex items-center justify-center gap-2 shadow-sm transition-colors"
                  >
                    <MessageSquare className="w-4 h-4" />
                    Ask Follow-up Questions
                  </button>
                </div>
              )}
            </div>
          )}

          {activeTab === "chat" && monumentId && monumentName && (
            <ChatWindow
              monumentId={monumentId}
              monumentName={monumentName}
              monumentDetails={details}
              language={language}
            />
          )}
        </div>
      </div>

      <Footer />
    </main>
  );
}
