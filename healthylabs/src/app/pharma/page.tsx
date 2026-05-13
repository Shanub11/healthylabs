'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Search, AlertTriangle, FileText, Upload, Loader2, Pill, Activity, Plus, X, CheckCircle, Home, Menu, ChevronLeft } from 'lucide-react';
import Link from 'next/link';
import axios from 'axios';

// Default to localhost:8001 where pharmacy_main.py runs
const API_URL = process.env.NEXT_PUBLIC_PHARMA_API_URL || 'http://localhost:8001';

export default function PharmaPage() {
  const [activeTab, setActiveTab] = useState<'search' | 'interactions' | 'ocr'>('search');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // --- Search State ---
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResult, setSearchResult] = useState<any>(null);

  // --- Interactions State ---
  const [medicines, setMedicines] = useState<string[]>(['', '']);
  const [interactionResult, setInteractionResult] = useState<any>(null);

  // --- OCR State ---
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [ocrResult, setOcrResult] = useState<any>(null);

  // --- Autocomplete State ---
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [activeField, setActiveField] = useState<{ type: 'search' | 'interaction', index?: number } | null>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Close suggestions on click outside
  useEffect(() => {
    const handleClick = () => setSuggestions([]);
    window.addEventListener('click', handleClick);
    return () => window.removeEventListener('click', handleClick);
  }, []);

  const fetchSuggestions = (query: string, field: { type: 'search' | 'interaction', index?: number }) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setActiveField(field);
    
    if (!query || query.length < 1) {
      setSuggestions([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      try {
        const res = await axios.get(`${API_URL}/medicine/autocomplete`, { params: { query } });
        if (res.data.suggestions) {
            setSuggestions(res.data.suggestions);
        }
      } catch (err) {
        console.error("Autocomplete error", err);
      }
    }, 100);
  };

  // --- Handlers ---

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setLoading(true);
    setError('');
    setSearchResult(null);
    try {
      const res = await axios.get(`${API_URL}/medicine/search`, { params: { query: searchQuery } });
      setSearchResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch medicine details.');
    } finally {
      setLoading(false);
    }
  };

  const handleInteractionCheck = async () => {
    const validMeds = medicines.filter(m => m.trim() !== '');
    if (validMeds.length < 2) {
      setError('Please enter at least two medicines to check interactions.');
      return;
    }
    setLoading(true);
    setError('');
    setInteractionResult(null);
    try {
      const res = await axios.post(`${API_URL}/medicine/interactions`, { medicines: validMeds });
      setInteractionResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to check interactions.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleOcrSubmit = async () => {
    if (!selectedFile) {
      setError('Please select a file first.');
      return;
    }
    setLoading(true);
    setError('');
    setOcrResult(null);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await axios.post(`${API_URL}/medicine/ocr`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setOcrResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to analyze prescription.');
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestionClick = (e: React.MouseEvent, val: string) => {
    e.stopPropagation(); // Prevent window click listener from clearing immediately
    if (activeField?.type === 'search') {
        setSearchQuery(val);
    } else if (activeField?.type === 'interaction' && activeField.index !== undefined) {
        updateMedicine(activeField.index, val);
    }
    setSuggestions([]);
  };

  const updateMedicine = (index: number, value: string) => {
    const newMeds = [...medicines];
    newMeds[index] = value;
    setMedicines(newMeds);
    fetchSuggestions(value, { type: 'interaction', index });
  };

  const addMedicineField = () => setMedicines([...medicines, '']);
  const removeMedicineField = (index: number) => {
    if (medicines.length > 2) {
      const newMeds = medicines.filter((_, i) => i !== index);
      setMedicines(newMeds);
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
          
          /* Custom scrollbar for glassmorphism */
          .custom-scrollbar::-webkit-scrollbar {
            width: 6px;
          }
          .custom-scrollbar::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
          }
          .custom-scrollbar::-webkit-scrollbar-thumb {
            background: rgba(156, 163, 175, 0.5);
            border-radius: 10px;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: rgba(107, 114, 128, 0.8);
          }
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
        <div className="p-6 border-b border-white/50">
           <h1 className="text-2xl font-lora font-bold text-slate-800 tracking-tight">
            Pharma <span className="text-blue-600">Intel</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1 font-medium">AI Medication Assistant</p>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
           <button
            onClick={() => setActiveTab('search')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-sm font-semibold ${activeTab === 'search' ? 'bg-white/60 text-blue-600 shadow-sm border border-white/60' : 'text-slate-600 hover:bg-white/40 hover:text-slate-900 border border-transparent'}`}
          >
            <Search size={18} />
            Medicine Search
          </button>
          <button
            onClick={() => setActiveTab('interactions')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-sm font-semibold ${activeTab === 'interactions' ? 'bg-white/60 text-purple-600 shadow-sm border border-white/60' : 'text-slate-600 hover:bg-white/40 hover:text-slate-900 border border-transparent'}`}
          >
            <Activity size={18} />
            Interaction Checker
          </button>
          <button
            onClick={() => setActiveTab('ocr')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-sm font-semibold ${activeTab === 'ocr' ? 'bg-white/60 text-teal-600 shadow-sm border border-white/60' : 'text-slate-600 hover:bg-white/40 hover:text-slate-900 border border-transparent'}`}
          >
            <FileText size={18} />
            Prescription OCR
          </button>
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

        {/* Header */}
        <div className="p-4 flex items-center justify-between bg-white/40 backdrop-blur-md border-b border-white/60 shadow-sm">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-white/60 rounded-xl transition-colors text-slate-700"
            >
              {sidebarOpen ? <ChevronLeft className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <h2 className="text-lg font-semibold text-slate-800 hidden sm:block font-lora">
              {activeTab === 'search' && 'Search Medicines'}
              {activeTab === 'interactions' && 'Check Interactions'}
              {activeTab === 'ocr' && 'Analyze Prescription'}
            </h2>
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
          <div className="max-w-5xl mx-auto pb-20">
            
            {/* Error Message */}
            {error && (
              <div className="mb-6 p-4 bg-red-50/80 backdrop-blur-sm border border-red-100 rounded-2xl flex items-start gap-3 text-red-700 shadow-sm animate-in slide-in-from-top-2">
                <AlertTriangle size={20} className="flex-shrink-0 mt-0.5" />
                <span className="font-medium">{error}</span>
              </div>
            )}

            {/* --- SEARCH TAB --- */}
            {activeTab === 'search' && (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="text-center mb-10">
                  <h1 className="text-4xl font-lora font-bold text-slate-800 mb-3">Medicine <span className="text-blue-600">Search</span></h1>
                  <p className="text-slate-600 font-medium">Find detailed information about any medication.</p>
                </div>

                <form onSubmit={handleSearch} className="relative max-w-3xl mx-auto">
                  <div className="relative group">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => {
                            setSearchQuery(e.target.value);
                            fetchSuggestions(e.target.value, { type: 'search' });
                        }}
                        placeholder="Enter medicine name (e.g., Dolo 650, Aspirin)..."
                        className="w-full bg-white/50 backdrop-blur-sm border border-white/60 rounded-2xl py-5 pl-14 pr-32 text-lg focus:ring-2 focus:ring-blue-400 focus:outline-none transition-all shadow-sm hover:shadow-md text-slate-800 placeholder-slate-400"
                        onClick={(e) => e.stopPropagation()}
                    />
                    <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-hover:text-blue-500 transition-colors" size={24} />
                    <button
                        type="submit"
                        disabled={loading}
                        className="absolute right-3 top-3 bottom-3 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white px-6 rounded-xl font-medium transition-all disabled:opacity-70 shadow-md hover:shadow-lg transform hover:scale-[1.02]"
                    >
                        {loading ? <Loader2 className="animate-spin" /> : 'Search'}
                    </button>
                  </div>
                  {activeField?.type === 'search' && suggestions.length > 0 && (
                    <ul className="absolute z-20 w-full bg-white/90 backdrop-blur-xl border border-white/60 rounded-2xl mt-2 shadow-xl max-h-60 overflow-y-auto custom-scrollbar">
                        {suggestions.map((s, i) => (
                            <li 
                                key={i} 
                                onClick={(e) => handleSuggestionClick(e, s)}
                                className="px-5 py-3 hover:bg-blue-50/80 cursor-pointer text-slate-700 border-b border-white/50 last:border-0 font-medium transition-colors"
                            >
                                {s}
                            </li>
                        ))}
                    </ul>
                  )}
                </form>

                {searchResult && (
                  <div className="bg-white/60 backdrop-blur-xl border border-white/80 rounded-[2rem] p-8 shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] mt-8 animate-in fade-in zoom-in-95 duration-500">
                    <div className="flex items-start justify-between mb-8 border-b border-white/50 pb-6">
                      <div>
                        <h2 className="text-3xl font-lora font-bold text-slate-800">{searchResult.generic_name || searchQuery}</h2>
                        <span className="text-sm text-blue-700 bg-blue-100/50 px-4 py-1.5 rounded-full mt-3 inline-block font-semibold border border-blue-200/50">Generic Name</span>
                      </div>
                      <div className="bg-blue-100/80 p-4 rounded-full shadow-sm">
                        <Pill className="text-blue-600" size={32} />
                      </div>
                    </div>
                    
                    <div className="grid md:grid-cols-2 gap-8">
                      <div className="bg-teal-50/40 rounded-3xl p-6 border border-teal-100/60">
                        <h3 className="text-lg font-bold text-teal-800 mb-4 flex items-center gap-2">
                          <CheckCircle size={20} className="text-teal-600" /> Use Cases
                        </h3>
                        <ul className="space-y-3">
                          {searchResult.use_cases?.map((use: string, i: number) => (
                            <li key={i} className="flex items-start gap-2 text-slate-700 font-medium">
                                <span className="w-1.5 h-1.5 bg-teal-400 rounded-full mt-2 flex-shrink-0"></span>
                                {use}
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div className="bg-orange-50/40 rounded-3xl p-6 border border-orange-100/60">
                        <h3 className="text-lg font-bold text-orange-800 mb-4 flex items-center gap-2">
                          <Activity size={20} className="text-orange-600" /> Side Effects
                        </h3>
                        <ul className="space-y-3">
                          {searchResult.side_effects?.map((effect: string, i: number) => (
                            <li key={i} className="flex items-start gap-2 text-slate-700 font-medium">
                                <span className="w-1.5 h-1.5 bg-orange-400 rounded-full mt-2 flex-shrink-0"></span>
                                {effect}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {searchResult.warnings && searchResult.warnings.length > 0 && (
                      <div className="mt-8 p-6 bg-yellow-50/60 border border-yellow-200/60 rounded-3xl">
                        <h3 className="text-yellow-800 font-bold flex items-center gap-2 mb-4">
                          <AlertTriangle size={22} className="text-yellow-600" /> Warnings & Precautions
                        </h3>
                        <ul className="space-y-2">
                          {searchResult.warnings.map((warn: string, i: number) => (
                            <li key={i} className="flex items-start gap-2 text-yellow-900/80 font-medium">
                                <span className="w-1.5 h-1.5 bg-yellow-400 rounded-full mt-2 flex-shrink-0"></span>
                                {warn}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* --- INTERACTIONS TAB --- */}
            {activeTab === 'interactions' && (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="text-center mb-10">
                  <h1 className="text-4xl font-lora font-bold text-slate-800 mb-3">Interaction <span className="text-purple-600">Checker</span></h1>
                  <p className="text-slate-600 font-medium">Ensure your combination of medicines is safe.</p>
                </div>

                <div className="bg-white/60 backdrop-blur-xl border border-white/80 rounded-[2rem] p-8 shadow-[0_8px_32px_0_rgba(31,38,135,0.05)]">
                  <h2 className="text-xl font-bold mb-6 text-slate-800 flex items-center gap-2">
                    <Pill className="w-5 h-5 text-purple-500" /> Enter Medicines
                  </h2>
                  <div className="space-y-4">
                    {medicines.map((med, index) => (
                      <div key={index} className="flex gap-3 relative group">
                        <div className="flex-1 relative">
                            <input
                            type="text"
                            value={med}
                            onChange={(e) => updateMedicine(index, e.target.value)}
                            placeholder={`Medicine ${index + 1}`}
                            className="w-full bg-white/50 backdrop-blur-sm border border-white/60 rounded-xl px-5 py-4 focus:ring-2 focus:ring-purple-400 focus:outline-none text-slate-800 placeholder-slate-400 transition-all shadow-inner"
                            onClick={(e) => e.stopPropagation()}
                            />
                            {activeField?.type === 'interaction' && activeField.index === index && suggestions.length > 0 && (
                                <ul className="absolute z-20 w-full bg-white/90 backdrop-blur-xl border border-white/60 rounded-xl top-full mt-2 shadow-xl max-h-60 overflow-y-auto custom-scrollbar">
                                    {suggestions.map((s, i) => (
                                        <li 
                                            key={i} 
                                            onClick={(e) => handleSuggestionClick(e, s)}
                                            className="px-5 py-3 hover:bg-purple-50/80 cursor-pointer text-slate-700 border-b border-white/50 last:border-0 font-medium"
                                        >
                                            {s}
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                        {medicines.length > 2 && (
                          <button
                            onClick={() => removeMedicineField(index)}
                            className="p-4 text-red-500 hover:bg-red-50/80 rounded-xl transition-colors border border-red-100/50 hover:border-red-200 shadow-sm"
                          >
                            <X size={20} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                  
                  <div className="flex flex-col sm:flex-row gap-4 mt-8">
                    <button
                      onClick={addMedicineField}
                      className="flex items-center justify-center gap-2 text-sm text-purple-700 hover:text-purple-800 px-6 py-3 rounded-xl hover:bg-purple-50/80 transition-all font-semibold border border-purple-100/50 hover:border-purple-200 shadow-sm"
                    >
                      <Plus size={18} /> Add Another
                    </button>
                    <button
                      onClick={handleInteractionCheck}
                      disabled={loading}
                      className="sm:ml-auto bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white px-8 py-3 rounded-xl font-bold text-lg transition-all disabled:opacity-70 flex items-center justify-center gap-2 shadow-lg hover:shadow-xl transform hover:scale-[1.02]"
                    >
                      {loading ? <Loader2 className="animate-spin" size={20} /> : 'Check Safety'}
                    </button>
                  </div>
                </div>

                {interactionResult && (
                  <div className={`border rounded-[2rem] p-8 shadow-lg backdrop-blur-xl animate-in fade-in slide-in-from-bottom-4 duration-500 ${
                    interactionResult.safe_to_combine 
                      ? 'bg-green-50/60 border-green-200/60' 
                      : 'bg-red-50/60 border-red-200/60'
                  }`}>
                    <div className="flex items-start gap-5 mb-6">
                      {interactionResult.safe_to_combine ? (
                        <div className="bg-green-100 p-4 rounded-full shadow-sm flex-shrink-0">
                          <CheckCircle className="text-green-600" size={32} />
                        </div>
                      ) : (
                        <div className="bg-red-100 p-4 rounded-full shadow-sm flex-shrink-0">
                          <AlertTriangle className="text-red-600" size={32} />
                        </div>
                      )}
                      <div>
                        <h3 className={`text-2xl font-bold ${
                          interactionResult.safe_to_combine ? 'text-green-800' : 'text-red-800'
                        }`}>
                          {interactionResult.safe_to_combine ? 'Safe to Combine' : 'Potential Interactions Found'}
                        </h3>
                        <p className="text-slate-700 mt-2 font-medium leading-relaxed">{interactionResult.recommendation}</p>
                      </div>
                    </div>

                    {interactionResult.interactions && interactionResult.interactions.length > 0 && (
                      <div className="space-y-4 mt-8">
                        {interactionResult.interactions.map((inter: any, i: number) => (
                          <div key={i} className="bg-white/70 backdrop-blur-sm p-6 rounded-2xl border border-white/60 shadow-sm hover:shadow-md transition-all">
                            <div className="flex justify-between items-start mb-3">
                              <span className="font-bold text-slate-800 text-lg">
                                {inter.medicine_a} + {inter.medicine_b}
                              </span>
                              <span className={`text-xs px-3 py-1.5 rounded-full uppercase font-bold tracking-wide shadow-sm ${
                                inter.severity === 'High' ? 'bg-red-100 text-red-700' : 
                                inter.severity === 'Medium' ? 'bg-orange-100 text-orange-700' : 
                                'bg-yellow-100 text-yellow-700'
                              }`}>
                                {inter.severity} Risk
                              </span>
                            </div>
                            <p className="text-slate-600 text-sm leading-relaxed font-medium">{inter.description}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* --- OCR TAB --- */}
            {activeTab === 'ocr' && (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="text-center mb-10">
                  <h1 className="text-4xl font-lora font-bold text-slate-800 mb-3">Prescription <span className="text-teal-600">Analyzer</span></h1>
                  <p className="text-slate-600 font-medium">Upload a prescription to extract medicines and instructions.</p>
                </div>

                <div className="bg-white/60 backdrop-blur-xl border border-white/80 rounded-[2rem] p-12 text-center shadow-[0_8px_32px_0_rgba(31,38,135,0.05)]">
                  <div className="w-24 h-24 bg-teal-50 rounded-full flex items-center justify-center mx-auto mb-6 shadow-inner">
                    <Upload className="text-teal-600" size={40} />
                  </div>
                  <h2 className="text-2xl font-bold mb-3 text-slate-800">Upload Prescription Image or PDF</h2>
                  <p className="text-slate-500 mb-10 max-w-md mx-auto font-medium">
                    Our AI will scan the document to identify medicines, dosages, and doctor's notes.
                  </p>
                  
                  <input
                    type="file"
                    id="file-upload"
                    className="hidden"
                    accept="image/*,.pdf"
                    onChange={handleFileUpload}
                  />
                  <label
                    htmlFor="file-upload"
                    className="inline-block bg-gradient-to-r from-teal-500 to-emerald-600 hover:from-teal-600 hover:to-emerald-700 text-white px-10 py-4 rounded-2xl font-bold text-lg cursor-pointer transition-all shadow-lg hover:shadow-xl transform hover:scale-[1.02]"
                  >
                    Select File
                  </label>
                  {selectedFile && (
                    <div className="mt-8 text-teal-800 flex items-center justify-center gap-3 bg-teal-50/80 py-3 px-6 rounded-xl inline-flex border border-teal-100 shadow-sm">
                      <FileText size={20} />
                      <span className="font-semibold">{selectedFile.name}</span>
                    </div>
                  )}
                  
                  {selectedFile && (
                    <div className="mt-8">
                      <button
                        onClick={handleOcrSubmit}
                        disabled={loading}
                        className="w-full md:w-auto bg-slate-800 hover:bg-slate-900 text-white px-12 py-4 rounded-2xl font-bold text-lg transition-all disabled:opacity-70 shadow-lg hover:shadow-xl transform hover:scale-[1.02]"
                      >
                        {loading ? <span className="flex items-center gap-3 justify-center"><Loader2 className="animate-spin" size={20}/> Analyzing...</span> : 'Analyze Prescription'}
                      </button>
                    </div>
                  )}
                </div>

                {ocrResult && (
                  <div className="grid md:grid-cols-2 gap-8 mt-10">
                    {/* Extracted Text */}
                    <div className="bg-white/60 backdrop-blur-xl border border-white/80 rounded-[2rem] p-8 shadow-sm h-full flex flex-col">
                      <h3 className="text-xl font-bold text-slate-700 mb-6 flex items-center gap-3">
                        <div className="bg-slate-100 p-2 rounded-lg">
                            <FileText size={20} className="text-slate-600" />
                        </div>
                        Raw Extracted Text
                      </h3>
                      <div className="bg-white/50 p-6 rounded-2xl text-slate-600 text-sm h-80 overflow-y-auto whitespace-pre-wrap font-mono border border-white/60 flex-1 shadow-inner custom-scrollbar">
                        {ocrResult.extracted_text}
                      </div>
                    </div>

                    {/* Analysis */}
                    <div className="bg-white/60 backdrop-blur-xl border border-white/80 rounded-[2rem] p-8 shadow-sm h-full flex flex-col">
                      <h3 className="text-xl font-bold text-teal-800 mb-6 flex items-center gap-3">
                        <div className="bg-teal-100 p-2 rounded-lg">
                            <Activity size={20} className="text-teal-600" />
                        </div>
                        AI Analysis
                      </h3>
                      <div className="space-y-4 flex-1 overflow-y-auto max-h-[500px] pr-2 custom-scrollbar">
                        {ocrResult.analysis?.medicines?.map((med: any, i: number) => (
                          <div key={i} className="bg-white/40 border border-white/60 rounded-2xl p-5 shadow-sm hover:bg-white/60 transition-colors">
                            <div className="flex justify-between items-baseline mb-2">
                              <span className="font-bold text-slate-800 text-lg">{med.name}</span>
                              <span className="text-xs font-bold text-teal-700 bg-teal-100/60 px-3 py-1 rounded-full border border-teal-200/50">{med.dosage}</span>
                            </div>
                            <p className="text-sm text-slate-600 mt-2 leading-relaxed font-medium">{med.explanation}</p>
                            {med.frequency && (
                              <div className="mt-3 flex items-center gap-2">
                                <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Frequency:</span>
                                <span className="text-xs bg-slate-100 text-slate-700 px-3 py-1 rounded-lg font-semibold border border-slate-200">
                                  {med.frequency}
                                </span>
                              </div>
                            )}
                          </div>
                        ))}
                        {ocrResult.analysis?.doctor_notes && (
                          <div className="mt-6 pt-6 border-t border-white/50 bg-yellow-50/40 p-5 rounded-2xl border border-yellow-100/50">
                            <span className="text-sm font-bold text-yellow-800 block mb-2">Doctor's Notes:</span>
                            <p className="text-slate-600 text-sm italic font-medium">"{ocrResult.analysis.doctor_notes}"</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

          </div>
        </div>
      </div>
    </div>
    </>
  );
}
