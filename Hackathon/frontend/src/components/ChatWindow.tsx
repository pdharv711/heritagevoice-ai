"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Send,
  Volume2,
  VolumeX,
  Mic,
  MicOff,
  User,
  MessageSquare,
} from "lucide-react";
import { getBcp47 } from "@/components/LanguageSelector";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://heritagevoice-ai.onrender.com";

export interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatWindowProps {
  monumentId: string;
  monumentName: string;
  monumentDetails?: any;
  language: string;
}

const GREETINGS: Record<string, string> = {
  English:
    "Hi! Ask me anything about this monument, including its history, architecture, construction, or cultural importance.",

  Hindi:
    "नमस्ते! आप इस स्मारक के इतिहास, वास्तुकला, निर्माण या सांस्कृतिक महत्व के बारे में कुछ भी पूछ सकते हैं।",

  Gujarati:
    "નમસ્તે! તમે આ સ્મારકના ઇતિહાસ, સ્થાપત્ય, બાંધકામ અથવા સાંસ્કૃતિક મહત્વ વિશે કંઈપણ પૂછી શકો છો.",

  Tamil:
    "வணக்கம்! இந்த நினைவுச்சின்னத்தின் வரலாறு, கட்டிடக்கலை, கட்டுமானம் அல்லது கலாச்சார முக்கியத்துவம் பற்றி கேட்கலாம்.",

  Telugu:
    "నమస్కారం! ఈ స్మారక చిహ్నం చరిత్ర, నిర్మాణ శైలి, నిర్మాణం లేదా సాంస్కృతిక ప్రాముఖ్యత గురించి అడగవచ్చు.",

  Bengali:
    "নমস্কার! এই স্মৃতিস্তম্ভের ইতিহাস, স্থাপত্য, নির্মাণ বা সাংস্কৃতিক গুরুত্ব সম্পর্কে যেকোনো প্রশ্ন করতে পারেন।",

  Marathi:
    "नमस्कार! या स्मारकाचा इतिहास, वास्तुकला, बांधकाम किंवा सांस्कृतिक महत्त्व याबद्दल काहीही विचारू शकता.",

  Kannada:
    "ನಮಸ್ಕಾರ! ಈ ಸ್ಮಾರಕದ ಇತಿಹಾಸ, ವಾಸ್ತುಶಿಲ್ಪ, ನಿರ್ಮಾಣ ಅಥವಾ ಸಾಂಸ್ಕೃತಿಕ ಮಹತ್ವದ ಬಗ್ಗೆ ಕೇಳಬಹುದು.",

  Punjabi:
    "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਤੁਸੀਂ ਇਸ ਸਮਾਰਕ ਦੇ ਇਤਿਹਾਸ, ਵਾਸਤੂਕਲਾ, ਨਿਰਮਾਣ ਜਾਂ ਸੱਭਿਆਚਾਰਕ ਮਹੱਤਵ ਬਾਰੇ ਕੁਝ ਵੀ ਪੁੱਛ ਸਕਦੇ ਹੋ.",

  French:
    "Bonjour ! Posez-moi vos questions sur l’histoire, l’architecture, la construction ou l’importance culturelle de ce monument.",

  Spanish:
    "¡Hola! Puedes preguntarme sobre la historia, arquitectura, construcción o importancia cultural de este monumento.",

  German:
    "Hallo! Fragen Sie mich gern nach der Geschichte, Architektur, Bauweise oder kulturellen Bedeutung dieses Denkmals.",

  Arabic:
    "مرحباً! يمكنك أن تسألني عن تاريخ هذا المعلم أو عمارته أو بنائه أو أهميته الثقافية.",

  Japanese:
    "こんにちは！この記念碑の歴史、建築、建設、文化的な重要性について何でも質問してください。",

  Korean:
    "안녕하세요! 이 기념물의 역사, 건축, 건설 또는 문화적 중요성에 대해 무엇이든 질문해 주세요.",

  Portuguese:
    "Olá! Pergunte sobre a história, arquitetura, construção ou importância cultural deste monumento.",

  Russian:
    "Здравствуйте! Вы можете спросить об истории, архитектуре, строительстве или культурном значении этого памятника.",

  Italian:
    "Ciao! Puoi chiedermi della storia, dell’architettura, della costruzione o dell’importanza culturale di questo monumento.",
};

