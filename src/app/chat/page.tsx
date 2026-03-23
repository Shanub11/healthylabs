'use client';

import React, { useState, useRef } from 'react';
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

export default function AIChatInterface() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inputText, setInputText] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);

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

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Your browser does not support Speech Recognition. Try Chrome or Edge.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => setIsRecording(true);
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInputText(prev => prev + (prev ? ' ' : '') + transcript);
    };
    recognition.onerror = (event: any) => {
      console.error("Speech recognition error", event.error);
      setIsRecording(false);
    };
    recognition.onend = () => setIsRecording(false);

    recognition.start();
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
      `}</style>

      <div className="flex h-screen bg-gradient-to-br from-[#cbe5ff] via-[#dcedff] to-[#e1f0ff] font-sans overflow-hidden relative">
        
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
            <button className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-white/50 hover:bg-white/80 rounded-xl border border-white/60 transition-all text-sm font-semibold shadow-sm text-slate-700">
              <Plus className="w-4 h-4" />
              New Chat
            </button>
          </div>

          {/* History List */}
          <div className="flex-1 overflow-y-auto px-3 py-4 custom-scrollbar">
            <div className="px-1 py-2 text-xs font-bold text-slate-500 uppercase tracking-wider flex justify-between items-center mb-2">
              <span>Recent Chats</span>
              <button className="hover:text-blue-600 transition-colors" title="Refresh History">
                <RefreshCw className="w-3 h-3" />
              </button>
            </div>
            
            <div className="space-y-1">
              {/* TODO: Map your backend history items here */}
              <div className="px-3 py-4 text-sm text-slate-400 text-center italic">
                No chat history yet
              </div>
            </div>
          </div>
          
          
        </div>

        {/* ================= MAIN CONTENT AREA ================= */}
        <div className="flex-1 flex flex-col h-full overflow-hidden relative z-10">
          
          {/* Mobile Overlay */}
          {sidebarOpen && (
            <div 
              className="fixed inset-0 bg-black/20 backdrop-blur-sm z-10 md:hidden"
              onClick={() => setSidebarOpen(false)}
            />
          )}

          {/* Header / Toggle */}
          <header className="p-4 flex items-center justify-between bg-white/40 backdrop-blur-md border-b border-white/60 shadow-sm z-10">
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
          <div className="flex-1 p-2 sm:p-4 lg:p-6 overflow-hidden flex flex-col">
            
            <div className="flex-1 max-w-5xl w-full mx-auto bg-white/60 backdrop-blur-xl rounded-[2rem] shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] border border-white/80 flex flex-col overflow-hidden relative">
              
              {/* Chat Area Header */}
              <div className="px-6 py-4 border-b border-white/50 bg-white/40 flex items-center gap-3 shadow-sm z-10">
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
              <div className="flex-1 overflow-y-auto p-4 sm:p-6 flex flex-col gap-6 custom-scrollbar">
                
                {/* TODO: Map backend chat messages here */}
              </div>

              {/* Input Area */}
              <div className="p-4 sm:p-5 bg-white/30 backdrop-blur-xl border-t border-white/60 relative z-10">
                
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
                    /* handle send */ 
                    setInputText(''); 
                    setSelectedFile(null);
                  }}
                >
                  
                  {/* Hidden File Input */}
                  <input type="file" className="hidden" ref={fileInputRef} onChange={handleFileChange} />

                  {/* Actions (Left) */}
                  <div className="flex items-center gap-1 pb-1 pl-1">
                    <button type="button" onClick={triggerFileSelect} className="p-2.5 text-slate-400 hover:text-blue-600 transition-colors rounded-full hover:bg-blue-50">
                      <Paperclip size={20} />
                    </button>
                    <button type="button" onClick={toggleRecording} className={`p-2.5 transition-colors rounded-full hover:bg-blue-50 hidden sm:block ${isRecording ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-blue-600'}`}>
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
                        // Handle Submit logic
                        setInputText('');
                        setSelectedFile(null);
                      }
                    }}
                  />
                  
                  {/* Submit Button (Right) */}
                  <div className="pb-1 pr-1">
                    <button 
                      type="submit"
                      disabled={!inputText.trim() && !selectedFile}
                      className={`p-3 rounded-full flex items-center justify-center transition-all duration-300 shadow-sm ${
                        (inputText.trim() || selectedFile)
                          ? 'bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white cursor-pointer hover:scale-105' 
                          : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                      }`}
                    >
                      <Send size={18} className={(inputText.trim() || selectedFile) ? 'ml-0.5' : ''} />
                    </button>
                  </div>

                </form>
                
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