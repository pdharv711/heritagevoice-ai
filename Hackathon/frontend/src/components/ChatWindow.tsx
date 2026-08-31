"use client";

import React, {
  useState,
  useRef,
  useEffect,
} from "react";

import {
  Send,
  Volume2,
  VolumeX,
  Mic,
  MicOff,
  User,
  MessageSquare,
} from "lucide-react";


// =============================================================================
// TYPES
// =============================================================================

export interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatWindowProps {
  monumentId: string;
  monumentName: string;
  language: string;

  // Details returned by /api/identify.
  // This is important for monuments that are NOT
  // present in database.py.
  monumentDetails?: Record<string, any> | null;
}


// =============================================================================
// API
// =============================================================================

const API_BASE_URL =
  "https://heritagevoice-ai.onrender.com";


// =============================================================================
// LANGUAGE → BCP47
// =============================================================================

const LANGUAGE_CODES: Record<string, string> = {
  English: "en-US",

  Hindi: "hi-IN",

  Tamil: "ta-IN",

  Telugu: "te-IN",

  Bengali: "bn-IN",

  Marathi: "mr-IN",

  Gujarati: "gu-IN",

  Kannada: "kn-IN",

  Punjabi: "pa-IN",

  French: "fr-FR",

  Spanish: "es-ES",

  German: "de-DE",

  Arabic: "ar-SA",

  Japanese: "ja-JP",

  Korean: "ko-KR",

  Portuguese: "pt-BR",

  Russian: "ru-RU",

  Italian: "it-IT",
};


// =============================================================================
// COMPONENT
// =============================================================================

