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
    <div className="flex h-screen bg-gray-50 font-sans overflow-hidden">
      {/* Sidebar */}
      <div 
        className={`${
          sidebarOpen ? 'w-64 translate-x-0' : 'w-0 -translate-x-full opacity-0'
        } bg-gray-900 text-white transition-all duration-300 flex flex-col flex-shrink-0 absolute md:relative z-20 h-full overflow-hidden`}
      >
        <div className="p-4 border-b border-gray-800">
           <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-teal-400">
            Pharma Intelligence
          </h1>
          <p className="text-xs text-gray-500 mt-1">AI Medication Assistant</p>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
           <button
            onClick={() => setActiveTab('search')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-sm font-medium ${activeTab === 'search' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-400 hover:bg-gray-800 hover:text-white'}`}
          >
            <Search size={18} />
            Medicine Search
          </button>
          <button
            onClick={() => setActiveTab('interactions')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-sm font-medium ${activeTab === 'interactions' ? 'bg-purple-600 text-white shadow-lg' : 'text-gray-400 hover:bg-gray-800 hover:text-white'}`}
          >
            <Activity size={18} />
            Interaction Checker
          </button>
          <button
            onClick={() => setActiveTab('ocr')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-sm font-medium ${activeTab === 'ocr' ? 'bg-teal-600 text-white shadow-lg' : 'text-gray-400 hover:bg-gray-800 hover:text-white'}`}
          >
            <FileText size={18} />
            Prescription OCR
          </button>
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

        {/* Header */}
        <div className="p-4 flex items-center justify-between bg-white border-b border-gray-200 shadow-sm">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
            >
              {sidebarOpen ? <ChevronLeft className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <h2 className="text-lg font-semibold text-gray-800 hidden sm:block">
              {activeTab === 'search' && 'Search Medicines'}
              {activeTab === 'interactions' && 'Check Interactions'}
              {activeTab === 'ocr' && 'Analyze Prescription'}
            </h2>
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
            
            {/* Error Message */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-xl flex items-start gap-3 text-red-700 shadow-sm">
                <AlertTriangle size={20} className="flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* --- SEARCH TAB --- */}
            {activeTab === 'search' && (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="text-center mb-8">
                  <h1 className="text-3xl font-bold text-gray-900 mb-2">Medicine Search</h1>
                  <p className="text-gray-600">Find detailed information about any medication.</p>
                </div>

                <form onSubmit={handleSearch} className="relative max-w-2xl mx-auto">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => {
                        setSearchQuery(e.target.value);
                        fetchSuggestions(e.target.value, { type: 'search' });
                    }}
                    placeholder="Enter medicine name (e.g., Dolo 650, Aspirin)..."
                    className="w-full bg-white border border-gray-300 rounded-xl py-4 pl-12 pr-4 text-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all shadow-sm text-gray-900 placeholder-gray-400"
                    onClick={(e) => e.stopPropagation()}
                  />
                  {activeField?.type === 'search' && suggestions.length > 0 && (
                    <ul className="absolute z-10 w-full bg-white border border-gray-200 rounded-xl mt-2 shadow-xl max-h-60 overflow-y-auto">
                        {suggestions.map((s, i) => (
                            <li 
                                key={i} 
                                onClick={(e) => handleSuggestionClick(e, s)}
                                className="px-4 py-3 hover:bg-blue-50 cursor-pointer text-gray-700 border-b border-gray-100 last:border-0"
                            >
                                {s}
                            </li>
                        ))}
                    </ul>
                  )}
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={24} />
                  <button
                    type="submit"
                    disabled={loading}
                    className="absolute right-2 top-2 bottom-2 bg-blue-600 hover:bg-blue-700 text-white px-6 rounded-lg font-medium transition-colors disabled:opacity-50 shadow-sm"
                  >
                    {loading ? <Loader2 className="animate-spin" /> : 'Search'}
                  </button>
                </form>

                {searchResult && (
                  <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-lg mt-8">
                    <div className="flex items-start justify-between mb-6 border-b border-gray-100 pb-4">
                      <div>
                        <h2 className="text-3xl font-bold text-gray-900">{searchResult.generic_name || searchQuery}</h2>
                        <span className="text-sm text-blue-700 bg-blue-50 px-3 py-1 rounded-full mt-2 inline-block font-medium">Generic Name</span>
                      </div>
                      <div className="bg-blue-100 p-3 rounded-full">
                        <Pill className="text-blue-600" size={32} />
                      </div>
                    </div>
                    
                    <div className="grid md:grid-cols-2 gap-8">
                      <div>
                        <h3 className="text-lg font-semibold text-teal-700 mb-3 flex items-center gap-2">
                          <CheckCircle size={18} /> Use Cases
                        </h3>
                        <ul className="list-disc list-inside text-gray-600 space-y-2 bg-teal-50/50 p-4 rounded-lg border border-teal-100">
                          {searchResult.use_cases?.map((use: string, i: number) => (
                            <li key={i}>{use}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-orange-700 mb-3 flex items-center gap-2">
                          <Activity size={18} /> Side Effects
                        </h3>
                        <ul className="list-disc list-inside text-gray-600 space-y-2 bg-orange-50/50 p-4 rounded-lg border border-orange-100">
                          {searchResult.side_effects?.map((effect: string, i: number) => (
                            <li key={i}>{effect}</li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {searchResult.warnings && searchResult.warnings.length > 0 && (
                      <div className="mt-8 p-5 bg-yellow-50 border border-yellow-200 rounded-xl">
                        <h3 className="text-yellow-800 font-semibold flex items-center gap-2 mb-3">
                          <AlertTriangle size={20} /> Warnings & Precautions
                        </h3>
                        <ul className="list-disc list-inside text-yellow-700 space-y-1">
                          {searchResult.warnings.map((warn: string, i: number) => (
                            <li key={i}>{warn}</li>
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
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="text-center mb-8">
                  <h1 className="text-3xl font-bold text-gray-900 mb-2">Drug Interaction Checker</h1>
                  <p className="text-gray-600">Ensure your combination of medicines is safe.</p>
                </div>

                <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-md">
                  <h2 className="text-xl font-semibold mb-4 text-gray-800">Enter Medicines</h2>
                  <div className="space-y-3">
                    {medicines.map((med, index) => (
                      <div key={index} className="flex gap-2 relative">
                        <input
                          type="text"
                          value={med}
                          onChange={(e) => updateMedicine(index, e.target.value)}
                          placeholder={`Medicine ${index + 1}`}
                          className="flex-1 bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-purple-500 outline-none text-gray-900 placeholder-gray-400 transition-shadow"
                          onClick={(e) => e.stopPropagation()}
                        />
                        {activeField?.type === 'interaction' && activeField.index === index && suggestions.length > 0 && (
                            <ul className="absolute z-10 w-full bg-white border border-gray-200 rounded-xl top-full mt-1 shadow-xl max-h-60 overflow-y-auto left-0">
                                {suggestions.map((s, i) => (
                                    <li 
                                        key={i} 
                                        onClick={(e) => handleSuggestionClick(e, s)}
                                        className="px-4 py-3 hover:bg-purple-50 cursor-pointer text-gray-700 border-b border-gray-100 last:border-0"
                                    >
                                        {s}
                                    </li>
                                ))}
                            </ul>
                        )}
                        {medicines.length > 2 && (
                          <button
                            onClick={() => removeMedicineField(index)}
                            className="p-3 text-red-500 hover:bg-red-50 rounded-lg transition-colors border border-transparent hover:border-red-100"
                          >
                            <X size={20} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                  
                  <div className="flex gap-3 mt-6">
                    <button
                      onClick={addMedicineField}
                      className="flex items-center gap-2 text-sm text-purple-700 hover:text-purple-800 px-4 py-2 rounded-lg hover:bg-purple-50 transition-colors font-medium border border-transparent hover:border-purple-100"
                    >
                      <Plus size={16} /> Add Another
                    </button>
                    <button
                      onClick={handleInteractionCheck}
                      disabled={loading}
                      className="ml-auto bg-purple-600 hover:bg-purple-700 text-white px-8 py-2.5 rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
                    >
                      {loading ? <Loader2 className="animate-spin" size={18} /> : 'Check Safety'}
                    </button>
                  </div>
                </div>

                {interactionResult && (
                  <div className={`border rounded-xl p-6 shadow-lg ${
                    interactionResult.safe_to_combine 
                      ? 'bg-green-50 border-green-200' 
                      : 'bg-red-50 border-red-200'
                  }`}>
                    <div className="flex items-center gap-4 mb-4">
                      {interactionResult.safe_to_combine ? (
                        <div className="bg-green-100 p-3 rounded-full">
                          <CheckCircle className="text-green-600" size={32} />
                        </div>
                      ) : (
                        <div className="bg-red-100 p-3 rounded-full">
                          <AlertTriangle className="text-red-600" size={32} />
                        </div>
                      )}
                      <div>
                        <h3 className={`text-2xl font-bold ${
                          interactionResult.safe_to_combine ? 'text-green-800' : 'text-red-800'
                        }`}>
                          {interactionResult.safe_to_combine ? 'Safe to Combine' : 'Potential Interactions Found'}
                        </h3>
                        <p className="text-gray-700 mt-1">{interactionResult.recommendation}</p>
                      </div>
                    </div>

                    {interactionResult.interactions && interactionResult.interactions.length > 0 && (
                      <div className="space-y-3 mt-6">
                        {interactionResult.interactions.map((inter: any, i: number) => (
                          <div key={i} className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                            <div className="flex justify-between items-start mb-2">
                              <span className="font-bold text-gray-900 text-lg">
                                {inter.medicine_a} + {inter.medicine_b}
                              </span>
                              <span className={`text-xs px-3 py-1 rounded-full uppercase font-bold tracking-wide ${
                                inter.severity === 'High' ? 'bg-red-100 text-red-700' : 
                                inter.severity === 'Medium' ? 'bg-orange-100 text-orange-700' : 
                                'bg-yellow-100 text-yellow-700'
                              }`}>
                                {inter.severity} Risk
                              </span>
                            </div>
                            <p className="text-gray-600 text-sm leading-relaxed">{inter.description}</p>
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
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="text-center mb-8">
                  <h1 className="text-3xl font-bold text-gray-900 mb-2">Prescription Analyzer</h1>
                  <p className="text-gray-600">Upload a prescription to extract medicines and instructions.</p>
                </div>

                <div className="bg-white border border-gray-200 rounded-xl p-10 text-center shadow-md">
                  <div className="w-20 h-20 bg-teal-50 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Upload className="text-teal-600" size={32} />
                  </div>
                  <h2 className="text-xl font-semibold mb-2 text-gray-900">Upload Prescription Image or PDF</h2>
                  <p className="text-gray-500 mb-8 max-w-md mx-auto">
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
                    className="inline-block bg-teal-600 hover:bg-teal-700 text-white px-8 py-3 rounded-xl font-medium cursor-pointer transition-colors shadow-sm hover:shadow-md"
                  >
                    Select File
                  </label>
                  {selectedFile && (
                    <div className="mt-6 text-teal-700 flex items-center justify-center gap-2 bg-teal-50 py-2 px-4 rounded-lg inline-flex">
                      <FileText size={18} />
                      <span className="font-medium">{selectedFile.name}</span>
                    </div>
                  )}
                  
                  {selectedFile && (
                    <div className="mt-6">
                      <button
                        onClick={handleOcrSubmit}
                        disabled={loading}
                        className="w-full md:w-auto bg-gray-900 hover:bg-gray-800 text-white px-10 py-3 rounded-xl font-medium transition-colors disabled:opacity-50 shadow-lg"
                      >
                        {loading ? <span className="flex items-center gap-2 justify-center"><Loader2 className="animate-spin" size={18}/> Analyzing...</span> : 'Analyze Prescription'}
                      </button>
                    </div>
                  )}
                </div>

                {ocrResult && (
                  <div className="grid md:grid-cols-2 gap-6 mt-8">
                    {/* Extracted Text */}
                    <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm h-full flex flex-col">
                      <h3 className="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
                        <FileText size={18} /> Raw Extracted Text
                      </h3>
                      <div className="bg-gray-50 p-4 rounded-lg text-gray-600 text-sm h-64 overflow-y-auto whitespace-pre-wrap font-mono border border-gray-100 flex-1">
                        {ocrResult.extracted_text}
                      </div>
                    </div>

                    {/* Analysis */}
                    <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm h-full flex flex-col">
                      <h3 className="text-lg font-semibold text-teal-700 mb-4 flex items-center gap-2">
                        <Activity size={18} /> AI Analysis
                      </h3>
                      <div className="space-y-4 flex-1 overflow-y-auto max-h-[500px] pr-2">
                        {ocrResult.analysis?.medicines?.map((med: any, i: number) => (
                          <div key={i} className="border-b border-gray-100 pb-4 last:border-0">
                            <div className="flex justify-between items-baseline">
                              <span className="font-bold text-gray-900 text-lg">{med.name}</span>
                              <span className="text-sm font-medium text-teal-600 bg-teal-50 px-2 py-0.5 rounded">{med.dosage}</span>
                            </div>
                            <p className="text-sm text-gray-600 mt-2 leading-relaxed">{med.explanation}</p>
                            {med.frequency && (
                              <div className="mt-2 flex items-center gap-2">
                                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Frequency:</span>
                                <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded font-medium">
                                  {med.frequency}
                                </span>
                              </div>
                            )}
                          </div>
                        ))}
                        {ocrResult.analysis?.doctor_notes && (
                          <div className="mt-4 pt-4 border-t border-gray-100 bg-yellow-50/50 p-4 rounded-lg">
                            <span className="text-sm font-bold text-gray-700 block mb-1">Doctor's Notes:</span>
                            <p className="text-gray-600 text-sm italic">"{ocrResult.analysis.doctor_notes}"</p>
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
  );
}
