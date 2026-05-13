"use client";

// Import the necessary icons from lucide-react
import { HeartPulse, MessageSquare, HandHeart, Search, Hospital, Upload, Pill } from 'lucide-react';
import Link from 'next/link';

// Main App Component
const App = () => {
    return (
        <>
            <style>{`
                @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;500;600&family=Inter:wght@400;500&display=swap');
                
                body {
                    font-family: 'Inter', sans-serif;
                    background-color: #cbe5ff; /* Matches the light blue theme */
                    color: #1e293b; /* Dark slate text */
                    overflow-x: hidden;
                }
                .font-lora {
                    font-family: 'Lora', serif;
                }
                /* Floating animation for background water-like orbs */
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

            {/* Main container with light blue gradient base */}
            <div className="relative w-full h-screen flex flex-col bg-gradient-to-br from-[#cbe5ff] via-[#dcedff] to-[#e1f0ff] overflow-hidden">
                
                {/* --- BACKGROUND GLOWING ORBS (Light / Water Theme) --- */}
                <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-white/60 rounded-full blur-[100px] animate-float-1 pointer-events-none"></div>
                <div className="absolute top-[20%] right-[-5%] w-[400px] h-[400px] bg-blue-300/30 rounded-full blur-[80px] animate-float-2 pointer-events-none"></div>
                <div className="absolute bottom-[-10%] left-[20%] w-[600px] h-[600px] bg-cyan-200/40 rounded-full blur-[100px] animate-float-3 pointer-events-none"></div>

                {/* Header */}
                <header className="w-full p-4 md:p-6 flex justify-between items-center z-20 shrink-0">
                    {/* Left side icons */}
                    <div className="flex items-center space-x-4">
                        <div className="w-10 h-10 md:w-12 md:h-12 bg-white/60 backdrop-blur-xl border border-white/80 shadow-sm rounded-full flex items-center justify-center">
                            <HeartPulse className="w-6 h-6 text-blue-500" />
                        </div>
                        <span className="font-lora text-xl font-semibold tracking-wide hidden sm:block text-slate-800">HealthyLabs.AI</span>
                    </div>
                    
                    {/* Right side icons and buttons */}
                    <div className="flex items-center space-x-4">
                         
                        <Link href="Login" className="bg-white/60 backdrop-blur-xl border border-white/80 shadow-sm text-slate-700 rounded-full px-6 py-2.5 text-sm font-medium hover:bg-white transition-all cursor-pointer">
                            Login
                        </Link>
                        <Link href="Register" className="hidden sm:block bg-white/60 backdrop-blur-xl border border-white/80 shadow-sm text-slate-700 rounded-full px-6 py-2.5 text-sm font-medium hover:bg-white transition-all cursor-pointer">
                            Register
                        </Link>
                    </div>
                </header>

                {/* Main Content Area */}
                <main className="flex-1 flex flex-col items-center justify-center px-4 z-10">
                    
                    {/* Hero Section */}
                    <div className="text-center mb-8 max-w-4xl mx-auto z-20 relative">
                        <h1 className="font-lora text-2xl sm:text-3xl md:text-4xl font-medium tracking-wide mb-4 leading-tight text-slate-900 drop-shadow-sm">
                            Your Personal <br/>
                            <span className="font-semibold text-blue-600">
                                AI Health Companion
                            </span>
                        </h1>
                        <p className="text-base md:text-lg text-slate-600 font-medium max-w-2xl mx-auto leading-relaxed">
                            Experience the future of healthcare with our comprehensive suite of AI-powered tools designed to keep you healthy and informed.
                        </p>
                    </div>

                    {/* Features Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 w-full max-w-7xl px-4 relative z-20">
                        
                        {/* Feature 1: AI Doctor */}
                        <div className="relative bg-white/40 backdrop-blur-xl border border-white/80 shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] rounded-[1.5rem] p-5 hover:bg-white/60 hover:-translate-y-1 transition-all duration-500 group overflow-hidden">
                            <div className="absolute top-0 left-0 w-full h-1/2 bg-gradient-to-b from-white/40 to-transparent pointer-events-none"></div>
                            <div className="relative z-10">
                                <div className="w-10 h-10 bg-white border border-gray-100 shadow-sm rounded-xl flex items-center justify-center mb-3 group-hover:scale-110 transition-all duration-300">
                                    <MessageSquare className="w-5 h-5 text-blue-500" />
                                </div>
                                <h3 className="text-lg font-semibold mb-2 font-lora text-slate-800">AI Doctor Chat</h3>
                                <p className="text-sm text-slate-600 leading-relaxed font-medium">
                                    Get instant, 24/7 medical advice and symptom checking from our advanced AI health assistant.
                                </p>
                            </div>
                        </div>

                        {/* Feature 2: Hospital Finder */}
                        <div className="relative bg-white/40 backdrop-blur-xl border border-white/80 shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] rounded-[1.5rem] p-5 hover:bg-white/60 hover:-translate-y-1 transition-all duration-500 group overflow-hidden">
                            <div className="absolute top-0 left-0 w-full h-1/2 bg-gradient-to-b from-white/40 to-transparent pointer-events-none"></div>
                            <div className="relative z-10">
                                <div className="w-10 h-10 bg-white border border-gray-100 shadow-sm rounded-xl flex items-center justify-center mb-3 group-hover:scale-110 transition-all duration-300">
                                    <Hospital className="w-5 h-5 text-blue-500" />
                                </div>
                                <h3 className="text-lg font-semibold mb-2 font-lora text-slate-800">Hospital Finder</h3>
                                <p className="text-sm text-slate-600 leading-relaxed font-medium">
                                    Locate nearby hospitals instantly and check real-time bed availability in your city.
                                </p>
                            </div>
                        </div>

                        {/* Feature 3: Report Analysis */}
                        <div className="relative bg-white/40 backdrop-blur-xl border border-white/80 shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] rounded-[1.5rem] p-5 hover:bg-white/60 hover:-translate-y-1 transition-all duration-500 group overflow-hidden">
                            <div className="absolute top-0 left-0 w-full h-1/2 bg-gradient-to-b from-white/40 to-transparent pointer-events-none"></div>
                            <div className="relative z-10">
                                <div className="w-10 h-10 bg-white border border-gray-100 shadow-sm rounded-xl flex items-center justify-center mb-3 group-hover:scale-110 transition-all duration-300">
                                    <Upload className="w-5 h-5 text-blue-500" />
                                </div>
                                <h3 className="text-lg font-semibold mb-2 font-lora text-slate-800">Report Analysis</h3>
                                <p className="text-sm text-slate-600 leading-relaxed font-medium">
                                    Upload your medical scans or lab reports to get simplified, AI-generated summaries and insights.
                                </p>
                            </div>
                        </div>

                        {/* Feature 4: Pharma Guide */}
                        <div className="relative bg-white/40 backdrop-blur-xl border border-white/80 shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] rounded-[1.5rem] p-5 hover:bg-white/60 hover:-translate-y-1 transition-all duration-500 group overflow-hidden">
                            <div className="absolute top-0 left-0 w-full h-1/2 bg-gradient-to-b from-white/40 to-transparent pointer-events-none"></div>
                            <div className="relative z-10">
                                <div className="w-10 h-10 bg-white border border-gray-100 shadow-sm rounded-xl flex items-center justify-center mb-3 group-hover:scale-110 transition-all duration-300">
                                    <Pill className="w-5 h-5 text-blue-500" />
                                </div>
                                <h3 className="text-lg font-semibold mb-2 font-lora text-slate-800">Pharma Guide</h3>
                                <p className="text-sm text-slate-600 leading-relaxed font-medium">
                                    Search for medicines, understand their usage, side effects, and check for potential drug interactions.
                                </p>
                            </div>
                        </div>

                    </div>
                </main>

                {/* Bottom Search Bar / Footer */}
                
            </div>
        </>
    );
};

export default App;