export default function ChatWindow({
  monumentId,
  monumentName,
  language,
  monumentDetails,
}: ChatWindowProps) {


  // ===========================================================================
  // STATE
  // ===========================================================================

  const [messages, setMessages] =
    useState<Message[]>([
      {
        role: "assistant",

        content:
          `Hello! I am your HeritageVoice AI tour guide for ${monumentName}. ` +
          `Ask me anything about its history, architecture, construction, ` +
          `culture, or interesting facts.`,
      },
    ]);


  const [inputText, setInputText] =
    useState("");


  const [isLoading, setIsLoading] =
    useState(false);


  const [isSpeaking, setIsSpeaking] =
    useState(false);


  const [isListening, setIsListening] =
    useState(false);


  const [speechSupported, setSpeechSupported] =
    useState(false);


  // ===========================================================================
  // REFS
  // ===========================================================================

  const messagesEndRef =
    useRef<HTMLDivElement | null>(null);


  const synthRef =
    useRef<SpeechSynthesis | null>(null);


  const utteranceRef =
    useRef<SpeechSynthesisUtterance | null>(null);


  const recognitionRef =
    useRef<any>(null);


  // ===========================================================================
  // LANGUAGE CODE
  // ===========================================================================

  const getLanguageCode = () => {

    return (
      LANGUAGE_CODES[language] ||
      "en-US"
    );
  };


  // ===========================================================================
  // INITIALIZE SPEECH
  // ===========================================================================

  useEffect(() => {

    if (typeof window === "undefined") {
      return;
    }


    // -------------------------------------------------------------------------
    // TEXT TO SPEECH
    // -------------------------------------------------------------------------

    if (
      "speechSynthesis" in window
    ) {

      synthRef.current =
        window.speechSynthesis;

      setSpeechSupported(true);
    }


    // -------------------------------------------------------------------------
    // SPEECH RECOGNITION
    // -------------------------------------------------------------------------

    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;


    if (!SpeechRecognition) {
      return;
    }


    const recognition =
      new SpeechRecognition();


    recognition.continuous = false;

    recognition.interimResults = false;

    recognition.lang =
      getLanguageCode();


    recognition.onstart = () => {

      setIsListening(true);
    };


    recognition.onresult = (
      event: any
    ) => {

      const transcript =
        event.results?.[0]?.[0]?.transcript ||
        "";


      setInputText(
        transcript
      );


      setIsListening(false);
    };


    recognition.onerror = (
      event: any
    ) => {

      console.error(
        "Speech recognition error:",
        event
      );


      setIsListening(false);
    };


    recognition.onend = () => {

      setIsListening(false);
    };


    recognitionRef.current =
      recognition;


    return () => {

      try {
        recognition.stop();
      } catch {}

    };

  }, [language]);


  // ===========================================================================
  // UPDATE SPEECH RECOGNITION LANGUAGE
  // ===========================================================================

  useEffect(() => {

    if (
      recognitionRef.current
    ) {

      recognitionRef.current.lang =
        getLanguageCode();
    }

  }, [language]);


  // ===========================================================================
  // SCROLL TO BOTTOM
  // ===========================================================================

  useEffect(() => {

    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });

  }, [
    messages,
    isLoading,
  ]);


  // ===========================================================================
  // STOP SPEAKING
  // ===========================================================================

  const stopSpeaking = () => {

    if (
      synthRef.current
    ) {

      synthRef.current.cancel();
    }


    setIsSpeaking(false);
  };


  // ===========================================================================
  // FIND BEST VOICE
  // ===========================================================================

  const findVoice = (
    languageCode: string
  ): SpeechSynthesisVoice | null => {

    if (!synthRef.current) {
      return null;
    }


    const voices =
      synthRef.current.getVoices();


    if (!voices.length) {
      return null;
    }


    const target =
      languageCode.toLowerCase();


    const languagePrefix =
      target
        .split("-")[0]
        .toLowerCase();


    // Exact match.
    const exact =
      voices.find(
        (voice) =>
          voice.lang.toLowerCase() ===
          target
      );


    if (exact) {
      return exact;
    }


    // Prefix match.
    const prefix =
      voices.find(
        (voice) =>
          voice.lang
            .toLowerCase()
            .startsWith(
              languagePrefix
            )
      );


    return prefix || null;
  };


  // ===========================================================================
  // SPEAK TEXT
  // ===========================================================================

  const speakText = (
    text: string
  ) => {

    if (
      !synthRef.current
    ) {

      console.warn(
        "Speech synthesis is not supported."
      );

      return;
    }


    stopSpeaking();


    const cleanText =
      text
        .replace(/[*#`_]/g, "")
        .replace(/\s+/g, " ")
        .trim();


    if (!cleanText) {
      return;
    }


    const utterance =
      new SpeechSynthesisUtterance(
        cleanText
      );


    utteranceRef.current =
      utterance;


    const languageCode =
      getLanguageCode();


    const voice =
      findVoice(
        languageCode
      );


    if (voice) {

      utterance.voice =
        voice;
    }


    utterance.lang =
      languageCode;


    utterance.rate =
      1.0;


    utterance.pitch =
      1.0;


    utterance.volume =
      1.0;


    utterance.onstart = () => {

      setIsSpeaking(true);
    };


    utterance.onend = () => {

      setIsSpeaking(false);
    };


    utterance.onerror = (
      event
    ) => {

      console.error(
        "Speech synthesis error:",
        event
      );

      setIsSpeaking(false);
    };


    synthRef.current.speak(
      utterance
    );
  };


  // ===========================================================================
  // TOGGLE MICROPHONE
  // ===========================================================================

  const toggleListening = () => {

    if (
      !recognitionRef.current
    ) {

      alert(
        "Speech recognition is not supported in this browser. Please use Google Chrome."
      );

      return;
    }


    if (isListening) {

      try {

        recognitionRef.current.stop();

      } catch {}

      setIsListening(false);

      return;
    }


    // Stop current narration.
    stopSpeaking();


    // Set selected language.
    recognitionRef.current.lang =
      getLanguageCode();


    try {

      recognitionRef.current.start();

    } catch (error) {

      console.error(
        "Could not start microphone:",
        error
      );

      setIsListening(false);
    }
  };


  // ===========================================================================
  // SEND MESSAGE
  // ===========================================================================

  const handleSendMessage = async (
    event: React.FormEvent
  ) => {

    event.preventDefault();


    const question =
      inputText.trim();


    if (
      !question ||
      isLoading
    ) {

      return;
    }


    // -------------------------------------------------------------------------
    // USER MESSAGE
    // -------------------------------------------------------------------------

    const userMessage: Message = {
      role: "user",
      content: question,
    };


    const previousMessages =
      messages;


    setMessages(
      (current) => [
        ...current,
        userMessage,
      ]
    );


    setInputText("");

    setIsLoading(true);

    stopSpeaking();


    try {

      // -----------------------------------------------------------------------
      // CONVERSATION HISTORY
      // -----------------------------------------------------------------------

      const history =
        previousMessages
          .slice(-6)
          .map(
            (message) => ({
              role:
                message.role ===
                "assistant"
                  ? "model"
                  : "user",

              content:
                message.content,
            })
          );


      // -----------------------------------------------------------------------
      // API REQUEST
      // -----------------------------------------------------------------------

      const response =
        await fetch(
          `${API_BASE_URL}/api/chat`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({

              monument_id:
                monumentId,

              question:
                question,

              language:
                language,

              history:
                history,

              // VERY IMPORTANT:
              // This allows the backend to answer
              // questions about dynamic monuments
              // which are not in database.py.
              monument_details:
                monumentDetails || null,
            }),
          }
        );


      // -----------------------------------------------------------------------
      // HTTP ERROR
      // -----------------------------------------------------------------------

      if (!response.ok) {

        let errorMessage =
          "Unable to contact the AI guide.";


        try {

          const errorData =
            await response.json();


          if (
            errorData?.detail
          ) {

            errorMessage =
              errorData.detail;
          }

        } catch {}


        throw new Error(
          errorMessage
        );
      }


      // -----------------------------------------------------------------------
      // RESPONSE
      // -----------------------------------------------------------------------

      const data =
        await response.json();


      const answer =
        data?.reply ||
        "Sorry, I could not generate an answer.";


      const assistantMessage:
        Message = {

        role:
          "assistant",

        content:
          answer,
      };


      setMessages(
        (current) => [
          ...current,
          assistantMessage,
        ]
      );


      // -----------------------------------------------------------------------
      // SPEAK RESPONSE
      // -----------------------------------------------------------------------

      speakText(
        answer
      );


    } catch (error) {

      console.error(
        "Chat request failed:",
        error
      );


      setMessages(
        (current) => [
          ...current,

          {
            role: "assistant",

            content:
              "Sorry, I could not connect to the AI guide. Please check your internet connection and try again.",
          },
        ]
      );


    } finally {

      setIsLoading(false);
    }
  };


  // ===========================================================================
  // UI
  // ===========================================================================

  return (

    <div
      className="
        flex
        flex-col
        bg-white
        border
        border-gray-200
        rounded-2xl
        shadow-sm
        h-[450px]
        w-full
        overflow-hidden
      "
    >

      {/* =====================================================================
          HEADER
      ====================================================================== */}

      <div
        className="
          bg-gradient-to-r
          from-rose-500
          to-pink-600
          px-4
          py-3
          flex
          justify-between
          items-center
          text-white
          shrink-0
        "
      >

        <div
          className="
            flex
            items-center
            space-x-2
          "
        >

          <MessageSquare
            className="
              w-5
              h-5
              text-pink-100
            "
          />


          <div>

            <h3
              className="
                font-bold
                text-sm
                leading-tight
              "
            >
              HeritageVoice Assistant
            </h3>


            <p
              className="
                text-xs
                text-pink-100
                font-medium
              "
            >
              Q&amp;A: {monumentName}
            </p>

          </div>

        </div>


        {/* STOP SPEAKING */}

        {speechSupported &&
          isSpeaking && (

            <button
              type="button"

              onClick={
                stopSpeaking
              }

              className="
                p-1.5
                bg-white/10
                hover:bg-white/20
                rounded-lg
                transition-colors
              "

              title="Stop audio"
            >

              <VolumeX
                className="
                  w-4
                  h-4
                  text-white
                "
              />

            </button>
          )}

      </div>


      {/* =====================================================================
          MESSAGES
      ====================================================================== */}

      <div
        className="
          flex-1
          overflow-y-auto
          p-4
          space-y-4
          bg-slate-50/50
        "
      >

        {messages.map(
          (message, index) => (

            <div
              key={index}

              className={`
                flex
                items-start
                gap-2.5
                max-w-[85%]
                ${
                  message.role === "user"
                    ? "ml-auto flex-row-reverse"
                    : "mr-auto"
                }
              `}
            >

              {/* AVATAR */}

              <div
                className={`
                  w-7
                  h-7
                  rounded-full
                  flex
                  items-center
                  justify-center
                  shrink-0
                  text-white
                  ${
                    message.role === "user"
                      ? "bg-rose-500"
                      : "bg-gradient-to-tr from-indigo-500 to-purple-600"
                  }
                `}
              >

                {message.role === "user"
                  ? (
                    <User
                      className="
                        w-4
                        h-4
                      "
                    />
                  )
                  : (
                    <MessageSquare
                      className="
                        w-4
                        h-4
                      "
                    />
                  )}

              </div>


              {/* MESSAGE */}

              <div
                className={`
                  p-3
                  rounded-2xl
                  relative
                  shadow-sm
                  ${
                    message.role === "user"
                      ? "bg-rose-500 text-white rounded-tr-none"
                      : "bg-white text-gray-800 rounded-tl-none border border-slate-100"
                  }
                `}
              >

                <p
                  className="
                    text-sm
                    font-medium
                    leading-relaxed
                    whitespace-pre-wrap
                    pr-5
                  "
                >
                  {message.content}
                </p>


                {/* PLAY MESSAGE */}

                {message.role ===
                  "assistant" &&
                  speechSupported && (

                    <button
                      type="button"

                      onClick={() =>
                        speakText(
                          message.content
                        )
                      }

                      className="
                        absolute
                        right-2
                        bottom-1.5
                        text-gray-400
                        hover:text-rose-500
                        p-0.5
                        rounded
                        transition-colors
                      "

                      title="Listen"
                    >

                      <Volume2
                        className="
                          w-3.5
                          h-3.5
                        "
                      />

                    </button>
                  )}

              </div>

            </div>
          )
        )}


        {/* ===================================================================
            LOADING
        ==================================================================== */}

        {isLoading && (

          <div
            className="
              flex
              items-center
              space-x-2
              mr-auto
              max-w-[80%]
            "
          >

            <div
              className="
                w-7
                h-7
                rounded-full
                bg-indigo-500
                flex
                items-center
                justify-center
                text-white
                shrink-0
              "
            >

              <MessageSquare
                className="
                  w-4
                  h-4
                "
              />

            </div>


            <div
              className="
                bg-white
                border
                border-slate-100
                p-3
                rounded-2xl
                rounded-tl-none
                flex
                items-center
                space-x-1.5
                shadow-sm
              "
            >

              <span
                className="
                  w-2
                  h-2
                  bg-gray-400
                  rounded-full
                  animate-bounce
                "
              />


              <span
                className="
                  w-2
                  h-2
                  bg-gray-400
                  rounded-full
                  animate-bounce
                "

                style={{
                  animationDelay:
                    "150ms",
                }}
              />


              <span
                className="
                  w-2
                  h-2
                  bg-gray-400
                  rounded-full
                  animate-bounce
                "

                style={{
                  animationDelay:
                    "300ms",
                }}
              />

            </div>

          </div>
        )}


        <div
          ref={messagesEndRef}
        />

      </div>


      {/* =====================================================================
          INPUT
      ====================================================================== */}

      <form
        onSubmit={
          handleSendMessage
        }

        className="
          p-3
          bg-white
          border-t
          border-gray-100
          flex
          items-center
          gap-2
          shrink-0
        "
      >

        {/* MICROPHONE */}

        <button
          type="button"

          onClick={
            toggleListening
          }

          disabled={
            isLoading
          }

          className={`
            p-3
            rounded-xl
            border
            flex
            items-center
            justify-center
            transition-all
            ${
              isListening
                ? "bg-red-500 text-white border-red-500 animate-pulse"
                : "bg-gray-50 hover:bg-gray-100 text-gray-500 border-gray-200"
            }
          `}

          title={
            isListening
              ? "Stop listening"
              : `Speak in ${language}`
          }
        >

          {isListening
            ? (
              <MicOff
                className="
                  w-4
                  h-4
                "
              />
            )
            : (
              <Mic
                className="
                  w-4
                  h-4
                "
              />
            )}

        </button>


        {/* INPUT */}

        <input
          type="text"

          value={
            inputText
          }

          onChange={(
            event
          ) =>
            setInputText(
              event.target.value
            )
          }

          placeholder={
            isListening
              ? `Listening in ${language}...`
              : `Ask about ${monumentName}...`
          }

          disabled={
            isLoading ||
            isListening
          }

          className="
            flex-1
            bg-gray-50
            border
            border-gray-200
            text-gray-800
            text-sm
            py-3
            px-4
            rounded-xl
            focus:outline-none
            focus:ring-2
            focus:ring-rose-500
            focus:border-rose-500
            transition-all
          "
        />


        {/* SEND */}

        <button
          type="submit"

          disabled={
            !inputText.trim() ||
            isLoading
          }

          className="
            p-3
            bg-rose-500
            hover:bg-rose-600
            disabled:bg-gray-100
            disabled:text-gray-400
            text-white
            rounded-xl
            shadow-sm
            transition-all
            transform
            active:scale-95
          "

          title="Send message"
        >

          <Send
            className="
              w-4
              h-4
            "
          />

        </button>

      </form>

    </div>
  );
}
