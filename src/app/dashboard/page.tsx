"use client";

import { useState, useEffect } from 'react';
import Link from "next/link";
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import { User as SupabaseUser } from '@supabase/supabase-js';
import { MessageSquare, Hospital, Upload, Pill, Stethoscope, BarChart3, User, LogOut, ChevronDown } from "lucide-react";

export default function HealthyLabsHome() {
  const [user, setUser] = useState<SupabaseUser | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const getUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        setUser(session.user);
      }
    };
    getUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push('/Login');
  };

  const sections = [
    { title: "Your Daily Dr.", icon: <Stethoscope className="h-6 w-6" />, color: "from-pink-400 to-pink-600" },
    { title: "Chat Freely", icon: <MessageSquare className="h-6 w-6" />, color: "from-purple-400 to-pink-500" },
    { title: "Hospitals", icon: <Hospital className="h-6 w-6" />, color: "from-rose-400 to-pink-600", path: "/Hospitals" },
    { title: "Reports", icon: <Upload className="h-6 w-6" />, color: "from-fuchsia-400 to-pink-500" },
    { title: "AI Analyzed Reports", icon: <Upload className="h-6 w-6" />, color: "from-pink-300 to-rose-500" },
    { title: "Pharma Section", icon: <Pill className="h-6 w-6" />, color: "from-purple-300 to-pink-500" },
    { title: "Your Personal Dr.", icon: <User className="h-6 w-6" />, color: "from-pink-500 to-rose-600" },
    { title: "Your Data", icon: <BarChart3 className="h-6 w-6" />, color: "from-pink-400 to-purple-500" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-200 via-purple-200 to-rose-200 flex flex-col items-center p-6 font-sans relative">
      
      {/* Profile Button (Top Right) */}
      <div className="absolute top-6 right-6 z-50">
        <div className="relative">
          <button 
            onClick={() => setMenuOpen(!menuOpen)} 
            className="flex cursor-pointer items-center space-x-2 bg-white/80 backdrop-blur-sm px-3 py-2 rounded-full shadow-sm hover:bg-white transition border border-pink-100"
          >
            <div className="bg-pink-500 rounded-full p-1">
              <User className="w-4 h-4 text-white" />
            </div>
            <span className="text-gray-700 font-medium text-sm hidden sm:block">{user?.email?.split('@')[0] || 'Profile'}</span>
            <ChevronDown className="w-4 h-4 text-gray-500" />
          </button>
          
          {menuOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl py-2 border border-gray-100 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-50 bg-gray-50/50">
                <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Signed in as</p>
                <p className="text-sm font-medium text-gray-900 truncate" title={user?.email}>{user?.email}</p>
              </div>
              <button 
                onClick={handleLogout} 
                className="w-full text-left px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 flex items-center transition-colors"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Hero Section */}
      <div className="text-center mb-10">
        <h1 className="text-5xl font-extrabold text-pink-700 drop-shadow-lg mb-2">HealthyLabs.AI</h1>
        <p className="text-gray-700 text-lg max-w-xl mx-auto">
          Your AI companion for <span className="text-pink-600 font-semibold">mental, physical & emotional health</span>
        </p>
        <div className="mt-6 flex items-center justify-center">
          <input
            type="text"
            placeholder="Worried about your health? Ask me…"
            className="px-4 py-3 w-80 rounded-2xl border text-black border-pink-300 shadow-sm focus:ring-2 focus:ring-pink-400 outline-none"
          />
        </div>
      </div>

      {/* Sections Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 w-full max-w-5xl">
        {sections.map((sec, idx) => {
          const Card = (
            <div
              className={`rounded-3xl p-6 bg-gradient-to-br ${sec.color} text-white shadow-lg hover:scale-105 transform transition cursor-pointer`}
            >
              <div className="flex items-center space-x-3 mb-3">
                {sec.icon}
                <h2 className="text-xl font-semibold">{sec.title}</h2>
              </div>
              <p className="text-sm opacity-90">
                {sec.title === "Your Daily Dr." && "Get instant AI health advice daily."}
                {sec.title === "Chat Freely" && "Talk openly with AI about your health."}
                {sec.title === "Hospitals" && "Find nearby hospitals & availability."}
                {sec.title === "Reports" && "View and manage all medical reports."}
                {sec.title === "AI Analyzed Reports" && "Upload scans, tests & get AI analysis."}
                {sec.title === "Pharma Section" && "Search medicines & nearby pharmacies."}
                {sec.title === "Your Personal Dr." && "Connect with your AI + real doctor."}
                {sec.title === "Your Data" && "Track your weekly health stats & insights."}
              </p>
            </div>
          );

          return sec.path ? (
            <Link key={idx} href={sec.path}>
              {Card}
            </Link>
          ) : (
            <div key={idx}>{Card}</div>
          );
        })}
      </div>

      {/* Footer */}
      <footer className="mt-12 text-center text-gray-600 text-sm">
        <p>
          💖 Stay Healthy. Stay Happy. With{" "}
          <span className="text-pink-600 font-semibold">HealthyLabs.AI</span>
        </p>
        <div className="mt-2 space-x-4">
          <a href="#" className="hover:underline">About</a>
          <a href="#" className="hover:underline">Contact</a>
          <a href="#" className="hover:underline">Privacy Policy</a>
        </div>
      </footer>
    </div>
  );
}
