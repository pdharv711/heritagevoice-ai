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
  process.env.NEXT_PUBLIC_API_URL || "https://heritagevoice-ai.onrender.com";

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

  useEffect(() => {
    if (typeof window === "undefined") return;

    const synth = window.speechSynthesis;
    synthRef.current = synth;

    const markReady = () => setVoicesReady(true);

    if (synth.getVoices().length > 0) {
      setVoicesReady(true);
    }

    synth.addEventListener("voiceschanged", markReady);

    return () => {
      synth.removeEventListener("voiceschanged", markReady);
      synth.cancel();
    };
  }, []);

  const stopNarration = useCallback(() => {
    synthRef.current?.cancel();
    setIsSpeaking(false);
  }, []);

  const pickVoice = useCallback((bcp47: string) => {
    if (!synthRef.current) return null;

    const voices = synthRef.current.getVoices();
    const exact = voices.find(
      (voice) => voice.lang.toLowerCase() === bcp47.toLowerCase()
    );
    if (exact) return exact;

    const prefix = bcp47.split("-")[0].toLowerCase();

    return (
      voices.find((voice) =>
        voice.lang.toLowerCase().startsWith(prefix)
      ) ||
      voices.find((voice) =>
        voice.lang.toLowerCase().includes(prefix)
      ) ||
      null
    );
  }, []);

  const speakText = useCallback(
    (text: string, languageCode: string) => {
      if (!synthRef.current || !text) return;

      stopNarration();

      const utterance = new SpeechSynthesisUtterance(
        text.replace(/[*#`_]/g, "")
      );
      utteranceRef.current = utterance;

      const bcp47 = getBcp47(languageCode);
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
      utterance.pitch = 1;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      synthRef.current.speak(utterance);
    },
    [pickVoice, stopNarration]
  );

  const handleLanguageChange = async (newLanguage: string) => {
    if (newLanguage === language) return;

    stopNarration();

    // No monument yet: simply change the selected guide language.
    if (!monumentId || !monumentName || !details) {
      setLanguage(newLanguage);
      return;
    }

    setLanguageLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/narrate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
      }, 150);
    } catch (error) {
      console.error("Language change error:", error);

      // Keep the current narration instead of destroying a working result.
      setLanguage(newLanguage);

      alert(
        "The language changed, but the new narration could not be generated. Please try the language again."
      );
    } finally {
      setLanguageLoading(false);
    }
  };

  const handleImageCapture = async (base64Image: string) => {
    setLoading(true);
    stopNarration();

    try {
      const response = await fetch(`${API_BASE_URL}/api/identify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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

      const autoPlay = () => speakText(data.narration, language);

      if (voicesReady) {
        setTimeout(autoPlay, 150);
      } else {
        const synth = synthRef.current;

        if (synth) {
          const onReady = () => {
            setVoicesReady(true);
            setTimeout(autoPlay, 150);
            synth.removeEventListener("voiceschanged", onReady);
          };

          synth.addEventListener("voiceschanged", onReady);

          setTimeout(() => {
            synth.removeEventListener("voiceschanged", onReady);
            autoPlay();
          }, 3000);
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

  const resetApp = () => {
    stopNarration();
    setMonumentId(null);
    setMonumentName(null);
    setNarration(null);
    setDetails(null);
    setActiveVoiceName(null);
    setActiveTab("camera");
  };

