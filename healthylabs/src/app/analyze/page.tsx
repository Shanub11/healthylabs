'use client';

import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { supabase } from '@/lib/supabaseClient';
import { Upload, FileText, Activity, AlertTriangle, CheckCircle, Loader2, File as FileIcon, XCircle, Copy, Check, Menu, Plus, MessageSquare, Clock, ChevronLeft, Home, RefreshCw } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function AnalyzeReportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'upload' | 'text'>('upload');
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [copied, setCopied] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  
  const uploadSectionRef = useRef<HTMLDivElement>(null);
  const resultSectionRef = useRef<HTMLDivElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setText('');
      setError('');
    }
  };

  const fetchHistory = async () => {
    setHistoryLoading(true);
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      try {
        const response = await axios.get(`${API_URL}/history/${user.id}`);
        setHistory(response.data || []);
      } catch (error) {
        console.error("Failed to fetch history", error);
      } finally {
        setHistoryLoading(false);
      }
    } else {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
        if (event === 'SIGNED_IN') {
            fetchHistory();
        }
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setText('');
      setActiveTab('upload');
      setError('');
    }
  };

  const removeFile = () => {
    setFile(null);
    setError('');
  };

  const handleCancel = () => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
    }
  };

  const handleCopy = () => {
    if (result?.summary) {
      navigator.clipboard.writeText(result.summary);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const startNewAnalysis = () => {
    setFile(null);
    setText('');
    setResult(null);
    setError('');
    setActiveTab('upload');
    
    setTimeout(() => {
      uploadSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  };

  const loadHistoryItem = (item: any) => {
    setResult({
      summary: item.ai_summary,
      confidence: item.confidence
    });
    setText(item.source === 'text' ? item.original_text : '');
    setFile(null);
    if (window.innerWidth < 768) setSidebarOpen(false);
    
    setTimeout(() => {
      resultSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file && !text) return;

    const controller = new AbortController();
    setAbortController(controller);

    setLoading(true);
    setUploadProgress(0);
    setError('');
    setResult(null);

    const formData = new FormData();
    if (file) {
      formData.append('file', file);
    } else if (text) {
      formData.append('text', text);
    }
    
    // Get current user and append ID to form data for MongoDB storage
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      formData.append('user_id', user.id);
    }

    try {
      // Pointing to the FastAPI backend (ensure it's running on port 8000)
      const response = await axios.post(`${API_URL}/analyze-report`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        signal: controller.signal,
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
          setUploadProgress(percentCompleted);
        },
      });
      setResult(response.data);
      fetchHistory(); // Refresh history after new analysis
      
      setTimeout(() => {
        resultSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);

    } catch (err: any) {
      if (axios.isCancel(err)) {
        setError('Analysis cancelled by user.');
      } else {
        console.error(err);
        setError(err.response?.data?.detail || 'Failed to analyze report. Please ensure the backend is running.');
      }
    } finally {
      setLoading(false);
      setAbortController(null);
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
      `}</style>
    <div className="flex h-screen bg-gradient-to-br from-[#cbe5ff] via-[#dcedff] to-[#e1f0ff] font-sans overflow-hidden relative">
      {/* Background Orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-white/60 rounded-full blur-[100px] animate-float-1 pointer-events-none"></div>
      <div className="absolute top-[20%] right-[-5%] w-[400px] h-[400px] bg-blue-300/30 rounded-full blur-[80px] animate-float-2 pointer-events-none"></div>
      <div className="absolute bottom-[-10%] left-[20%] w-[600px] h-[600px] bg-cyan-200/40 rounded-full blur-[100px] animate-float-3 pointer-events-none"></div>

      {/* Sidebar */}
      <div 
        className={`${
          sidebarOpen ? 'w-64 translate-x-0' : 'w-0 -translate-x-full opacity-0'
        } bg-white/30 backdrop-blur-xl border-r border-white/50 text-slate-800 transition-all duration-300 flex flex-col flex-shrink-0 absolute md:relative z-20 h-full overflow-hidden shadow-lg`}
      >
        <div className="p-4">
          <button
            onClick={startNewAnalysis}
            className="w-full flex items-center gap-2 px-4 py-3 bg-white/50 hover:bg-white/80 rounded-xl border border-white/60 transition-all text-sm font-semibold shadow-sm text-slate-700"
          >
            <Plus className="w-4 h-4" />
            New Analysis
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 pb-4 custom-scrollbar">
          <div className="px-2 py-2 text-xs font-bold text-slate-500 uppercase tracking-wider flex justify-between items-center">
            <span>History</span>
            <button onClick={fetchHistory} className="hover:text-blue-600 transition-colors" title="Refresh History">
                <RefreshCw className={`w-3 h-3 ${historyLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <div className="space-y-1">
            {history && history.map((item) => (
              <button
                key={item._id}
                onClick={() => loadHistoryItem(item)}
                className="w-full flex items-center gap-3 px-3 py-3 text-sm text-slate-600 hover:bg-white/60 hover:text-blue-700 rounded-xl transition-all text-left group border border-transparent hover:border-white/50"
              >
                <MessageSquare className="w-4 h-4 flex-shrink-0 opacity-70 group-hover:opacity-100" />
                <div className="flex-1 truncate">
                  <span className="block truncate font-medium">
                    {new Date(item.created_at).toLocaleDateString()} Report
                  </span>
                  <span className="text-xs text-slate-400 truncate block group-hover:text-slate-500">
                    {item.original_text?.substring(0, 30)}...
                  </span>
                </div>
              </button>
            ))}
            {(!history || history.length === 0) && (
              <div className="px-3 py-4 text-sm text-slate-400 text-center italic">
                No history yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative z-10">
        {/* Mobile Overlay */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/20 backdrop-blur-sm z-10 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Header / Toggle */}
        <div className="p-4 flex items-center justify-between bg-white/40 backdrop-blur-md border-b border-white/60 shadow-sm">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-white/60 rounded-lg transition-colors text-slate-700"
            >
              {sidebarOpen ? <ChevronLeft className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
          <Link 
            href="/dashboard" 
            className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:text-blue-600 hover:bg-white/60 rounded-full transition-all font-medium border border-transparent hover:border-white/60"
          >
            <Home className="w-5 h-5" />
            <span>Home</span>
          </Link>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 custom-scrollbar">
          <div className="max-w-4xl mx-auto pb-20">
            <div className="text-center mb-10" ref={uploadSectionRef}>
              <h1 className="text-4xl font-lora font-bold text-slate-800 tracking-tight sm:text-5xl mb-3">
                AI Report <span className="text-blue-600">Analyzer</span>
              </h1>
              <p className="text-lg text-slate-600 font-medium max-w-2xl mx-auto">
                Upload your medical reports or paste text to get an instant, easy-to-understand summary powered by AI.
              </p>
            </div>

            <div className="bg-white/60 backdrop-blur-xl rounded-[2rem] shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] overflow-hidden border border-white/80">
              {/* Header / Tabs */}
              <div className="flex border-b border-white/50">
                <button
                  onClick={() => setActiveTab('upload')}
                  className={`flex-1 py-4 text-sm font-semibold text-center transition-all duration-300 flex items-center justify-center gap-2 ${
                    activeTab === 'upload'
                      ? 'bg-white/50 text-blue-600 border-b-2 border-blue-500'
                      : 'text-slate-500 hover:text-slate-700 hover:bg-white/30'
                  }`}
                >
                  <Upload className="w-4 h-4" />
                  Upload File
                </button>
                <button
                  onClick={() => setActiveTab('text')}
                  className={`flex-1 py-4 text-sm font-semibold text-center transition-all duration-300 flex items-center justify-center gap-2 ${
                    activeTab === 'text'
                      ? 'bg-white/50 text-blue-600 border-b-2 border-blue-500'
                      : 'text-slate-500 hover:text-slate-700 hover:bg-white/30'
                  }`}
                >
                  <FileText className="w-4 h-4" />
                  Paste Text
                </button>
              </div>

              <div className="p-8">
                <form onSubmit={handleSubmit}>
                  {activeTab === 'upload' && (
                    <div 
                      className={`relative border-2 border-dashed rounded-3xl p-12 text-center transition-all duration-300 ${
                        dragActive ? 'border-blue-500 bg-blue-50/50' : 'border-slate-300 hover:border-blue-400 hover:bg-white/40'
                      }`}
                      onDragEnter={handleDrag}
                      onDragLeave={handleDrag}
                      onDragOver={handleDrag}
                      onDrop={handleDrop}
                    >
                      <input
                        type="file"
                        accept=".pdf,image/*"
                        onChange={handleFileChange}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        disabled={loading}
                      />
                      
                      {file ? (
                        <div className="flex flex-col items-center animate-in fade-in zoom-in duration-300">
                          <div className="bg-blue-100 p-4 rounded-full mb-3 shadow-sm">
                            <FileIcon className="w-8 h-8 text-blue-600" />
                          </div>
                          <p className="text-lg font-semibold text-slate-800">{file.name}</p>
                          <p className="text-sm text-slate-500 mb-4">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                          <button 
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              removeFile();
                            }}
                            className="z-10 px-5 py-2 bg-red-50 text-red-600 rounded-full text-sm font-medium hover:bg-red-100 transition-colors shadow-sm border border-red-100"
                          >
                            Remove File
                          </button>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center pointer-events-none">
                          <div className="bg-white p-5 rounded-full mb-4 shadow-sm border border-slate-100">
                            <Upload className="w-8 h-8 text-blue-500" />
                          </div>
                          <p className="text-xl font-semibold text-slate-800">Click to upload or drag and drop</p>
                          <p className="text-sm text-slate-500 mt-2">PDF, JPG, PNG (Max 10MB)</p>
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'text' && (
                    <div className="relative">
                      <textarea
                        value={text}
                        onChange={(e) => { setText(e.target.value); setFile(null); }}
                        placeholder="Paste the content of your medical report here..."
                        rows={12}
                        className="w-full p-5 border border-white/60 bg-white/40 rounded-3xl focus:ring-2 focus:ring-blue-400 focus:border-transparent transition-all resize-y text-slate-700 leading-relaxed placeholder-slate-400 shadow-inner outline-none"
                        disabled={loading}
                      />
                    </div>
                  )}

                  {error && (
                    <div className="mt-6 p-4 bg-red-50/80 backdrop-blur-sm border border-red-100 rounded-2xl flex items-start gap-3 animate-in slide-in-from-top-2">
                      <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                      <p className="text-red-700 text-sm font-medium">{error}</p>
                    </div>
                  )}

                  <div className="mt-8 space-y-3">
                    <button
                      type="submit"
                      disabled={loading || (!file && !text)}
                      className={`w-full py-4 px-6 rounded-2xl cursor-pointer text-white font-bold text-lg shadow-lg shadow-blue-500/20 transition-all duration-300 flex items-center justify-center gap-2 ${
                        (!file && !text)
                          ? 'bg-slate-300 cursor-not-allowed shadow-none'
                          : 'bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 hover:scale-[1.02]'
                      } ${loading ? 'cursor-wait opacity-90' : ''}`}
                    >
                      {loading ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          Analyzing Report...
                        </>
                      ) : (
                        <>
                          <Activity className="w-5 h-5" />
                          Analyze Report
                        </>
                      )}
                    </button>

                    {loading && (
                      <button
                        type="button"
                        onClick={handleCancel}
                        className="w-full py-3 px-6 rounded-2xl text-red-500 font-medium text-sm hover:bg-red-50/50 transition-colors flex items-center justify-center gap-2 border border-transparent hover:border-red-100"
                      >
                        <XCircle className="w-4 h-4" />
                        Cancel Analysis
                      </button>
                    )}
                  </div>
                </form>
              </div>
            </div>

            {/* Results Section */}
            {result && (
              <div className="mt-10 animate-in fade-in slide-in-from-bottom-8 duration-700" ref={resultSectionRef}>
                <div className="bg-white/60 backdrop-blur-xl rounded-[2rem] shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] overflow-hidden border border-white/80">
                  <div className="bg-gradient-to-r from-emerald-500/90 to-teal-600/90 backdrop-blur-md p-5 flex items-center justify-between">
                    <h2 className="text-white font-bold text-xl flex items-center gap-2">
                      <CheckCircle className="w-6 h-6" />
                      Analysis Complete
                    </h2>
                    
                  </div>
                  
                  <div className="p-8">
                    <div className="prose prose-slate max-w-none">
                      <div className="flex items-center justify-between mb-6">
                        <h3 className="text-slate-800 font-lora font-bold text-2xl m-0">Summary & Findings</h3>
                        <button
                          onClick={handleCopy}
                          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-white/50 border border-white/60 rounded-full hover:bg-white hover:shadow-sm transition-all"
                        >
                          {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                          {copied ? 'Copied!' : 'Copy'}
                        </button>
                      </div>
                      <div className="bg-white/40 rounded-3xl p-8 border border-white/60 text-slate-700 leading-relaxed whitespace-pre-wrap shadow-sm font-medium">
                        {result.summary}
                      </div>
                    </div>

                    <div className="mt-8 p-5 bg-yellow-50/60 backdrop-blur-sm border border-yellow-100 rounded-2xl flex items-start gap-4">
                      <AlertTriangle className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <h4 className="text-yellow-800 font-bold text-sm mb-1">Medical Disclaimer</h4>
                        <p className="text-yellow-700 text-sm leading-relaxed">
                          This analysis is generated by AI and may contain errors. It is for informational purposes only and does not constitute medical advice. Always consult a qualified healthcare professional for diagnosis and treatment.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
    </>
  );
}