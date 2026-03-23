'use client';
import React, { useState } from 'react';
import Link from 'next/link';
import { Home } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import { useRouter } from 'next/navigation';

function RegisterPage() { 
    const router = useRouter();
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        password: ''
    });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({
            ...formData,
            [e.target.id]: e.target.value
        });
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        const { error } = await supabase.auth.signUp({
            email: formData.email,
            password: formData.password,
            options: {
                data: {
                    full_name: formData.name,
                },
            },
        });

        if (error) {
            setError(error.message);
            setLoading(false);
        } else {
            alert('Registration successful! Please check your email for verification.');
            router.push('/Login');
        }
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-screen font-sans overflow-hidden bg-[#e0f2fe] bg-gradient-to-br from-[#dcfce7] via-[#e0f2fe] to-[#f0f9ff] relative">
            
            {/* Background Decorative Bubbles */}
            <div className="absolute top-20 right-[20%] w-32 h-32 bg-white/20 rounded-full backdrop-blur-3xl border border-white/30 hidden md:block" />
            <div className="absolute bottom-10 left-[15%] w-48 h-48 bg-white/20 rounded-full backdrop-blur-3xl border border-white/30 hidden md:block" />
            <div className="absolute bottom-4 right-4 w-12 h-12 bg-white/40 rounded-full flex items-center justify-center border border-white/30 shadow-sm">

            </div>

            {/* Home Button */}
            <div className="absolute top-8 left-8">
                <Link 
                    href="/" 
                    className="flex items-center gap-2 px-4 py-2 text-slate-600 bg-white/50 backdrop-blur-md hover:bg-white/80 rounded-xl transition-all font-medium border border-white/50 shadow-sm"
                >
                    <Home className="w-4 h-4" />
                    <span className="text-sm">Home</span>
                </Link>
            </div>

            {/* Registration Card */}
            <div className="w-full max-w-md bg-white/40 backdrop-blur-2xl rounded-[2.5rem] border border-white/60 shadow-2xl shadow-blue-200/50 p-10 flex flex-col items-center">
                
                {/* Logo Section */}
                <div className="flex items-center gap-2 mb-4">
                    <div className="flex gap-1">
                        <div className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-sm"></div>
                        <div className="w-2.5 h-2.5 rounded-full bg-[#52ce90] shadow-sm"></div>
                    </div>
                    <h2 className="text-xl font-bold text-slate-800 tracking-tight">HealthyLabs.AI</h2>
                </div>

                <h1 className="text-3xl font-black text-slate-900 mb-8 tracking-tight text-center">Create a new account</h1>

                <form className="w-full space-y-5" onSubmit={handleSubmit}>
                    {error && (
                        <div className="p-3 bg-red-50/50 backdrop-blur-md border border-red-100 text-red-600 text-xs font-semibold rounded-xl text-center animate-in fade-in slide-in-from-top-1">
                            {error}
                        </div>
                    )}

                    <div className="space-y-2">
                        <label className="block text-sm font-bold text-slate-700 ml-1">Name</label>
                        <input 
                            className="w-full px-5 py-3 bg-white/60 border border-white/80 text-slate-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-400 transition-all placeholder:text-slate-400 font-medium" 
                            type="text" 
                            id="name" 
                            placeholder="Enter your name"
                            required 
                            onChange={handleChange} 
                        />          
                    </div>

                    <div className="space-y-2">
                        <label className="block text-sm font-bold text-slate-700 ml-1" htmlFor="email">Email</label>
                        <input 
                            className="w-full px-5 py-3 bg-white/60 border border-white/80 text-slate-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-400 transition-all placeholder:text-slate-400 font-medium" 
                            type="email" 
                            id="email" 
                            placeholder="Enter your email"
                            required 
                            onChange={handleChange} 
                        />          
                    </div>

                    <div className="space-y-2">
                        <label className="block text-sm font-bold text-slate-700 ml-1" htmlFor="password">Password</label> 
                        <input 
                            className="w-full px-5 py-3 bg-white/60 border border-white/80 text-slate-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-400 transition-all placeholder:text-slate-400 font-medium" 
                            type="password" 
                            id="password" 
                            placeholder="Create password"
                            required 
                            onChange={handleChange} 
                        />
                    </div>  

                    <button 
                        disabled={loading} 
                        className="w-full mt-2 bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-2xl font-bold text-lg shadow-xl shadow-blue-200 transition-all transform active:scale-[0.98] disabled:bg-blue-400 disabled:shadow-none cursor-pointer" 
                        type="submit"
                    >
                        {loading ? 'Registering...' : 'Register'}
                    </button>
                </form>

                <p className="mt-8 text-slate-600 font-medium text-sm">
                    Already a user? <Link href="/Login" className="text-blue-600 font-bold hover:underline">Login</Link>
                </p>
            </div>
        </div>
    );
}

export default RegisterPage;