export default function ChatWindow({
  monumentId,
  monumentName,
  monumentDetails,
  language,
}: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: GREETINGS[language] || GREETINGS.English,
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

  /* ----------------------------------------
     SPEECH INITIALIZATION
  ---------------------------------------- */

  useEffect(() => {
    if (typeof window === "undefined") return;

    if ("speechSynthesis" in window) {
      synthRef.current = window.speechSynthesis;
      setSpeechSupported(true);
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();

      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = getBcp47(language);

      recognition.onresult = (event: any) => {
        const transcript =
          event.results?.[0]?.[0]?.transcript || "";

        setInputText(transcript);
        setIsListening(false);
      };

      recognition.onerror = (event: any) => {
        console.warn("Speech recognition error:", event);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }

    return () => {
      synthRef.current?.cancel();
      recognitionRef.current?.stop();
    };
  }, [language]);

  /* ----------------------------------------
     UPDATE GREETING WHEN LANGUAGE CHANGES
  ---------------------------------------- */

  useEffect(() => {
    setMessages([
      {
        role: "assistant",
        content: GREETINGS[language] || GREETINGS.English,
      },
    ]);

    setInputText("");
    stopSpeaking();
  }, [language]);

  /* ----------------------------------------
     AUTO SCROLL
  ---------------------------------------- */

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  /* ----------------------------------------
     STOP SPEAKING
  ---------------------------------------- */

  const stopSpeaking = () => {
    synthRef.current?.cancel();
    setIsSpeaking(false);
  };

  /* ----------------------------------------
     TEXT TO SPEECH
  ---------------------------------------- */

  const speakText = (text: string) => {
    if (!synthRef.current || !text) return;

    stopSpeaking();

    const cleanText = text
      .replace(/[*#`_]/g, "")
      .replace(/\s+/g, " ")
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanText);

    utteranceRef.current = utterance;

    const bcp47 = getBcp47(language);

    const voices = synthRef.current.getVoices();

    /*
      First try exact language.
      Example:
      Gujarati -> gu-IN
      Hindi -> hi-IN
      English -> en-IN
    */

    let voice = voices.find(
      (item) =>
        item.lang.toLowerCase() === bcp47.toLowerCase()
    );

    /*
      Then try language family.
    */

    if (!voice) {
      const languageCode = bcp47
        .split("-")[0]
        .toLowerCase();

      voice = voices.find((item) =>
        item.lang
          .toLowerCase()
          .startsWith(languageCode)
      );
    }

    /*
      Use selected language even if
      a specific voice is unavailable.
    */

    utterance.lang = voice?.lang || bcp47;

    if (voice) {
      utterance.voice = voice;
    }

    utterance.rate = 0.92;
    utterance.pitch = 1;

    utterance.onstart = () => {
      setIsSpeaking(true);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
    };

    synthRef.current.speak(utterance);
  };

  /* ----------------------------------------
     MICROPHONE
  ---------------------------------------- */

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert(
        "Speech recognition is not supported in this browser. Please use Google Chrome."
      );
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
      return;
    }

    stopSpeaking();

    /*
      IMPORTANT:
      Microphone uses the currently
      selected language.
    */

    recognitionRef.current.lang = getBcp47(language);

    setIsListening(true);

    try {
      recognitionRef.current.start();
    } catch (error) {
      console.warn(
        "Speech recognition could not start:",
        error
      );

      setIsListening(false);
    }
  };

  /* ----------------------------------------
     SEND MESSAGE
  ---------------------------------------- */

  const handleSendMessage = async (
    event: React.FormEvent
  ) => {
    event.preventDefault();

    const text = inputText.trim();

    if (!text || isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: text,
    };

    /*
      Convert chat history into backend format.
    */

    const apiHistory = messages.map((message) => ({
      role:
        message.role === "assistant"
          ? "model"
          : "user",
      content: message.content,
    }));

    setMessages((previous) => [
      ...previous,
      userMessage,
    ]);

    setInputText("");
    setIsLoading(true);

    stopSpeaking();

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/chat`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            monument_id: monumentId,

            monument_name: monumentName,

            monument_details:
              monumentDetails || null,

            question: text,

            /*
              THIS IS VERY IMPORTANT.
              Backend must use this language.
            */

            language: language,

            history: apiHistory,
          }),
        }
      );

      if (!response.ok) {
        const errorText = await response.text();

        throw new Error(
          `Chat backend error ${response.status}: ${errorText}`
        );
      }

      const data = await response.json();

      const reply =
        data.reply ||
        "I could not generate an answer right now.";

      const assistantMessage: Message = {
        role: "assistant",
        content: reply,
      };

      setMessages((previous) => [
        ...previous,
        assistantMessage,
      ]);

      /*
        Automatically speak the answer
        in the selected language.
      */

      setTimeout(() => {
        speakText(reply);
      }, 150);
    } catch (error) {
      console.error("Chat error:", error);

      const errorMessage =
        language === "Gujarati"
          ? "માફ કરશો, હાલમાં AI માર્ગદર્શક સાથે જોડાવામાં સમસ્યા આવી."
          : language === "Hindi"
          ? "क्षमा करें, अभी AI गाइड से जुड़ने में समस्या हुई।"
          : language === "Tamil"
          ? "மன்னிக்கவும், தற்போது AI வழிகாட்டியுடன் இணைப்பதில் சிக்கல் ஏற்பட்டுள்ளது."
          : language === "Telugu"
          ? "క్షమించండి, ప్రస్తుతం AI గైడ్‌తో కనెక్ట్ కావడంలో సమస్య ఏర్పడింది."
          : language === "Bengali"
          ? "দুঃখিত, এই মুহূর্তে AI গাইডের সাথে সংযোগ করতে সমস্যা হচ্ছে।"
          : "Sorry, I could not connect to the AI guide right now.";

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: errorMessage,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  /* ----------------------------------------
     UI
  ---------------------------------------- */

  return (
    <div className="flex flex-col bg-white border border-gray-200 rounded-2xl shadow-sm h-[450px] w-full overflow-hidden">

      {/* HEADER */}

      <div className="bg-gradient-to-r from-rose-500 to-pink-600 px-4 py-3 flex justify-between items-center text-white shrink-0">

        <div className="flex items-center space-x-2">

          <MessageSquare className="w-5 h-5 text-pink-100" />

          <div>
            <h3 className="font-bold text-sm leading-tight">
              HeritageVoice Assistant
            </h3>

            <p className="text-xs text-pink-100/90 font-medium">
              {monumentName} • {language}
            </p>
          </div>

        </div>

        {speechSupported && isSpeaking && (
          <button
            onClick={stopSpeaking}
            className="p-1.5 bg-white/10 hover:bg-white/20 rounded-lg"
            title="Stop audio"
          >
            <VolumeX className="w-4 h-4 text-white" />
          </button>
        )}

      </div>

      {/* MESSAGES */}

      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/50">

        {messages.map((message, index) => (

          <div
            key={index}
            className={`flex items-start gap-2.5 max-w-[85%] ${
              message.role === "user"
                ? "ml-auto flex-row-reverse"
                : "mr-auto"
            }`}
          >

            {/* AVATAR */}

            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-white ${
                message.role === "user"
                  ? "bg-rose-500"
                  : "bg-gradient-to-tr from-indigo-500 to-purple-600"
              }`}
            >
              {message.role === "user" ? (
                <User className="w-4 h-4" />
              ) : (
                <Volume2 className="w-4 h-4" />
              )}
            </div>

            {/* MESSAGE */}

            <div
              className={`p-3 rounded-2xl relative shadow-sm ${
                message.role === "user"
                  ? "bg-rose-500 text-white rounded-tr-none"
                  : "bg-white text-gray-800 rounded-tl-none border border-slate-100"
              }`}
            >

              <p className="text-sm font-medium leading-relaxed whitespace-pre-wrap pr-5">
                {message.content}
              </p>

              {/* SPEAKER BUTTON */}

              {message.role === "assistant" &&
                speechSupported && (
                  <button
                    onClick={() =>
                      speakText(message.content)
                    }
                    className="absolute right-2 bottom-1.5 text-gray-400 hover:text-rose-500 p-0.5 rounded"
                    title="Listen"
                  >
                    <Volume2 className="w-3.5 h-3.5" />
                  </button>
                )}

            </div>

          </div>

        ))}

        {/* LOADING */}

        {isLoading && (

          <div className="flex items-center space-x-2 mr-auto max-w-[80%]">

            <div className="w-7 h-7 rounded-full bg-indigo-500 flex items-center justify-center text-white shrink-0">
              <MessageSquare className="w-4 h-4 animate-bounce" />
            </div>

            <div className="bg-white border border-slate-100 p-3 rounded-2xl rounded-tl-none flex items-center space-x-1.5 shadow-sm">

              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />

              <div
                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                style={{
                  animationDelay: "150ms",
                }}
              />

              <div
                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                style={{
                  animationDelay: "300ms",
                }}
              />

            </div>

          </div>

        )}

        <div ref={messagesEndRef} />

      </div>

      {/* INPUT */}

      <form
        onSubmit={handleSendMessage}
        className="p-3 bg-white border-t border-gray-100 flex items-center gap-2 shrink-0"
      >

        {/* MICROPHONE */}

        <button
          type="button"
          onClick={toggleListening}
          className={`p-3 rounded-xl border flex items-center justify-center transition-all ${
            isListening
              ? "bg-red-500 text-white border-red-500 animate-pulse"
              : "bg-gray-50 hover:bg-gray-100 text-gray-500 border-gray-200"
          }`}
          title={
            isListening
              ? "Listening..."
              : "Speak question"
          }
        >

          {isListening ? (
            <MicOff className="w-4 h-4" />
          ) : (
            <Mic className="w-4 h-4" />
          )}

        </button>

        {/* TEXT INPUT */}

        <input
          type="text"
          value={inputText}
          onChange={(event) =>
            setInputText(event.target.value)
          }
          placeholder={
            isListening
              ? `Listening in ${language}...`
              : `Ask about ${monumentName}...`
          }
          disabled={isLoading || isListening}
          className="flex-1 bg-gray-50 border border-gray-200 text-gray-800 text-sm py-3 px-4 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500 transition-all"
        />

        {/* SEND */}

        <button
          type="submit"
          disabled={
            !inputText.trim() || isLoading
          }
          className="p-3 bg-rose-500 hover:bg-rose-600 disabled:bg-gray-100 disabled:text-gray-400 text-white rounded-xl shadow-sm transition-all"
          title="Send message"
        >
          <Send className="w-4 h-4" />
        </button>

      </form>
    </div>
  );
}
