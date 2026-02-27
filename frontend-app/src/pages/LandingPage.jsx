import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, ShieldCheck, Activity, Cpu } from 'lucide-react';
import { Link } from 'react-router-dom';

const LandingPage = () => {
    return (
        <div className="relative overflow-hidden min-h-[calc(100vh-73px)] flex flex-col">
            {/* Background Gradients */}
            <div className="absolute top-0 -left-1/4 w-1/2 h-1/2 bg-indigo-600/20 rounded-full blur-[120px] pointer-events-none" />
            <div className="absolute bottom-0 -right-1/4 w-1/2 h-1/2 bg-blue-600/20 rounded-full blur-[120px] pointer-events-none" />

            <div className="flex-1 flex flex-col items-center justify-center text-center px-4 max-w-5xl mx-auto z-10 w-full">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.7 }}
                    className="mb-6 inline-flex items-center gap-2 px-4 py-2 rounded-full glass-panel border border-indigo-500/30 text-indigo-300 text-sm font-medium"
                >
                    
                </motion.div>

                <motion.h1
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.7, delay: 0.1 }}
                    className="text-6xl md:text-8xl font-black tracking-tighter mb-6 bg-gradient-to-br from-white via-indigo-200 to-indigo-600 text-transparent bg-clip-text"
                >
                    Intelligent Crowd <br />& Security Vision
                </motion.h1>

                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.7, delay: 0.2 }}
                    className="text-xl md:text-2xl text-gray-400 mb-10 max-w-3xl leading-relaxed"
                >
                    Next-generation real-time threat detection and crowd density analysis powered by YOLOv8 and CUDA acceleration.
                </motion.p>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.7, delay: 0.3 }}
                    className="flex flex-col sm:flex-row gap-4"
                >
                    <Link to="/live" className="btn-primary px-8 py-4 text-lg">
                        Start Live Detection <ArrowRight size={20} />
                    </Link>
                    <Link to="/upload" className="btn-secondary px-8 py-4 text-lg">
                        Upload Footage
                    </Link>
                </motion.div>

                {/* Feature Grid */}
                <motion.div
                    initial={{ opacity: 0, y: 40 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.7, delay: 0.5 }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-20 w-full"
                >
                    {[
                        { title: "Real-time Processing", desc: "Sustains 30+ FPS utilizing GPU FP16 precision and multithreading.", icon: Activity },
                        { title: "Weapon Detection", desc: "Temporal smoothing and high-res scaling catches hidden threats instantly.", icon: ShieldCheck },
                        { title: "Smart Alerts", desc: "Automated risk assessment matrix triggers instant visual warnings.", icon: ArrowRight },
                    ].map((f, i) => (
                        <div key={i} className="glass-panel p-6 text-left hover:-translate-y-1 transition-transform">
                            <f.icon className="text-indigo-400 mb-4" size={32} />
                            <h3 className="text-xl font-bold mb-2 text-white">{f.title}</h3>
                            <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
                        </div>
                    ))}
                </motion.div>
            </div>
        </div>
    );
};

export default LandingPage;
