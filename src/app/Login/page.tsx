"use client";

import { useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useRouter } from 'next/navigation';

function LoginPage() {  
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const router = useRouter();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        const { error } = await supabase.auth.signInWithPassword({
            email,
            password,
        });

        if (error) {
            setError(error.message);
            setLoading(false);
        } else {
            // Redirect to dashboard or home page after successful login
            router.push('/dashboard'); 
            router.refresh();
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-r from-blue-500 to-purple-500">
            <h1 className="text-4xl font-bold text-white mb-6">Login Page</h1>
            <form onSubmit={handleLogin} className="bg-white p-8 rounded-lg shadow-md w-full max-w-sm">
                {error && <div className="mb-4 text-red-500 text-sm text-center">{error}</div>}
                <div className="mb-4">
                    <label className="block text-gray-700 mb-2" htmlFor="email">Email</label>
                    <input onChange={(e) => setEmail(e.target.value)} value={email} className="w-full px-3 py-2 border border-gray-300 text-black rounded focus:outline-none focus:ring-2 focus:ring-blue-500" type="email" id="email" required />          
                </div>
                <div className="mb-4">
                    <label className="block text-gray-700 mb-2" htmlFor="password">Password</label> 
                    <input onChange={(e) => setPassword(e.target.value)} value={password} className="w-full px-3 py-2 border border-gray-300 text-black rounded focus:outline-none focus:ring-2 focus:ring-blue-500" type="password" id="password" required />
                </div>  
                <button disabled={loading} className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition-colors cursor-pointer disabled:bg-blue-400" type="submit">
                    {loading ? 'Logging in...' : 'Login'}
                </button>
            </form>
            <p className="mt-4 text-white">Don't have an account? <a href="/Register" className="text-blue-200 hover:underline">Register</a></p>
        </div>
    );
}
export default LoginPage;