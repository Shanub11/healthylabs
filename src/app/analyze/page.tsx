'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { supabase } from '@/lib/supabaseClient';
import { Upload, FileText, Activity, AlertTriangle, CheckCircle, Loader2, File as FileIcon, XCircle, Copy, Check, Menu, Plus, MessageSquare, Clock, ChevronLeft, Home } from 'lucide-react';

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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setText('');
      setError('');
    }
  };

  const fetchHistory = async () => {
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      try {
        const response = await axios.get(`${API_URL}/history/${user.id}`);
        setHistory(response.data);
      } catch (error) {
        console.error("Failed to fetch history", error);
      }
    }
  };

  useEffect(() => {
    fetchHistory();
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
  };

  const loadHistoryItem = (item: any) => {
    setResult({
      summary: item.ai_summary,
      confidence: item.confidence
    });
    setText(item.source === 'text' ? item.original_text : '');
    setFile(null);
    if (window.innerWidth < 768) setSidebarOpen(false);
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
    <div className="flex h-screen bg-gray-50 font-sans overflow-hidden">
      {/* Sidebar */}
      <div 
        className={`${
          sidebarOpen ? 'w-64 translate-x-0' : 'w-0 -translate-x-full opacity-0'
        } bg-gray-900 text-white transition-all duration-300 flex flex-col flex-shrink-0 absolute md:relative z-20 h-full overflow-hidden`}
      >
        <div className="p-4">
          <button
            onClick={startNewAnalysis}
            className="w-full flex items-center gap-2 px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-700 transition-colors text-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            New Analysis
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 pb-4">
          <div className="px-2 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
            History
          </div>
          <div className="space-y-1">
            {history.map((item) => (
              <button
                key={item._id}
                onClick={() => loadHistoryItem(item)}
                className="w-full flex items-center gap-3 px-3 py-3 text-sm text-gray-300 hover:bg-gray-800 hover:text-white rounded-lg transition-colors text-left group"
              >
                <MessageSquare className="w-4 h-4 flex-shrink-0" />
                <div className="flex-1 truncate">
                  <span className="block truncate">
                    {new Date(item.created_at).toLocaleDateString()} Report
                  </span>
                  <span className="text-xs text-gray-500 truncate block">
                    {item.original_text?.substring(0, 30)}...
                  </span>
                </div>
              </button>
            ))}
            {history.length === 0 && (
              <div className="px-3 py-4 text-sm text-gray-500 text-center">
                No history yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Mobile Overlay */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/50 z-10 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Header / Toggle */}
        <div className="p-4 flex items-center justify-between bg-white border-b border-gray-200 shadow-sm">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
            >
              {sidebarOpen ? <ChevronLeft className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
          <Link 
            href="/dashboard" 
            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors font-medium"
          >
            <Home className="w-5 h-5" />
            <span>Home</span>
          </Link>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-4xl mx-auto pb-20">
            <div className="text-center mb-10">
              <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight sm:text-5xl mb-2">
                AI Report Analyzer
              </h1>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                Upload your medical reports or paste text to get an instant, easy-to-understand summary powered by AI.
              </p>
            </div>

            <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100">
              {/* Header / Tabs */}
              <div className="flex border-b border-gray-200">
                <button
                  onClick={() => setActiveTab('upload')}
                  className={`flex-1 py-4 text-sm font-medium text-center transition-colors duration-200 flex items-center justify-center gap-2 ${
                    activeTab === 'upload'
                      ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-600'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <Upload className="w-4 h-4" />
                  Upload File
                </button>
                <button
                  onClick={() => setActiveTab('text')}
                  className={`flex-1 py-4 text-sm font-medium text-center transition-colors duration-200 flex items-center justify-center gap-2 ${
                    activeTab === 'text'
                      ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-600'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
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
                      className={`relative border-2 border-dashed rounded-xl p-10 text-center transition-all duration-200 ${
                        dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
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
                        <div className="flex flex-col items-center">
                          <div className="bg-blue-100 p-4 rounded-full mb-3">
                            <FileIcon className="w-8 h-8 text-blue-600" />
                          </div>
                          <p className="text-lg font-medium text-gray-900">{file.name}</p>
                          <p className="text-sm text-gray-500 mb-4">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                          <button 
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              removeFile();
                            }}
                            className="z-10 px-4 py-2 bg-red-50 text-red-600 rounded-lg text-sm font-medium hover:bg-red-100 transition-colors"
                          >
                            Remove File
                          </button>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center pointer-events-none">
                          <div className="bg-gray-100 p-4 rounded-full mb-3">
                            <Upload className="w-8 h-8 text-gray-400" />
                          </div>
                          <p className="text-lg font-medium text-gray-900">Click to upload or drag and drop</p>
                          <p className="text-sm text-gray-500 mt-1">PDF, JPG, PNG (Max 10MB)</p>
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
                        className="w-full p-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow resize-y text-gray-700 leading-relaxed"
                        disabled={loading}
                      />
                    </div>
                  )}

                  {error && (
                    <div className="mt-6 p-4 bg-red-50 border border-red-100 rounded-xl flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                      <p className="text-red-700 text-sm">{error}</p>
                    </div>
                  )}

                  <div className="mt-8 space-y-3">
                    <button
                      type="submit"
                      disabled={loading || (!file && !text)}
                      className={`w-full py-4 px-6 rounded-xl cursor-pointer text-white font-semibold text-lg shadow-lg transition-all duration-200 flex items-center justify-center gap-2 ${
                        (!file && !text)
                          ? 'bg-gray-300 cursor-not-allowed'
                          : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 hover:shadow-xl transform hover:-translate-y-0.5'
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
                        className="w-full py-3 px-6 rounded-xl text-red-600 font-medium text-sm hover:bg-red-50 transition-colors flex items-center justify-center gap-2 border border-transparent hover:border-red-100"
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
              <div className="mt-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100">
                  <div className="bg-gradient-to-r from-green-500 to-emerald-600 p-4 flex items-center justify-between">
                    <h2 className="text-white font-bold text-lg flex items-center gap-2">
                      <CheckCircle className="w-5 h-5" />
                      Analysis Complete
                    </h2>
                    {result.confidence && (
                      <span className="bg-white/20 text-white text-xs font-medium px-3 py-1 rounded-full backdrop-blur-sm">
                        {result.confidence} Confidence
                      </span>
                    )}
                  </div>
                  
                  <div className="p-8">
                    <div className="prose prose-blue max-w-none">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-900 font-bold text-xl m-0">Summary & Findings</h3>
                        <button
                          onClick={handleCopy}
                          className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                        >
                          {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                          {copied ? 'Copied!' : 'Copy'}
                        </button>
                      </div>
                      <div className="bg-gray-50 rounded-xl p-6 border border-gray-100 text-gray-700 leading-relaxed whitespace-pre-wrap">
                        {result.summary}
                      </div>
                    </div>

                    <div className="mt-8 p-4 bg-yellow-50 border border-yellow-100 rounded-xl flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <h4 className="text-yellow-800 font-semibold text-sm mb-1">Medical Disclaimer</h4>
                        <p className="text-yellow-700 text-sm">
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
  );
}