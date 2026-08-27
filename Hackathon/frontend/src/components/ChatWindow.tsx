"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Volume2, VolumeX, Mic, MicOff, User, MessageSquare } from "lucide-react";

export interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatWindowProps {
  monumentId: string;
  monumentName: string;
  language: string;
}

export default function ChatWindow({ monumentId, monumentName, language }: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: `Hi there! I am your AI tour guide for ${monumentName}. Feel free to ask me any questions about its history, construction, architecture, or who built it!`,
    },
  ]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const synthRef = useRef<SpeechSynthesis | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const recognitionRef = useRef<any>(null);

  // Initialize Speech Synthesis and Recognition
  useEffect(() => {
    if (typeof window !== "undefined") {
      synthRef.current = window.speechSynthesis;
      setSpeechSupported(true);

      // Setup Browser Speech Recognition
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const rec = new SpeechRecognition();
        rec.continuous = false;
        rec.interimResults = false;

        // Map languages to BCP-47 codes
        const langCodes: Record<string, string> = {
          English: "en-US",
          Hindi: "hi-IN",
          Tamil: "ta-IN",
          Telugu: "te-IN",
          Bengali: "bn-IN",
          Marathi: "mr-IN",
          Gujarati: "gu-IN",
          Kannada: "kn-IN",
          French: "fr-FR",
          Spanish: "es-ES",
        };
        rec.lang = langCodes[language] || "en-US";

        rec.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          setInputText(transcript);
          setIsListening(false);
        };

        rec.onerror = (err: any) => {
          console.error("Speech Recognition Error:", err);
          setIsListening(false);
        };

        rec.onend = () => {
          setIsListening(false);
        };

        recognitionRef.current = rec;
      }
    }

    return () => {
      stopSpeaking();
    };
  }, [language]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Handle SpeechSynthesis audio playback
  const speakText = (text: string) => {
    if (!synthRef.current) return;

    stopSpeaking();

    // Clean markdown bold or list markers from text
    const cleanText = text.replace(/[*#`_\-]/g, "");

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utteranceRef.current = utterance;

    // Set voice based on selected language
    const voices = synthRef.current.getVoices();
    const langCodes: Record<string, string> = {
      English: "en",
      Hindi: "hi",
      Tamil: "ta",
      Telugu: "te",
      Bengali: "bn",
      Marathi: "mr",
      Gujarati: "gu",
      Kannada: "kn",
      French: "fr",
      Spanish: "es",
    };
    
    const targetLangCode = langCodes[language] || "en";
    const voice = voices.find(v => v.lang.startsWith(targetLangCode));
    if (voice) {
      utterance.voice = voice;
    }
    
    utterance.lang = targetLangCode;
    utterance.rate = 1.0;

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    synthRef.current.speak(utterance);
  };

  const stopSpeaking = () => {
    if (synthRef.current) {
      synthRef.current.cancel();
    }
    setIsSpeaking(false);
  };

  // Toggle voice recording
  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser. Please try Google Chrome.");
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      stopSpeaking();
      setIsListening(true);
      recognitionRef.current.start();
    }
  };

  // Send message to FastAPI chat endpoint
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text || isLoading) return;

    // Append user message
    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInputText("");
    setIsLoading(true);
    stopSpeaking();

    try {
      // Map frontend context to API format
      const apiHistory = messages.map((m) => ({
        role: m.role === "assistant" ? "model" : "user",
        content: m.content,
      }));

      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          monument_id: monumentId,
          question: text,
          language: language,
          history: apiHistory,
        }),
      });

      if (!res.ok) throw new Error("Failed to get response from guide.");
      const data = await res.json();

      const assistantMsg: Message = { role: "assistant", content: data.reply };
      setMessages((prev) => [...prev, assistantMsg]);

      // Automatically speak the response
      speakText(data.reply);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I ran into an error connecting to my database. Please try again.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col bg-white border border-gray-200 rounded-2xl shadow-sm h-[450px] w-full overflow-hidden">
      {/* Header Info */}
      <div className="bg-gradient-to-r from-rose-500 to-pink-600 px-4 py-3 flex justify-between items-center text-white shrink-0">
        <div className="flex items-center space-x-2">
          <MessageSquare className="w-5 h-5 text-pink-100" />
          <div>
            <h3 className="font-bold text-sm leading-tight">HeritageVoice Assistant</h3>
            <p className="text-xs text-pink-100/90 font-medium">Q&A: {monumentName}</p>
          </div>
        </div>
        {speechSupported && isSpeaking && (
          <button
            onClick={stopSpeaking}
            className="p-1.5 bg-white/10 hover:bg-white/20 rounded-lg transition-colors"
            title="Stop playing audio"
          >
            <VolumeX className="w-4 h-4 text-white" />
          </button>
        )}
      </div>

      {/* Messages Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/50">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex items-start gap-2.5 max-w-[85%] ${
              msg.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
            }`}
          >
            {/* Avatar */}
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-white ${
                msg.role === "user" ? "bg-rose-500" : "bg-gradient-to-tr from-indigo-500 to-purple-600"
              }`}
            >
              {msg.role === "user" ? <User className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </div>

            {/* Bubble */}
            <div
              className={`p-3 rounded-2xl relative shadow-sm ${
                msg.role === "user"
                  ? "bg-rose-500 text-white rounded-tr-none"
                  : "bg-white text-gray-800 rounded-tl-none border border-slate-100"
              }`}
            >
              <p className="text-sm font-medium leading-relaxed whitespace-pre-wrap">{msg.content}</p>

              {/* TTS Read Aloud Icon (Assistant side) */}
              {msg.role === "assistant" && speechSupported && (
                <button
                  onClick={() => speakText(msg.content)}
                  className="absolute right-2 bottom-1.5 text-gray-400 hover:text-rose-500 p-0.5 rounded transition-colors"
                  title="Listen to this narration"
                >
                  <Volume2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center space-x-2 mr-auto max-w-[80%]">
            <div className="w-7 h-7 rounded-full bg-indigo-500 flex items-center justify-center text-white shrink-0">
              <MessageSquare className="w-4 h-4 animate-bounce" />
            </div>
            <div className="bg-white border border-slate-100 p-3 rounded-2xl rounded-tl-none flex items-center space-x-1.5 shadow-sm">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <form onSubmit={handleSendMessage} className="p-3 bg-white border-t border-gray-100 flex items-center gap-2 shrink-0">
        {/* Speak Input Button */}
        <button
          type="button"
          onClick={toggleListening}
          className={`p-3 rounded-xl border flex items-center justify-center transition-all ${
            isListening
              ? "bg-red-500 text-white border-red-500 animate-pulse"
              : "bg-gray-50 hover:bg-gray-100 text-gray-500 border-gray-200"
          }`}
          title={isListening ? "Listening..." : "Speak question"}
        >
          {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
        </button>

        {/* Text Input */}
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={isListening ? "Listening..." : `Ask about ${monumentName}...`}
          disabled={isLoading || isListening}
          className="flex-1 bg-gray-50 border border-gray-200 text-gray-800 text-sm py-3 px-4 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500 transition-all"
        />

        {/* Send Button */}
        <button
          type="submit"
          disabled={!inputText.trim() || isLoading}
          className="p-3 bg-rose-500 hover:bg-rose-600 disabled:bg-gray-100 disabled:text-gray-400 text-white rounded-xl shadow-sm transition-all transform active:scale-95"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
