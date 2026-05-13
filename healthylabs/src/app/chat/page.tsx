'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Plus, 
  RefreshCw, 
  ChevronLeft, 
  Home, 
  Paperclip, 
  Mic, 
  Bot,
  Menu,
  MessageSquare,
  User,
  Send,
  X
} from 'lucide-react';
import Link from 'next/link';
import { supabase } from '@/lib/supabaseClient';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

type ChatSession = {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
};

type DiagnosticChatResponse = {
  answer: string;
};

type UserProfileForChat = {
  age: number | null;
  sex: string | null;
  conditions: string[];
  allergies: string[];
  current_medications: string[];
  habits: string[];
  family_history: string[];
  height: number | null;
  weight: number | null;
};

type LocationContext = {
  country_code: string | null;
  timezone: string | null;
  locale: string | null;
  latitude: number | null;
  longitude: number | null;
  location_permission: string | null;
};

type SpeechRecognitionResultEventLike = {
  results: {
    length: number;
    [resultIndex: number]: {
      isFinal: boolean;
      [alternativeIndex: number]: {
        transcript: string;
      };
    };
  };
};

type SpeechRecognitionErrorEventLike = {
  error: string;
};

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onstart: (() => void) | null;
  onresult: ((event: SpeechRecognitionResultEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

type WindowWithSpeechRecognition = Window &
  typeof globalThis & {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };

const defaultUserProfile: UserProfileForChat = {
  age: null,
  sex: null,
  conditions: [],
  allergies: [],
  current_medications: [],
  habits: [],
  family_history: [],
  height: null,
  weight: null,
};

const CHAT_HISTORY_STORAGE_KEY = 'healthylabs-chat-sessions-v1';

function createId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

const createWelcomeMessage = (): ChatMessage => ({
  id: createId(),
  role: 'assistant',
  content: 'Ask a health question and I will help you understand what to do next.',
});

const createChatSession = (): ChatSession => {
  const now = Date.now();
  return {
    id: createId(),
    title: 'New chat',
    messages: [createWelcomeMessage()],
    createdAt: now,
    updatedAt: now,
  };
};

function titleFromQuestion(question: string): string {
  const trimmed = question.trim().replace(/\s+/g, ' ');
  return trimmed.length <= 42 ? trimmed : `${trimmed.slice(0, 39)}...`;
}

function isWelcomeMessage(message: ChatMessage): boolean {
  return message.role === 'assistant' && message.content === 'Ask a health question and I will help you understand what to do next.';
}

const defaultLocationContext = (): LocationContext => {
  const locale = typeof navigator !== 'undefined' ? navigator.language || null : null;
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  return {
    country_code: inferCountryCode(locale, timezone),
    timezone,
    locale,
    latitude: null,
    longitude: null,
    location_permission: 'not_requested',
  };
};

function splitProfileText(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map(String).map(item => item.trim()).filter(Boolean);
  }
  if (typeof value !== 'string') {
    return [];
  }
  return value
    .split(/[,;\n]/)
    .map(item => item.trim())
    .filter(Boolean);
}

function toNumberOrNull(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function inferCountryCode(locale: string | null, timezone: string | null): string | null {
  if (timezone === 'Asia/Kolkata' || timezone === 'Asia/Calcutta') {
    return 'IN';
  }
  const localeRegion = locale?.split('-')[1]?.toUpperCase();
  if (localeRegion) {
    return localeRegion;
  }
  return 'IN';
}

export default function AIChatInterface() {
  const initialSessionRef = useRef<ChatSession | null>(null);
  if (!initialSessionRef.current) {
    initialSessionRef.current = createChatSession();
  }

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inputText, setInputText] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>(() => [initialSessionRef.current as ChatSession]);
  const [activeSessionId, setActiveSessionId] = useState<string>(() => (initialSessionRef.current as ChatSession).id);
  const [isSending, setIsSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [userProfile, setUserProfile] = useState<UserProfileForChat>(defaultUserProfile);
  const [locationContext, setLocationContext] = useState<LocationContext>(() => defaultLocationContext());
  const [historyLoaded, setHistoryLoaded] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const preRecordingInputRef = useRef<string>('');
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeSession = useMemo(
    () => chatSessions.find(session => session.id === activeSessionId) || chatSessions[0],
    [activeSessionId, chatSessions]
  );
  const messages = useMemo(() => activeSession?.messages || [], [activeSession]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(CHAT_HISTORY_STORAGE_KEY);
      if (!saved) {
        setHistoryLoaded(true);
        return;
      }

      const parsed = JSON.parse(saved) as { sessions?: ChatSession[]; activeSessionId?: string };
      const validSessions = Array.isArray(parsed.sessions)
        ? parsed.sessions.filter(session => Array.isArray(session.messages) && session.id)
        : [];

      if (validSessions.length > 0) {
        setChatSessions(validSessions);
        setActiveSessionId(
          validSessions.some(session => session.id === parsed.activeSessionId)
            ? parsed.activeSessionId as string
            : validSessions[0].id
        );
      }
    } catch (error) {
      console.error('Unable to load chat history:', error);
    } finally {
      setHistoryLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (!historyLoaded) {
      return;
    }

    localStorage.setItem(
      CHAT_HISTORY_STORAGE_KEY,
      JSON.stringify({ sessions: chatSessions, activeSessionId })
    );
  }, [activeSessionId, chatSessions, historyLoaded]);

  useEffect(() => {
    const messagesContainer = messagesContainerRef.current;
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }, [messages, isSending]);

  useEffect(() => {
    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverscroll = document.documentElement.style.overscrollBehavior;

    document.body.style.overflow = 'hidden';
    document.documentElement.style.overscrollBehavior = 'none';

    return () => {
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.overscrollBehavior = previousHtmlOverscroll;
    };
  }, []);

  useEffect(() => {
    const loadProfile = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        setUserProfile(defaultUserProfile);
        return;
      }

      const { data } = await supabase
        .from('profiles')
        .select('age, gender, height, weight, conditions, medications, allergies, lifestyle, family_history')
        .eq('id', user.id)
        .single();

      if (!data) {
        setUserProfile(defaultUserProfile);
        return;
      }

      setUserProfile({
        age: toNumberOrNull(data.age),
        sex: data.gender || null,
        height: toNumberOrNull(data.height),
        weight: toNumberOrNull(data.weight),
        conditions: splitProfileText(data.conditions),
        allergies: splitProfileText(data.allergies),
        current_medications: splitProfileText(data.medications),
        habits: splitProfileText(data.lifestyle),
        family_history: splitProfileText(data.family_history),
      });
    };

    loadProfile();
  }, []);

  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationContext(prev => ({ ...prev, location_permission: 'unsupported' }));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      position => {
        setLocationContext(prev => ({
          ...prev,
          country_code: inferCountryCode(prev.locale, prev.timezone),
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          location_permission: 'granted',
        }));
      },
      () => {
        setLocationContext(prev => ({
          ...prev,
          location_permission: 'denied_or_unavailable',
        }));
      },
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 3000 }
    );
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  const toggleRecording = () => {
    if (isRecording) {
      recognitionRef.current?.stop();
      setIsRecording(false);
      return;
    }

    const speechWindow = window as WindowWithSpeechRecognition;
    const SpeechRecognition = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Your browser does not support Speech Recognition. Try Chrome or Edge.");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;
      recognition.continuous = false;
      recognition.interimResults = true; // Enable interim results for live feedback

      if (window.navigator?.language) {
        recognition.lang = window.navigator.language;
      }

      recognition.onstart = () => {
        preRecordingInputRef.current = inputText; // Save text before starting
        setIsRecording(true);
      };
      recognition.onresult = (event) => {
        // Combine all results so far to get the full transcript
        const transcript = Array.from(event.results)
          .map(result => result[0].transcript)
          .join('');

        // Check if the latest result is final
        const isFinal = event.results[event.results.length - 1].isFinal;
        
        const separator = preRecordingInputRef.current.trim() ? ' ' : '';
        const fullText = preRecordingInputRef.current + separator + transcript;

        if (isFinal) {
          setInputText(fullText);
        } else {
          // Add an ellipsis for the "listening" animation on interim results
          setInputText(fullText + '...');
        }
      };
      recognition.onerror = (event) => {
        if (event.error === 'no-speech') {
          console.log("Speech recognition stopped: No speech detected.");
        } else {
          console.error("Speech recognition error", event.error);
        }
        // On error, revert to the text that was there before recording started
        setInputText(preRecordingInputRef.current);
        setIsRecording(false);
      };
      recognition.onend = () => {
        setIsRecording(false);
        // Clean up any trailing ellipsis when recognition ends
        setInputText(prev => (prev.endsWith('...') ? prev.slice(0, -3) : prev));
      };

      recognition.start();
    } catch (err) {
      console.error("Speech recognition initialization failed:", err);
      setIsRecording(false);
    }
  };

  const selectChatSession = (sessionId: string) => {
    if (isSending) {
      return;
    }
    setActiveSessionId(sessionId);
    setInputText('');
    setSelectedFile(null);
    setErrorMessage('');
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  const handleNewChat = () => {
    if (isSending) {
      return;
    }
    const session = createChatSession();
    setChatSessions(prev => [session, ...prev]);
    setActiveSessionId(session.id);
    setInputText('');
    setSelectedFile(null);
    setErrorMessage('');
  };

  const handleSubmit = async () => {
    const question = inputText.trim();

    if (!question || isSending) {
      return;
    }

    const userMessage: ChatMessage = {
      id: createId(),
      role: 'user',
      content: selectedFile ? `${question}\n\nAttached image: ${selectedFile.name}` : question,
    };
    const attachedFile = selectedFile;
    const priorMessages = messages.filter(message => !isWelcomeMessage(message));
    const nextTitle = activeSession?.title === 'New chat' ? titleFromQuestion(question) : activeSession?.title || titleFromQuestion(question);

    setChatSessions(prev =>
      prev.map(session =>
        session.id === activeSessionId
          ? {
              ...session,
              title: nextTitle,
              messages: [...session.messages, userMessage],
              updatedAt: Date.now(),
            }
          : session
      )
    );
    setInputText('');
    setSelectedFile(null);
    setErrorMessage('');
    setIsSending(true);

    try {
      const requestPayload = {
        question,
        user_profile: userProfile,
        location_context: locationContext,
        session_id: activeSessionId,
        chat_history: priorMessages.map(message => ({
          role: message.role,
          content: message.content,
        })),
      };
      const requestBody = new FormData();
      requestBody.append('payload', JSON.stringify(requestPayload));
      if (attachedFile) {
        requestBody.append('image', attachedFile);
      }

      const response = await fetch('/api/diagnostic-chat', {
        method: 'POST',
        body: requestBody,
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail || payload.message || 'Health assistant request failed.');
      }

      const diagnostic = payload as DiagnosticChatResponse;
      const assistantMessage: ChatMessage = {
        id: createId(),
        role: 'assistant',
        content: diagnostic.answer || 'The diagnostic system returned an empty answer.',
      };

      setChatSessions(prev =>
        prev.map(session =>
          session.id === activeSessionId
            ? {
                ...session,
                messages: [...session.messages, assistantMessage],
                updatedAt: Date.now(),
              }
            : session
        )
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to reach the health assistant.';
      const assistantMessage: ChatMessage = {
        id: createId(),
        role: 'assistant',
        content: `I could not get a diagnostic answer right now. ${message}`,
      };
      setErrorMessage(message);
      setChatSessions(prev =>
        prev.map(session =>
          session.id === activeSessionId
            ? {
                ...session,
                messages: [...session.messages, assistantMessage],
                updatedAt: Date.now(),
              }
            : session
        )
      );
    } finally {
      setIsSending(false);
    }
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;500;600&family=Inter:wght@400;500&display=swap');
        
        @keyframes float-slow {
            0% { transform: translate(0px, 0px) scale(1); }
            33% { transform: translate(30px, -50px) scale(1.1); }
            66% { transform: translate(-20px, 20px) scale(0.9); }
            100% { transform: translate(0px, 0px) scale(1); }
        }
        .animate-float-1 { animation: float-slow 8s ease-in-out infinite; }
        .animate-float-2 { animation: float-slow 10s ease-in-out infinite reverse; }
        .animate-float-3 { animation: float-slow 12s ease-in-out infinite 1s; }
        
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: rgba(148, 163, 184, 0.3);
          border-radius: 20px;
        }

        .chat-viewport {
          --chat-top-offset: max(env(safe-area-inset-top), 12px);
          position: fixed;
          inset: var(--chat-top-offset) 0 0 0;
          height: auto;
          max-height: none;
          box-sizing: border-box;
          overflow: hidden;
          overscroll-behavior: none;
          isolation: isolate;
        }
      `}</style>

      <div className="chat-viewport flex w-full bg-gradient-to-br from-[#cbe5ff] via-[#dcedff] to-[#e1f0ff] font-sans relative">
        
        {/* ================= BACKGROUND ORBS ================= */}
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-white/60 rounded-full blur-[100px] animate-float-1 pointer-events-none"></div>
        <div className="absolute top-[20%] right-[-5%] w-[400px] h-[400px] bg-blue-300/30 rounded-full blur-[80px] animate-float-2 pointer-events-none"></div>
        <div className="absolute bottom-[-10%] left-[20%] w-[600px] h-[600px] bg-cyan-200/40 rounded-full blur-[100px] animate-float-3 pointer-events-none"></div>

        {/* ================= SIDEBAR (HISTORY) ================= */}
        <div 
          className={`${
            sidebarOpen ? 'w-72 translate-x-0' : 'w-0 -translate-x-full opacity-0'
          } bg-white/30 backdrop-blur-xl border-r border-white/50 text-slate-800 transition-all duration-300 flex flex-col flex-shrink-0 absolute md:relative z-30 h-full shadow-lg overflow-hidden`}
        >
          {/* New Chat Button */}
          <div className="p-4 border-b border-white/40">
            <button type="button" onClick={handleNewChat} disabled={isSending} className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-white/50 hover:bg-white/80 rounded-xl border border-white/60 transition-all text-sm font-semibold shadow-sm text-slate-700 disabled:cursor-not-allowed disabled:opacity-60">
              <Plus className="w-4 h-4" />
              New Chat
            </button>
          </div>

          {/* History List */}
          <div className="flex-1 overflow-y-auto px-3 py-4 custom-scrollbar">
            <div className="px-1 py-2 text-xs font-bold text-slate-500 uppercase tracking-wider flex justify-between items-center mb-2">
              <span>Recent Chats</span>
              <button type="button" className="hover:text-blue-600 transition-colors" title="Refresh History">
                <RefreshCw className="w-3 h-3" />
              </button>
            </div>
            
            <div className="space-y-1">
              {[...chatSessions]
                .sort((a, b) => b.updatedAt - a.updatedAt)
                .map(session => (
                  <button
                    key={session.id}
                    type="button"
                    onClick={() => selectChatSession(session.id)}
                    disabled={isSending}
                    className={`w-full flex items-start gap-2 rounded-xl px-3 py-2 text-left text-sm border transition-all ${
                      session.id === activeSessionId
                        ? 'bg-white/80 border-blue-200 text-blue-700 shadow-sm'
                        : 'bg-white/30 border-white/40 text-slate-600 hover:bg-white/60'
                    } ${isSending ? 'cursor-not-allowed opacity-70' : ''}`}
                  >
                    <MessageSquare className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-500" />
                    <span className="line-clamp-2">{session.title}</span>
                  </button>
                ))}
              {chatSessions.length === 0 && (
                <div className="px-3 py-4 text-sm text-slate-400 text-center italic">
                  No chat history yet
                </div>
              )}
            </div>
          </div>
          
          
        </div>

        {/* ================= MAIN CONTENT AREA ================= */}
        <div className="flex-1 flex flex-col h-full min-w-0 min-h-0 overflow-hidden relative z-10">
          
          {/* Mobile Overlay */}
          {sidebarOpen && (
            <div 
              className="fixed inset-0 bg-black/20 backdrop-blur-sm z-10 md:hidden"
              onClick={() => setSidebarOpen(false)}
            />
          )}

          {/* Header / Toggle */}
          <header className="shrink-0 p-4 flex items-center justify-between bg-white/40 backdrop-blur-md border-b border-white/60 shadow-sm z-10">
            <div className="flex items-center gap-4">
              <button
              type="button"
              onClick={() => setSidebarOpen(prev => !prev)}
              className="p-2 hover:bg-white/60 rounded-lg transition-colors text-slate-700 relative z-50"
              >
                {sidebarOpen ? <ChevronLeft className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
            </div>
            
            {/* Page Title for Desktop */}
            <div className="hidden md:block absolute left-1/2 transform -translate-x-1/2">
               <h1 className="text-xl font-lora font-bold text-slate-800 tracking-tight">
                AI Diagnostic <span className="text-blue-600">Chat</span>
              </h1>
            </div>

            <Link 
              href="/dashboard" 
              className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:text-blue-600 hover:bg-white/60 rounded-full transition-all font-medium border border-transparent hover:border-white/60"
            >
              <Home className="w-5 h-5" />
              <span className="hidden sm:inline">Home</span>
            </Link>
          </header>

          {/* Chat Container Wrapper */}
          <div className="flex-1 min-h-0 p-2 sm:p-4 lg:p-6 overflow-hidden flex flex-col">
            
            <div className="flex-1 min-h-0 max-w-5xl w-full mx-auto bg-white/60 backdrop-blur-xl rounded-[2rem] shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] border border-white/80 flex flex-col overflow-hidden relative">
              
              {/* Chat Area Header */}
              <div className="shrink-0 px-6 py-4 border-b border-white/50 bg-white/40 flex items-center gap-3 shadow-sm z-10">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-100 to-indigo-100 border border-white flex items-center justify-center text-blue-600 shadow-sm">
                  <Bot size={20} />
                </div>
                <div>
                  <h2 className="font-bold text-slate-800 text-lg leading-tight">AI Health Assistant</h2>
                  <p className="text-xs text-blue-600 font-medium flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span> Online
                  </p>
                </div>
              </div>

              {/* Messages Area */}
              <div ref={messagesContainerRef} className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 flex flex-col gap-6 custom-scrollbar">
                {messages.map(message => (
                  <div
                    key={message.id}
                    className={`flex items-start gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {message.role === 'assistant' && (
                      <div className="w-9 h-9 rounded-full bg-blue-100 text-blue-600 border border-white flex items-center justify-center flex-shrink-0">
                        <Bot size={18} />
                      </div>
                    )}

                    <div
                      className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm border ${
                        message.role === 'user'
                          ? 'bg-blue-600 text-white border-blue-500 rounded-tr-md'
                          : 'bg-white/80 text-slate-700 border-white/80 rounded-tl-md'
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{message.content}</div>

                    </div>

                    {message.role === 'user' && (
                      <div className="w-9 h-9 rounded-full bg-slate-800 text-white border border-white flex items-center justify-center flex-shrink-0">
                        <User size={17} />
                      </div>
                    )}
                  </div>
                ))}

                {isSending && (
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 rounded-full bg-blue-100 text-blue-600 border border-white flex items-center justify-center flex-shrink-0">
                      <Bot size={18} />
                    </div>
                    <div className="rounded-2xl rounded-tl-md bg-white/80 border border-white/80 px-4 py-3 text-sm text-slate-500 shadow-sm">
                      Thinking...
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="shrink-0 p-4 sm:p-5 bg-white/30 backdrop-blur-xl border-t border-white/60 relative z-10">
                
                {/* --- File Preview --- */}
                {selectedFile && (
                  <div className="max-w-4xl mx-auto mb-2 flex items-center gap-2 bg-white/60 backdrop-blur-md border border-white/80 py-2 px-3 rounded-xl w-max">
                    <span className="text-xs font-medium text-slate-700 truncate max-w-[200px]">{selectedFile.name}</span>
                    <button type="button" onClick={() => setSelectedFile(null)} className="text-slate-400 hover:text-red-500 transition-colors">
                      <X size={14} />
                    </button>
                  </div>
                )}

                <form 
                  className="max-w-4xl mx-auto flex items-end gap-2 bg-white/70 backdrop-blur-md border border-white/80 shadow-[0_4px_16px_rgba(0,0,0,0.04)] rounded-3xl p-2 transition-all focus-within:ring-2 focus-within:ring-blue-400/50 focus-within:bg-white"
                  onSubmit={(e) => { 
                    e.preventDefault(); 
                    handleSubmit();
                  }}
                >
                  
                  {/* Hidden File Input */}
                  <input type="file" className="hidden" ref={fileInputRef} onChange={handleFileChange} />

                  {/* Actions (Left) */}
                  <div className="flex items-center gap-1 pb-1 pl-1">
                    <button type="button" onClick={triggerFileSelect} className="p-2.5 text-slate-400 hover:text-blue-600 transition-colors rounded-full hover:bg-blue-50">
                      <Paperclip size={20} />
                    </button>
                    <button type="button" onClick={toggleRecording} className={`p-2.5 transition-colors rounded-full hover:bg-blue-50 ${isRecording ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-blue-600'}`}>
                      <Mic size={20} />
                    </button>
                  </div>
                  
                  {/* Textarea / Input */}
                  <textarea
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Type your symptoms or ask a medical question..."
                    className="flex-1 bg-transparent border-none focus:outline-none text-slate-700 placeholder:text-slate-400 py-3 px-2 resize-none max-h-32 min-h-[44px] custom-scrollbar"
                    rows={1}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSubmit();
                      }
                    }}
                  />
                  
                  {/* Submit Button (Right) */}
                  <div className="pb-1 pr-1">
                    <button 
                      type="submit"
                      disabled={!inputText.trim() || isSending}
                      className={`p-3 rounded-full flex items-center justify-center transition-all duration-300 shadow-sm ${
                        inputText.trim() && !isSending
                          ? 'bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white cursor-pointer hover:scale-105' 
                          : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                      }`}
                    >
                      <Send size={18} className={inputText.trim() && !isSending ? 'ml-0.5' : ''} />
                    </button>
                  </div>

                </form>

                {errorMessage && (
                  <p className="mx-auto mt-3 max-w-4xl text-center text-xs font-medium text-red-600">
                    {errorMessage}
                  </p>
                )}
                
                {/* Disclaimer Text */}
                <div className="text-center mt-3">
                  <p className="text-xs text-slate-500">
                    AI can make mistakes. This chat is for informational purposes and is <span className="font-semibold">not a substitute for professional medical advice</span>.
                  </p>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>
    </>
  );
}
