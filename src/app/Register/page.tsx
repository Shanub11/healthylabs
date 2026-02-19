'use client';
import React, { useState } from 'react';
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
        <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-r from-blue-500 to-purple-500">
            <h1 className="text-4xl font-bold text-white mb-6">Create a new account</h1>
            <form className="bg-white p-8 rounded-lg shadow-md w-full max-w-sm" onSubmit={handleSubmit}>
                {error && <div className="mb-4 text-red-500 text-sm text-center">{error}</div>}
                <div className="mb-4">
                    <label className="block text-gray-700 mb-2">Name</label>
                    <input className="w-full px-3 py-2 border border-gray-300 text-black rounded focus:outline-none focus:ring-2 focus:ring-blue-500" type="text" id="name" required onChange={handleChange} />          
                </div>
                <div className="mb-4">
                    <label className="block text-gray-700 mb-2" htmlFor="email">Email</label>
                    <input className="w-full px-3 py-2 border border-gray-300 text-black rounded focus:outline-none focus:ring-2 focus:ring-blue-500" type="email" id="email" required onChange={handleChange} />          
                </div>
                <div className="mb-4">
                    <label className="block text-gray-700 mb-2" htmlFor="password">Password</label> 
                    <input className="w-full px-3 py-2 border border-gray-300 rounded text-black focus:outline-none focus:ring-2 focus:ring-blue-500" type="password" id="password" required onChange={handleChange} />
                </div>  
                <button disabled={loading} className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition-colors cursor-pointer disabled:bg-blue-400" type="submit">
                    {loading ? 'Registering...' : 'Register'}
                </button>
            </form>
            <p className="mt-4 text-white">Already a user? <a href="/Login" className="text-blue-200 hover:underline">Login</a></p>
        </div>
    );
}
export default RegisterPage;