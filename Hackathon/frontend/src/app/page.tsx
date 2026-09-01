
"use client";

import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  Camera,
  Volume2,
  MessageSquare,
  RefreshCw,
  Landmark,
  Info,
} from "lucide-react";

import LanguageSelector from "@/components/LanguageSelector";
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

interface TTSResponse {
  success?: boolean;
  language?: string;
  language_code?: string;
  mime_type?: string;
  sample_rate?: number;
  audio_base64?: string;
  detail?: string;
}

export default function Home() {
  // ---------------------------------------------------------
  // APP STATE
  // ---------------------------------------------------------

  const [language, setLanguage] = useState("English");

  const [monumentId, setMonumentId] =
    useState<string | null>(null);

  const [monumentName, setMonumentName] =
    useState<string | null>(null);

  const [narration, setNarration] =
    useState<string | null>(null);

  const [details, setDetails] =
    useState<MonumentDetails | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [languageLoading, setLanguageLoading] =
    useState(false);

  const [activeTab, setActiveTab] =
    useState<ActiveTab>("camera");

  // ---------------------------------------------------------
  // GEMINI TTS STATE
  // ---------------------------------------------------------

  const [isSpeaking, setIsSpeaking] =
    useState(false);

  const [ttsLoading, setTtsLoading] =
    useState(false);

  const [activeVoiceName, setActiveVoiceName] =
    useState<string | null>(null);

  const audioRef =
    useRef<HTMLAudioElement | null>(null);

  const audioUrlRef =
    useRef<string | null>(null);

  // ---------------------------------------------------------
  // CLEAN UP AUDIO
  // ---------------------------------------------------------

  const cleanupAudio = useCallback(() => {
    const audio = audioRef.current;

    if (audio) {
      try {
        audio.pause();
        audio.currentTime = 0;
      } catch {
        // Ignore cleanup errors.
      }

      audio.onplay = null;
      audio.onended = null;
      audio.onerror = null;
    }

    audioRef.current = null;

    if (audioUrlRef.current) {
      URL.revokeObjectURL(
        audioUrlRef.current
      );

      audioUrlRef.current = null;
    }

    setIsSpeaking(false);
  }, []);

  // ---------------------------------------------------------
  // STOP GEMINI NARRATION
  // ---------------------------------------------------------

  const stopNarration = useCallback(() => {
    cleanupAudio();
    setTtsLoading(false);
  }, [cleanupAudio]);

  // ---------------------------------------------------------
  // CLEAN UP WHEN COMPONENT UNMOUNTS
  // ---------------------------------------------------------

  useEffect(() => {
    return () => {
      cleanupAudio();
    };
  }, [cleanupAudio]);

  // ---------------------------------------------------------
  // BASE64 → BLOB
  // ---------------------------------------------------------

  const base64ToBlob = (
    base64: string,
    mimeType: string
  ): Blob => {
    const binaryString =
      window.atob(base64);

    const length =
      binaryString.length;

    const bytes =
      new Uint8Array(length);

    for (let i = 0; i < length; i += 1) {
      bytes[i] =
        binaryString.charCodeAt(i);
    }

    return new Blob(
      [bytes],
      {
        type: mimeType,
      }
    );
  };

  // ---------------------------------------------------------
  // GEMINI TTS
  // ---------------------------------------------------------

  const speakText = useCallback(
    async (
      text: string,
      languageCode: string
    ) => {
      if (typeof window === "undefined") {
        return;
      }

      const cleanText =
        text
          ?.replace(/[\*#`_]/g, "")
          .replace(/\s+/g, " ")
          .trim();

      if (!cleanText) {
        console.warn(
          "TTS text is empty."
        );
        return;
      }

      // Stop any currently playing audio.
      cleanupAudio();

      setTtsLoading(true);
      setActiveVoiceName(
        "Gemini TTS · Kore"
      );

      try {
        console.log(
          "--------------------------------"
        );

        console.log(
          "Gemini TTS request"
        );

        console.log(
          "Language:",
          languageCode
        );

        console.log(
          "API:",
          `${API_BASE_URL}/api/tts`
        );

        console.log(
          "--------------------------------"
        );

        const response =
          await fetch(
            `${API_BASE_URL}/api/tts`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body: JSON.stringify({
                text: cleanText,
                language: languageCode,
              }),
            }
          );

        if (!response.ok) {
          let errorMessage =
            `TTS request failed (${response.status})`;

          try {
            const errorData =
              await response.json();

            if (errorData?.detail) {
              errorMessage =
                String(
                  errorData.detail
                );
            }
          } catch {
            const errorText =
              await response.text();

            if (errorText) {
              errorMessage =
                errorText;
            }
          }

          throw new Error(
            errorMessage
          );
        }

        const data =
          (await response.json()) as TTSResponse;

        console.log(
          "Gemini TTS response:",
          {
            success: data.success,
            language: data.language,
            language_code:
              data.language_code,
            mime_type:
              data.mime_type,
            sample_rate:
              data.sample_rate,
            has_audio:
              Boolean(
                data.audio_base64
              ),
          }
        );

        if (
          !data.audio_base64
        ) {
          throw new Error(
            "Backend returned no audio data."
          );
        }

        const mimeType =
          data.mime_type ||
          "audio/wav";

        const audioBlob =
          base64ToBlob(
            data.audio_base64,
            mimeType
          );

        const audioUrl =
          URL.createObjectURL(
            audioBlob
          );

        audioUrlRef.current =
          audioUrl;

        const audio =
          new Audio(audioUrl);

        audio.preload = "auto";

        audioRef.current =
          audio;

        audio.onplay = () => {
          setIsSpeaking(true);
          setTtsLoading(false);

          console.log(
            "Gemini TTS playback started."
          );
        };

        audio.onended = () => {
          setIsSpeaking(false);
          setTtsLoading(false);

          if (
            audioUrlRef.current ===
            audioUrl
          ) {
            URL.revokeObjectURL(
              audioUrl
            );

            audioUrlRef.current =
              null;
          }

          audioRef.current =
            null;

          console.log(
            "Gemini TTS playback completed."
          );
        };

        audio.onerror = () => {
          console.error(
            "HTML audio playback failed."
          );

          setIsSpeaking(false);
          setTtsLoading(false);

          if (
            audioUrlRef.current ===
            audioUrl
          ) {
            URL.revokeObjectURL(
              audioUrl
            );

            audioUrlRef.current =
              null;
          }

          audioRef.current =
            null;
        };

        try {
          await audio.play();
        } catch (playError) {
          console.warn(
            "Automatic audio playback was blocked:",
            playError
          );

          setIsSpeaking(false);
          setTtsLoading(false);

          /*
           * The browser may block automatic playback
           * after an asynchronous API request.
           *
           * The generated audio is still available
           * through the Listen button, which is a direct
           * user interaction.
           */
          throw new Error(
            "Audio was generated, but the browser blocked automatic playback. Press Listen to play it."
          );
        }
      } catch (error) {
        console.error(
          "Gemini TTS error:",
          error
        );

        setIsSpeaking(false);
        setTtsLoading(false);

        /*
         * Do not show an alert when the browser merely
         * blocks automatic playback. The narration itself
         * was successfully generated in that situation.
         */
        const message =
          String(error);

        if (
          !message.includes(
            "blocked automatic playback"
          )
        ) {
          alert(
            `Gemini TTS could not generate audio.\n\n${message}`
          );
        }
      }
    },
    [cleanupAudio]
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
        setLanguage(
          newLanguage
        );

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

        setActiveVoiceName(
          null
        );

        setActiveTab(
          "audio"
        );

      } catch (error) {
        console.error(
          "Language change error:",
          error
        );

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

    setActiveTab(
      "camera"
    );
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
                isSpeaking
                  ? "text-green-600"
                  : ttsLoading
                  ? "text-amber-500"
                  : "text-gray-400"
              }`}
            >

              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isSpeaking
                    ? "bg-green-500"
                    : ttsLoading
                    ? "bg-amber-400 animate-pulse"
                    : "bg-gray-300"
                }`}
              />

              {isSpeaking
                ? "Gemini Speaking"
                : ttsLoading
                ? "Generating Audio…"
                : "Gemini TTS Ready"}

            </span>

          </div>

        </div>
      </header>

      {/* MAIN */}

      <div className="max-w-md mx-auto px-4 pt-4 space-y-4">

        {/* LANGUAGE */}

        <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm">

          <LanguageSelector
            selectedLanguage={
              language
            }
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
              setActiveTab(
                "camera"
              )
            }
            className={`flex flex-col items-center py-2 px-1 rounded-xl transition-all ${
              activeTab ===
              "camera"
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
              setActiveTab(
                "audio"
              )
            }
            disabled={
              !monumentId
            }
            className={`flex flex-col items-center py-2 px-1 rounded-xl transition-all ${
              activeTab ===
              "audio"
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
              setActiveTab(
                "chat"
              )
            }
            disabled={
              !monumentId
            }
            className={`flex flex-col items-center py-2 px-1 rounded-xl transition-all ${
              activeTab ===
              "chat"
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
                            : ttsLoading
                            ? "bg-amber-100 text-amber-600 animate-pulse"
                            : "bg-gray-200 text-gray-600"
                        }`}
                      >
                        <Volume2 className="w-5 h-5" />
                      </div>

                      <div>

                        <h4 className="font-bold text-xs">
                          Gemini Audio Guide
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
                      onClick={() => {
                        if (
                          isSpeaking ||
                          ttsLoading
                        ) {
                          stopNarration();
                        } else {
                          void speakText(
                            narration,
                            language
                          );
                        }
                      }}
                      disabled={
                        languageLoading
                      }
                      className={`py-2 px-4 font-bold text-xs rounded-lg transition-all ${
                        isSpeaking
                          ? "bg-gray-800 text-white hover:bg-gray-900"
                          : ttsLoading
                          ? "bg-amber-500 text-white cursor-wait"
                          : "bg-rose-500 text-white hover:bg-rose-600 shadow-md shadow-rose-100"
                      }`}
                    >
                      {isSpeaking
                        ? "⏹ Stop"
                        : ttsLoading
                        ? "⏳ Generating"
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
