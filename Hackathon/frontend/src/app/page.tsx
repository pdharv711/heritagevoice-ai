"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Camera, Volume2, MessageSquare, RefreshCw, Landmark, AlertCircle, Info, Globe } from "lucide-react";
import LanguageSelector, { getBcp47 } from "@/components/LanguageSelector";
import CameraFeed from "@/components/CameraFeed";
import ChatWindow from "@/components/ChatWindow";

export default function Home() {
  const [language, setLanguage] = useState("English");
  const [monumentId, setMonumentId] = useState<string | null>(null);
  const [monumentName, setMonumentName] = useState<string | null>(null);
  const [narration, setNarration] = useState<string | null>(null);
  const [details, setDetails] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"camera" | "audio" | "chat">("camera");

  // Audio Playback State
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voicesReady, setVoicesReady] = useState(false);
  const [activeVoiceName, setActiveVoiceName] = useState<string | null>(null);
  const synthRef = useRef<SpeechSynthesis | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // ──────────────────────────────────────────────────────────────
  // Initialize SpeechSynthesis and wait for voices to load
  // Chrome loads voices asynchronously — we must listen for the
  // 'voiceschanged' event before trying to select a voice.
  // ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (typeof window === "undefined") return;
    const synth = window.speechSynthesis;
    synthRef.current = synth;

    const markReady = () => setVoicesReady(true);

    // Voices may already be loaded (Firefox / some builds)
    if (synth.getVoices().length > 0) {
      setVoicesReady(true);
    }
    // Otherwise wait for the async event (Chrome)
    synth.addEventListener("voiceschanged", markReady);
    return () => synth.removeEventListener("voiceschanged", markReady);
  }, []);

  // Stop speech when tab or language changes
  useEffect(() => {
    stopNarration();
    setActiveVoiceName(null);
  }, [activeTab, language]);

  // ──────────────────────────────────────────────────────────────
  // Smart BCP-47 voice picker with multi-level fallback
  // 1. Exact BCP-47 match (e.g. "hi-IN")
  // 2. Region-agnostic prefix match (e.g. "hi")
  // 3. Any voice with a matching lang attribute
  // 4. Browser default (no voice set)
  // ──────────────────────────────────────────────────────────────
  const pickVoice = useCallback(
    (bcp47: string): SpeechSynthesisVoice | null => {
      if (!synthRef.current) return null;
      const voices = synthRef.current.getVoices();
      const prefix = bcp47.split("-")[0].toLowerCase(); // e.g. "hi" from "hi-IN"

      // 1. Exact BCP-47
      let voice = voices.find((v) => v.lang.toLowerCase() === bcp47.toLowerCase());
      // 2. Starts-with prefix
      if (!voice) voice = voices.find((v) => v.lang.toLowerCase().startsWith(prefix));
      // 3. Contains prefix anywhere
      if (!voice) voice = voices.find((v) => v.lang.toLowerCase().includes(prefix));
      return voice ?? null;
    },
    []
  );

  const speakText = useCallback(
    (text: string, langCode: string) => {
      if (!synthRef.current) return;
      stopNarration();

      const cleanText = text.replace(/[*#`_\-]/g, "");
      const bcp47 = getBcp47(langCode);

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utteranceRef.current = utterance;

      const voice = pickVoice(bcp47);
      if (voice) {
        utterance.voice = voice;
        utterance.lang = voice.lang;
        setActiveVoiceName(voice.name);
      } else {
        utterance.lang = bcp47;
        setActiveVoiceName(`System default (${bcp47})`);
      }

      utterance.rate = 0.92;
      utterance.pitch = 1.0;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = (e) => {
        console.warn("TTS error:", e);
        setIsSpeaking(false);
      };

      synthRef.current.speak(utterance);
    },
    [pickVoice]
  );

  const playNarration = () => {
    if (!narration) return;
    speakText(narration, language);
  };

  const stopNarration = () => {
    synthRef.current?.cancel();
    setIsSpeaking(false);
  };

  // ──────────────────────────────────────────────────────────────
  // Call backend to identify monument from image
  // ──────────────────────────────────────────────────────────────
  const handleImageCapture = async (base64Image: string) => {
    setLoading(true);
    stopNarration();

    try {
     const response = await fetch("https://heritagevoice-ai.onrender.com/api/identify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: base64Image, language }),
      });

      if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
      }

      const data = await response.json();

      if (data.monument_id !== "unknown") {
        setMonumentId(data.monument_id);
        setMonumentName(data.canonical_name);
        setNarration(data.narration);
        setDetails(data.details);
        setActiveTab("audio");

        // Auto-play narration once voices are guaranteed ready
        const autoPlay = () => speakText(data.narration, language);
        if (voicesReady) {
          setTimeout(autoPlay, 150);
        } else {
          // Wait for voices to load (Chrome), then play
          const synth = synthRef.current;
          if (synth) {
            const onReady = () => {
              setVoicesReady(true);
              setTimeout(autoPlay, 150);
              synth.removeEventListener("voiceschanged", onReady);
            };
            synth.addEventListener("voiceschanged", onReady);
            // Safety timeout — play anyway after 3 seconds
            setTimeout(() => {
              synth.removeEventListener("voiceschanged", onReady);
              autoPlay();
            }, 3000);
          }
        }
      } else {
        alert("Monument not recognized. Please try a clearer image with the monument prominently visible!");
      }
    } catch (err) {
      console.error(err);
      alert(
        "Error reaching AI guide. Ensure the FastAPI backend is running on port 8000.\n\nRun: python main.py (inside the backend folder)"
      );
    } finally {
      setLoading(false);
    }
  };

  // Reset to scan a new monument
  const resetApp = () => {
    stopNarration();
    setMonumentId(null);
    setMonumentName(null);
    setNarration(null);
    setDetails(null);
    setActiveVoiceName(null);
    setActiveTab("camera");
  };

  return (
    <main className="min-h-screen bg-slate-50 text-gray-900 pb-12">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-md mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 bg-rose-500 rounded-xl flex items-center justify-center text-white font-bold shadow-md shadow-rose-200">
              HV
            </div>
            <div>
              <h1 className="font-extrabold text-base tracking-tight text-gray-900 leading-tight">
                HeritageVoice <span className="text-rose-500">AI</span>
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
            {/* Voice ready indicator */}
            <span
              className={`inline-flex items-center gap-1 text-[9px] font-semibold ${
                voicesReady ? "text-green-600" : "text-amber-500"
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${voicesReady ? "bg-green-500" : "bg-amber-400 animate-pulse"}`} />
              {voicesReady ? "Voice Ready" : "Loading voices…"}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-md mx-auto px-4 pt-4 space-y-4">
        {/* Language Selector */}
        <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm">
          <LanguageSelector selectedLanguage={language} onChange={setLanguage} />
        </div>

        {/* Tab Controls */}
        <div className="grid grid-cols-3 bg-white p-1 rounded-2xl border border-gray-200 shadow-sm">
          <button
            onClick={() => setActiveTab("camera")}
            className={`flex flex-col items-center py-2 px-1 rounded-xl transition-all duration-200 ${
              activeTab === "camera"
                ? "bg-rose-500 text-white font-bold shadow-sm"
                : "text-gray-500 hover:text-gray-800 font-medium"
            }`}
          >
            <Camera className="w-5 h-5 mb-0.5" />
            <span className="text-[11px]">1. Scan</span>
          </button>
          <button
            onClick={() => { if (monumentId) setActiveTab("audio"); }}
            disabled={!monumentId}
            className={`flex flex-col items-center py-2 px-1 rounded-xl transition-all duration-200 ${
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
            onClick={() => { if (monumentId) setActiveTab("chat"); }}
            disabled={!monumentId}
            className={`flex flex-col items-center py-2 px-1 rounded-xl transition-all duration-200 ${
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

        {/* Tab Content */}
        <div className="transition-all duration-200">

          {/* ── CAMERA / SCAN TAB ── */}
          {activeTab === "camera" && (
            <div className="space-y-4">
              <CameraFeed onCapture={handleImageCapture} isLoading={loading} />

              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-2xl p-4 flex gap-3 text-blue-900 shadow-sm">
                <Info className="w-5 h-5 shrink-0 text-blue-600 mt-0.5" />
                <div className="text-xs space-y-1">
                  <h4 className="font-bold">How to use HeritageVoice AI:</h4>
                  <ul className="list-disc pl-4 space-y-1 text-blue-800/90 font-medium">
                    <li>Select your preferred tour guide language above.</li>
                    <li>Point your device camera at <strong>any</strong> monument and tap <b>Identify Monument</b>.</li>
                    <li>Or <strong>upload</strong> / <strong>drag-and-drop</strong> a monument photo.</li>
                    <li>The AI will speak the monument story in your chosen language!</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* ── AUDIO / LISTEN TAB ── */}
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

                {/* Playback Controls */}
                <div className="bg-slate-50 border border-slate-100 rounded-xl p-3.5 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${isSpeaking ? "bg-rose-500 text-white animate-pulse" : "bg-gray-200 text-gray-600"}`}>
                      <Volume2 className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-bold text-xs">Audio Guide Playback</h4>
                      <p className="text-[10px] text-gray-500 font-medium">
                        Language: {language}
                      </p>
                      {activeVoiceName && (
                        <p className="text-[9px] text-gray-400 font-medium truncate max-w-[120px]" title={activeVoiceName}>
                          🔊 {activeVoiceName}
                        </p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={isSpeaking ? stopNarration : playNarration}
                    className={`py-2 px-4 font-bold text-xs rounded-lg transition-all ${
                      isSpeaking
                        ? "bg-gray-800 text-white hover:bg-gray-900"
                        : "bg-rose-500 text-white hover:bg-rose-600 shadow-md shadow-rose-100"
                    }`}
                  >
                    {isSpeaking ? "⏹ Stop" : "▶ Listen"}
                  </button>
                </div>

                {/* Narration Text */}
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

              {/* Factual Metadata */}
              {details && (
                <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm space-y-3">
                  <div className="flex items-center space-x-2 border-b border-gray-100 pb-2">
                    <Landmark className="w-4 h-4 text-rose-500" />
                    <h3 className="font-bold text-sm text-gray-800">Historical Record</h3>
                  </div>

                  <div className="grid grid-cols-2 gap-3.5 text-xs">
                    <div>
                      <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">Location</p>
                      <p className="font-bold text-gray-800 leading-snug">{details.location}</p>
                    </div>
                    <div>
                      <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">Built By</p>
                      <p className="font-bold text-gray-800 leading-snug">{details.built_by}</p>
                    </div>
                    <div>
                      <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">Construction Era</p>
                      <p className="font-bold text-gray-800 leading-snug">{details.construction_year}</p>
                    </div>
                    <div>
                      <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">Architectural Style</p>
                      <p className="font-bold text-gray-800 leading-snug">{details.theme}</p>
                    </div>
                  </div>

                  <div className="border-t border-gray-100 pt-3 space-y-1.5">
                    <p className="text-gray-400 font-semibold uppercase text-[9px] tracking-wider">Key Highlights</p>
                    <ul className="space-y-1.5">
                      {details.key_facts.map((fact: string, idx: number) => (
                        <li key={idx} className="flex gap-2 text-xs font-semibold text-gray-700 leading-normal">
                          <span className="text-rose-500 select-none">•</span>
                          <span>{fact}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="pt-2">
                    <button
                      onClick={() => setActiveTab("chat")}
                      className="w-full py-2.5 bg-gray-900 hover:bg-black text-white font-bold rounded-xl text-xs flex items-center justify-center gap-2 shadow-sm transition-colors"
                    >
                      <MessageSquare className="w-4 h-4" />
                      Ask Follow-up Questions
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── CHAT / DISCUSS TAB ── */}
          {activeTab === "chat" && monumentId && monumentName && (
            <ChatWindow
              monumentId={monumentId}
              monumentName={monumentName}
              language={language}
            />
          )}
        </div>
      </div>
    </main>
  );
}
