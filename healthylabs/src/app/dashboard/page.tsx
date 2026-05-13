"use client";

import { useState, useEffect } from 'react';
import Link from "next/link";
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import { User as SupabaseUser } from '@supabase/supabase-js';
import { 
  MessageSquare, Hospital, Upload, Pill, 
  User, LogOut, ChevronDown, LayoutDashboard, 
  FileText, Activity, MapPin, Smile, Meh, Frown
} from "lucide-react";

export default function HealthyLabsHome() {
  const [user, setUser] = useState<SupabaseUser | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const getUser = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession();
        if (error) throw error;
        if (session) {
          setUser(session.user);
        }
        setIsOffline(false);
      } catch (error) {
        if (error instanceof Error && (error.message.includes('Failed to fetch') || error.message.includes('fetch failed'))) {
          setIsOffline(true);
        }
        if (error instanceof Error && !error.message.includes('Failed to fetch')) {
          console.error("Error fetching session:", error);
        }
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

  return (
    // Background matching the pastel green/blue/purple gradient
    <div className="min-h-screen bg-gradient-to-br from-[#e2eaff] via-[#d4f0f0] to-[#cbf0d8] flex font-sans relative overflow-hidden text-gray-800">
      
      {/* Decorative background blur elements (mimicking the floating bubbles) */}
      <div className="absolute top-[-10%] right-[-5%] w-[400px] h-[400px] bg-gradient-to-br from-blue-200/40 to-teal-200/40 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-10 left-10 w-[200px] h-[200px] bg-gradient-to-tr from-purple-200/40 to-blue-200/40 rounded-full blur-2xl pointer-events-none"></div>

      {isOffline && (
        <div className="absolute top-0 left-0 w-full bg-red-500 text-white text-center py-2 px-4 z-[60] shadow-md animate-pulse">
          ⚠️ <strong>Connection Error:</strong> Unable to reach Supabase. Please check your internet connection.
        </div>
      )}

      {/* Profile Menu (Top Right) */}
      <div className="absolute top-8 right-8 z-50">
        <div className="relative">
          <button 
            onClick={() => setMenuOpen(!menuOpen)} 
            className="flex cursor-pointer items-center space-x-2 bg-white/40 backdrop-blur-md px-3 py-2 rounded-full shadow-sm hover:bg-white/60 transition border border-white/50"
          >
            <div className="bg-gray-800 rounded-full p-1">
              <User className="w-4 h-4 text-white" />
            </div>
            <span className="text-gray-700 font-medium text-sm hidden sm:block">
              {user?.email?.split('@')[0] || 'Profile'}
            </span>
            <ChevronDown className="w-4 h-4 text-gray-500" />
          </button>
          
          {menuOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-white/90 backdrop-blur-xl rounded-xl shadow-xl py-2 border border-white/50 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100 bg-gray-50/50">
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

      {/* --- SIDEBAR --- */}
      <aside className="w-64 m-6 p-6 rounded-3xl bg-white/40 backdrop-blur-xl border border-white/60 shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] flex flex-col z-10 hidden md:flex">
        <div className="flex items-center space-x-2 mb-10 pl-2">
          <div className="flex space-x-1">
            <div className="w-2 h-2 rounded-full bg-blue-500"></div>
            <div className="w-2 h-2 rounded-full bg-green-400"></div>
          </div>
          <span className="font-bold text-lg text-gray-800 tracking-tight">HealthyLabs.AI</span>
        </div>

        <nav className="flex-1 space-y-2">
          <div className="flex items-center space-x-3 bg-white/60 px-4 py-3 rounded-2xl text-gray-900 font-medium shadow-sm border border-white/50 cursor-pointer">
            <LayoutDashboard className="w-5 h-5 text-gray-600" />
            <span>Dashboard</span>
          </div>
          <Link href="/chat">
            <div className="flex items-center space-x-3 hover:bg-white/30 px-4 py-3 rounded-2xl text-gray-600 font-medium transition cursor-pointer">
              <MessageSquare className="w-5 h-5" />
              <span>Chat</span>
            </div>
          </Link>  
          <Link href="/Hospitals">
            <div className="flex items-center space-x-3 hover:bg-white/30 px-4 py-3 rounded-2xl text-gray-600 font-medium transition cursor-pointer">
              <Hospital className="w-5 h-5" />
              <span>Hospitals</span>
            </div>
          </Link>
          <Link href="/analyze">
            <div className="flex items-center space-x-3 hover:bg-white/30 px-4 py-3 rounded-2xl text-gray-600 font-medium transition cursor-pointer">
              <FileText className="w-5 h-5" />
              <span>Reports</span>
            </div>
          </Link>
          <Link href="/pharma">
            <div className="flex items-center space-x-3 hover:bg-white/30 px-4 py-3 rounded-2xl text-gray-600 font-medium transition cursor-pointer">
              <Pill className="w-5 h-5" />
              <span>Pharma</span>
            </div>
          </Link>
          <Link href="/profile">
            <div className="flex items-center space-x-3 hover:bg-white/30 px-4 py-3 rounded-2xl text-gray-600 font-medium transition cursor-pointer">
              <User className="w-5 h-5" />
              <span>Profile</span>
            </div>
          </Link>
        </nav>
      </aside>

      {/* --- MAIN CONTENT --- */}
      <main className="flex-1 m-6 ml-0 flex flex-col space-y-6 z-10 pt-16 md:pt-0">
        
        {/* Greeting Banner */}
        <div className="rounded-3xl p-8 bg-white/40 backdrop-blur-xl border border-white/60 shadow-[0_8px_32px_0_rgba(31,38,135,0.05)]">
          <h1 className="text-3xl font-bold text-gray-900 mb-1">
            Hi, {user?.email?.split('@')[0] || 'Alex'}.
          </h1>
          <p className="text-xl text-gray-800 font-medium mb-6">How are you feeling today?</p>
          
          <div className="flex flex-wrap gap-3">
            <button className="flex items-center space-x-2 bg-white/70 hover:bg-white transition px-4 py-2 rounded-full shadow-sm border border-white text-sm font-medium">
              <Smile className="w-4 h-4 text-yellow-500" />
              <span>Great</span>
            </button>
            <button className="flex items-center space-x-2 bg-white/70 hover:bg-white transition px-4 py-2 rounded-full shadow-sm border border-white text-sm font-medium">
              <Meh className="w-4 h-4 text-orange-400" />
              <span>Good</span>
            </button>
            <button className="flex items-center space-x-2 bg-white/70 hover:bg-white transition px-4 py-2 rounded-full shadow-sm border border-white text-sm font-medium">
              <Frown className="w-4 h-4 text-blue-400" />
              <span>Less</span>
            </button>
          </div>
        </div>

        {/* 2x2 Grid Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chat */}
          <Link href="/chat">
            <div className="rounded-3xl p-6 bg-white/40 backdrop-blur-xl border border-white/60 shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] hover:bg-white/50 transition cursor-pointer flex items-center space-x-5">
              <div className="p-4 bg-white rounded-2xl shadow-sm border border-gray-100">
                <MessageSquare className="w-6 h-6 text-gray-700" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">Chat with AI Dr.</h3>
                <p className="text-sm text-gray-600 leading-tight">Get instant AI health advice daily.</p>
              </div>
            </div>
          </Link>
          {/* Hospitals */}
          <Link href="/Hospitals">
            <div className="rounded-3xl p-6 bg-white/40 backdrop-blur-xl border border-white/60 shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] hover:bg-white/50 transition cursor-pointer flex items-center space-x-5 h-full">
              <div className="p-4 bg-white rounded-2xl shadow-sm border border-gray-100">
                <MapPin className="w-6 h-6 text-gray-700" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">Find Hospitals Near Me</h3>
                <p className="text-sm text-gray-600 leading-tight">Find nearby hospitals & bed availability.</p>
              </div>
            </div>
          </Link>

          {/* Analyze */}
          <Link href="/analyze">
            <div className="rounded-3xl p-6 bg-white/40 backdrop-blur-xl border border-white/60 shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] hover:bg-white/50 transition cursor-pointer flex items-center space-x-5 h-full">
              <div className="p-4 bg-white rounded-2xl shadow-sm border border-gray-100">
                <Upload className="w-6 h-6 text-gray-700" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">Analyze Reports</h3>
                <p className="text-sm text-gray-600 leading-tight">Upload scans, tests & get AI analysis.</p>
              </div>
            </div>
          </Link>

          {/* Pharma */}
          <Link href="/pharma">
            <div className="rounded-3xl p-6 bg-white/40 backdrop-blur-xl border border-white/60 shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] hover:bg-white/50 transition cursor-pointer flex items-center space-x-5 h-full">
              <div className="p-4 bg-white rounded-2xl shadow-sm border border-gray-100">
                <Pill className="w-6 h-6 text-gray-700" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">Pharma & Meds</h3>
                <p className="text-sm text-gray-600 leading-tight">Search medicines & drug interaction</p>
              </div>
            </div>
          </Link>
        </div>

      </main>
    </div>
  );
}