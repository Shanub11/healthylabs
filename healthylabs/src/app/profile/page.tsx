'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useRouter } from 'next/navigation';
import { 
  Home, User as UserIcon, Activity, Pill, Clock, 
  AlertTriangle, Scale, Ruler, Cigarette, HeartPulse, ShieldCheck
} from 'lucide-react';
import Link from 'next/link';
import { User } from '@supabase/supabase-js';

const ProfilePage = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  const [formData, setFormData] = useState({
    full_name: '',
    age: '',
    gender: '',
    height: '',
    weight: '',
    conditions: '',
    medications: '',
    allergies: '',
    lifestyle: '',
    family_history: ''
  });

  const router = useRouter();

  useEffect(() => {
    const fetchUserAndProfile = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        router.push('/login');
        return;
      }
      setUser(user);

      const { data } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', user.id)
        .single();

      if (data) {
        setFormData({
          full_name: data.full_name || data.name || '',
          age: data.age || '',
          gender: data.gender || '',
          height: data.height || '',
          weight: data.weight || '',
          conditions: data.conditions || '',
          medications: data.medications || '',
          allergies: data.allergies || '',
          lifestyle: data.lifestyle || '',
          family_history: data.family_history || ''
        });
      }
      setLoading(false);
    };

    fetchUserAndProfile();
  }, [router]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user?.id) return;

    setSaving(true);

    const payload = {
      id: user.id,
      full_name: formData.full_name,
      age: formData.age ? parseInt(formData.age.toString(), 10) : null,
      gender: formData.gender,
      height: formData.height ? parseFloat(formData.height.toString()) : null,
      weight: formData.weight ? parseFloat(formData.weight.toString()) : null,
      conditions: formData.conditions,
      medications: formData.medications,
      allergies: formData.allergies,
      lifestyle: formData.lifestyle,
      family_history: formData.family_history,
      updated_at: new Date(),
    };

    const { error } = await supabase.from('profiles').upsert(payload);

    if (error) {
      alert('Error updating profile: ' + error.message);
    } else {
      alert('Medical profile updated successfully!');
    }
    setSaving(false);
  };

  const inputClass = "w-full bg-white/50 backdrop-blur-sm border border-white/80 shadow-sm rounded-2xl px-4 py-3 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white transition-all";
  const iconInputClass = "w-full bg-white/50 backdrop-blur-sm border border-white/80 shadow-sm rounded-2xl pl-12 pr-4 py-3 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white transition-all";

  if (loading) return <div className="min-h-screen flex items-center justify-center font-sans text-slate-500">Loading your health profile...</div>;

  return (
    <>
      <style>{`
        @keyframes float-slow {
            0% { transform: translate(0px, 0px) scale(1); }
            33% { transform: translate(30px, -50px) scale(1.1); }
            66% { transform: translate(-20px, 20px) scale(0.9); }
            100% { transform: translate(0px, 0px) scale(1); }
        }
        .animate-float-1 { animation: float-slow 8s ease-in-out infinite; }
        .animate-float-2 { animation: float-slow 10s ease-in-out infinite reverse; }
      `}</style>

      {/* Main Wrapper: Removed overflow-hidden and added min-h-screen */}
      <div className="relative min-h-screen bg-gradient-to-br from-[#cbe5ff] via-[#dcedff] to-[#e1f0ff] font-sans flex flex-col items-center py-12 px-4 sm:px-8">
        
        {/* Background Decorative Elements: Changed to fixed so they don't cause extra scrolling */}
        <div className="fixed top-[-5%] left-[-5%] w-[400px] h-[400px] bg-white/60 rounded-full blur-[100px] animate-float-1 pointer-events-none z-0"></div>
        <div className="fixed bottom-[-10%] right-[-5%] w-[500px] h-[500px] bg-blue-300/30 rounded-full blur-[80px] animate-float-2 pointer-events-none z-0"></div>

        {/* Main Card */}
        <div className="relative w-full max-w-3xl bg-white/40 backdrop-blur-xl border border-white/80 shadow-[0_8px_32px_0_rgba(31,38,135,0.07)] rounded-[2.5rem] p-6 sm:p-12 z-10">
          
          <Link href="/dashboard" className="absolute top-6 left-6">
            <div className="w-10 h-10 bg-white/60 hover:bg-white backdrop-blur-md border border-white/80 shadow-sm rounded-full flex items-center justify-center transition-all cursor-pointer group">
              <Home className="w-5 h-5 text-blue-500 group-hover:scale-110 transition-transform" />
            </div>
          </Link>

          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-10 pt-4">
              <div className="w-20 h-20 bg-white border border-gray-100 shadow-sm rounded-full flex items-center justify-center mx-auto mb-4">
                <ShieldCheck className="w-10 h-10 text-blue-400" />
              </div>
              <h1 className="text-3xl font-bold text-slate-800">Medical Profile</h1>
              <p className="text-slate-500 font-medium mt-2">Personalized data for precision AI health insights</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-8">
              
              {/* SECTION: Basic Information */}
              <div className="space-y-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-blue-600 ml-1">Basic Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="relative md:col-span-2">
                    <label className="block text-xs font-bold text-slate-600 mb-1 ml-1">FULL NAME</label>
                    <UserIcon className="absolute left-4 top-9 w-5 h-5 text-slate-400" />
                    <input name="full_name" type="text" placeholder="John Doe" className={iconInputClass} value={formData.full_name} onChange={handleChange} />
                  </div>
                  
                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1 ml-1">AGE</label>
                    <div className="relative">
                      <Clock className="absolute left-4 top-3.5 w-5 h-5 text-slate-400" />
                      <input name="age" type="number" placeholder="25" className={iconInputClass} value={formData.age} onChange={handleChange} />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1 ml-1">GENDER</label>
                    <select name="gender" className={inputClass} value={formData.gender} onChange={handleChange}>
                      <option value="">Select Gender</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="non-binary">Non-binary</option>
                      <option value="other">Other</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1 ml-1">HEIGHT (CM)</label>
                    <div className="relative">
                      <Ruler className="absolute left-4 top-3.5 w-5 h-5 text-slate-400" />
                      <input name="height" type="number" placeholder="180" className={iconInputClass} value={formData.height} onChange={handleChange} />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1 ml-1">WEIGHT (KG)</label>
                    <div className="relative">
                      <Scale className="absolute left-4 top-3.5 w-5 h-5 text-slate-400" />
                      <input name="weight" type="number" placeholder="75" className={iconInputClass} value={formData.weight} onChange={handleChange} />
                    </div>
                  </div>
                </div>
              </div>

              {/* SECTION: Medical History */}
              <div className="space-y-4 pt-4 border-t border-white/40">
                <h3 className="text-xs font-bold uppercase tracking-wider text-blue-600 ml-1">Medical Context</h3>
                
                <div className="relative">
                  <label className="block text-xs font-bold text-slate-600 mb-1 ml-1">ALLERGIES</label>
                  <AlertTriangle className="absolute left-4 top-9 w-5 h-5 text-slate-400" />
                  <input name="allergies" placeholder="Peanuts, Penicillin, Pollen..." className={iconInputClass} value={formData.allergies} onChange={handleChange} />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="relative">
                    <label className="block text-xs font-bold text-slate-600 mb-1 ml-1">EXISTING CONDITIONS</label>
                    <Activity className="absolute left-4 top-9 w-5 h-5 text-slate-400" />
                    <textarea name="conditions" rows={3} placeholder="Asthma, Hypertension..." className={`${iconInputClass} resize-none`} value={formData.conditions} onChange={handleChange} />
                  </div>
                  <div className="relative">
                    <label className="block text-xs font-bold text-slate-600 mb-1 ml-1">CURRENT MEDICATIONS</label>
                    <Pill className="absolute left-4 top-9 w-5 h-5 text-slate-400" />
                    <textarea name="medications" rows={3} placeholder="Metformin 500mg..." className={`${iconInputClass} resize-none`} value={formData.medications} onChange={handleChange} />
                  </div>
                </div>
              </div>

              {/* SECTION: Lifestyle & Genetics */}
              <div className="space-y-4 pt-4 border-t border-white/40">
                <h3 className="text-sm font-bold uppercase tracking-wider text-blue-600 ml-1">Lifestyle & Genetics</h3>
                
                <div className="relative">
                  <label className="block text-xs font-bold text-slate-600 mb-1 ml-1">LIFESTYLE HABITS</label>
                  <Cigarette className="absolute left-4 top-9 w-5 h-5 text-slate-400" />
                  <input name="lifestyle" placeholder="Smoker, Vegan, Sedentary, Marathons..." className={iconInputClass} value={formData.lifestyle} onChange={handleChange} />
                </div>

                <div className="relative">
                  <label className="block text-xs font-bold text-slate-600 mb-1 ml-1">FAMILY MEDICAL HISTORY</label>
                  <HeartPulse className="absolute left-4 top-9 w-5 h-5 text-slate-400" />
                  <textarea name="family_history" rows={2} placeholder="History of heart disease..." className={`${iconInputClass} resize-none`} value={formData.family_history} onChange={handleChange} />
                </div>
              </div>

              <button 
                type="submit" 
                disabled={saving}
                className={`w-full text-white font-bold rounded-2xl py-4 shadow-lg shadow-blue-500/25 transition-all active:scale-[0.98] mt-4 ${saving ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-500 hover:bg-blue-600'}`}
              >
                {saving ? 'Saving...' : 'Update AI Health Profile'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </>
  );
};

export default ProfilePage;