import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Play, Square, Activity } from 'lucide-react';
import StatsCard from '../components/StatsCard';
import AlertBanner from '../components/AlertBanner';
import { useWebSocket } from '../contexts/WebSocketContext';

const LiveDetection = () => {
    const { stats } = useWebSocket();
    const [isPlaying, setIsPlaying] = useState(stats.status === "Running");
    const [streamKey, setStreamKey] = useState(Date.now());
    const imgRef = useRef(null);

    // Sync isPlaying with backend engine state via WebSocket
    useEffect(() => {
        if (stats.status === "Running") {
            setIsPlaying(true);
        } else if (stats.status === "Offline") {
            setIsPlaying(false);
        }
    }, [stats.status]);

    const handleStart = async () => {
        try {
            const res = await fetch('http://localhost:8000/api/start-camera', { method: 'POST' });
            if (res.ok) {
                setStreamKey(Date.now());
                setIsPlaying(true);
            }
        } catch (e) {
            console.error(e);
        }
    };

    const handleStop = async () => {
        try {
            await fetch('http://localhost:8000/api/stop-camera', { method: 'POST' });
            setIsPlaying(false);
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Live Security Feed</h1>

                </div>
                <div className="flex gap-4">
                    {!isPlaying ? (
                        <button onClick={handleStart} className="btn-primary">
                            <Play size={20} /> Start Camera
                        </button>
                    ) : (
                        <button onClick={handleStop} className="btn-secondary text-red-400 hover:border-red-500/50">
                            <Square size={20} /> Stop Feed
                        </button>
                    )}
                </div>
            </div>

            <AlertBanner level={stats.risk_level} message={stats.message} />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Video Feed */}
                <div className="col-span-1 lg:col-span-2">
                    <div className="glass-panel overflow-hidden relative aspect-video bg-black flex items-center justify-center">
                        {isPlaying ? (
                            <img
                                ref={imgRef}
                                key={streamKey}
                                src={`http://localhost:8000/api/video?t=${streamKey}`}
                                alt="Live Video Feed"
                                className="w-full h-full object-cover"
                                onError={() => {
                                    if (isPlaying) {
                                        setTimeout(() => setStreamKey(Date.now()), 1500);
                                    }
                                }}
                            />
                        ) : (
                            <div className="text-gray-500 flex flex-col items-center gap-4">
                                <Activity size={48} className="opacity-50" />
                                <p>Camera is offline. Click "Start Camera" to begin detection.</p>
                            </div>
                        )}

                        {/* Live Indicator */}
                        {isPlaying && (
                            <div className="absolute top-4 right-4 flex items-center gap-2 bg-black/60 px-3 py-1 rounded-full backdrop-blur-md border border-white/10">
                                <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
                                <span className="text-xs font-bold tracking-wider text-red-500">LIVE</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Realtime Stats */}
                <div className="flex flex-col gap-4">
                    <StatsCard
                        title="Current Crowd"
                        value={stats.crowd_count}
                        icon={Activity}
                        color={stats.crowd_count > 30 ? "yellow" : "indigo"}
                    />
                    <StatsCard
                        title="Total Unique People"
                        value={stats.unique_count}
                        icon={Activity}
                        color="indigo"
                        delay={0.1}
                    />
                    <StatsCard
                        title="FPS"
                        value={stats.fps}
                        icon={Activity}
                        color={stats.fps < 20 ? "red" : "green"}
                        delay={0.2}
                    />
                </div>
            </div>
        </div>
    );
};

export default LiveDetection;
