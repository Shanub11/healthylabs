// Import the necessary icons from lucide-react
import { HeartPulse, MessageSquare, HandHeart, Search } from 'lucide-react';
import Link from 'next/link';

// Main App Component
const App = () => {
    return (
        <>
            {/* In a real React application, you would place the Google Fonts link 
              in the `public/index.html` file. The custom styles and keyframes 
              would typically go into a separate CSS file (e.g., App.css) and be imported.
              For this self-contained example, they are included directly.
            */}
            <style>{`
                @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;500;600&family=Inter:wght@400;500&display=swap');
                
                body {
                    font-family: 'Inter', sans-serif;
                    background-color: #111827; /* bg-gray-900 */
                    color: white;
                    overflow: hidden;
                }
                .font-lora {
                    font-family: 'Lora', serif;
                }
                .glass-blob {
                    border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%;
                    animation: morph 8s ease-in-out infinite;
                    transition: all 1s ease-in-out;
                }
                @keyframes morph {
                    0% {
                        border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%;
                    }
                    50% {
                        border-radius: 30% 60% 70% 40% / 50% 60% 30% 60%;
                    }
                    100% {
                        border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%;
                    }
                }
            `}</style>

            {/* Main container with gradient background */}
            <div className="relative w-full h-screen flex items-center justify-center bg-gradient-to-br from-[#6f00ff] via-[#b600a3] to-[#71c562]">
                
                {/* Header Icons and Buttons */}
                <header className="absolute top-0 left-0 w-full p-6 md:p-8 flex justify-between items-center z-20">
                    {/* Left side icons */}
                    <div className="flex items-center space-x-4">
                        <div className="w-10 h-10 md:w-12 md:h-12 bg-white/20 backdrop-blur-sm border border-white/30 rounded-full flex items-center justify-center">
                            {/* Replaced with Lucide icon */}
                            <HeartPulse className="w-6 h-6 text-white" />
                        </div>
                        <div className="w-10 h-10 md:w-12 md:h-12 bg-white/20 backdrop-blur-sm border border-white/30 rounded-full flex items-center justify-center">
                            {/* Replaced with Lucide icon */}
                            <MessageSquare className="w-6 h-6 text-white" />
                        </div>
                    </div>
                    
                    {/* Right side icons and buttons */}
                    <div className="flex items-center space-x-4">
                         <div className="w-10 h-10 md:w-12 md:h-12 bg-white/20 backdrop-blur-sm border border-white/30 rounded-full flex items-center justify-center">
                            {/* Replaced with Lucide icon */}
                            <HandHeart className="w-7 h-7 text-white" />
                        </div>
                        <Link href="Login" className="bg-white/20 backdrop-blur-sm border border-white/30 rounded-full px-5 py-2.5 text-sm font-medium hover:bg-white/30 transition-colors cursor-pointer">Login</Link>
                        <Link href="Register" className="hidden sm:block bg-white/20 backdrop-blur-sm border border-white/30 rounded-full px-5 py-2.5 text-sm font-medium hover:bg-white/30 transition-colors cursor-pointer">Register</Link>
                    </div>
                </header>

                {/* Main Content Area */}
                <main className="relative w-full flex items-center justify-center">
                    {/* Glassmorphism Blob */}
                    <div className="glass-blob w-[90%] h-[45vh] sm:w-2/3 sm:h-[50vh] md:w-1/2 lg:w-[45%] lg:h-[50vh] bg-white/10 backdrop-blur-xl border-2 border-white/20 shadow-2xl flex items-center justify-center">
                        <div className="text-center">
                            <h1 className="font-lora text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-medium tracking-wide">Welcome to</h1>
                            <h2 className="font-lora text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-semibold tracking-wide mt-2">HealthyLabs.AI</h2>
                        </div>
                    </div>
                </main>

                {/* Bottom Search Bar */}
                <footer className="absolute bottom-8 md:bottom-12 w-full flex justify-center z-20 px-4">
                    <div className="flex items-center space-x-4 bg-black/20 backdrop-blur-sm border border-white/30 rounded-full px-4 py-3 md:px-6 md:py-4">
                        <span className="text-2xl md:text-3xl font-light opacity-70">(</span>
                        <div className="w-8 h-8 md:w-10 md:h-10 border-2 border-white/80 rounded-full flex items-center justify-center">
                            {/* Replaced with Lucide icon */}
                            <Search className="w-4 h-4 md:w-5 md:h-5 text-white" />
                        </div>
                        <p className="text-sm md:text-base text-white/90 tracking-wide">Worry about your health? Ask me</p>
                        <span className="text-2xl md:text-3xl font-light opacity-70">)</span>
                    </div>
                </footer>
            </div>
        </>
    );
};

export default App;
