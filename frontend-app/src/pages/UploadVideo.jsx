import React, { useState } from 'react';
import { UploadCloud, FileVideo, Activity, StopCircle } from 'lucide-react';
import StatsCard from '../components/StatsCard';
import AlertBanner from '../components/AlertBanner';
import { useWebSocket } from '../contexts/WebSocketContext';

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const UploadVideo = () => {
    const { stats } = useWebSocket();
    const [file, setFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [isStreaming, setIsStreaming] = useState(() => {
        return sessionStorage.getItem('uploadStreaming') === 'true';
    });
    const [streamKey, setStreamKey] = useState(() => Date.now());

    const handleDrop = (e) => {
        e.preventDefault();
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile && droppedFile.type.startsWith('video/')) {
            setFile(droppedFile);
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        setIsUploading(true);
        setIsStreaming(false);
        sessionStorage.removeItem('uploadStreaming');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch(`${API_BASE}/api/upload`, {
                method: 'POST',
                body: formData,
            });
            if (res.ok) {
                console.log('Upload complete, live processing started');
                setIsStreaming(true);
                sessionStorage.setItem('uploadStreaming', 'true');
            } else {
                const errorText = await res.text();
                console.error('Upload failed:', res.status, errorText);
            }
        } catch (error) {
            console.error('Upload error:', error);
        } finally {
            setIsUploading(false);
        }
    };

    const handleStopAndReset = async () => {
        try {
            await fetch(`${API_BASE}/api/stop-camera`, { method: 'POST' });
        } catch (e) { }
        setIsStreaming(false);
        setFile(null);
        sessionStorage.removeItem('uploadStreaming');
    };

    return (
        <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Post-Event Analysis</h1>
                    <p className="text-gray-400 mt-1">Upload CCTV footage for forensic AI scanning</p>
                </div>
                {isStreaming && (
                    <button onClick={handleStopAndReset} className="btn-secondary text-red-400 hover:border-red-500/50">
                        <StopCircle size={20} /> Stop & New Upload
                    </button>
                )}
            </div>

            <AlertBanner level={stats.risk_level} message={stats.message} />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="col-span-1 lg:col-span-2 flex flex-col gap-6">
                    {!isStreaming && !isUploading && (
                        <div
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={handleDrop}
                            className="glass-panel border-2 border-dashed border-gray-600 hover:border-indigo-500 transition-colors rounded-2xl p-12 text-center cursor-pointer flex flex-col items-center justify-center min-h-[400px]"
                            onClick={() => document.getElementById('file-upload').click()}
                        >
                            <input
                                id="file-upload"
                                type="file"
                                accept="video/*"
                                className="hidden"
                                onChange={(e) => setFile(e.target.files[0])}
                            />
                            <UploadCloud size={64} className="text-gray-500 mb-6" />
                            <h3 className="text-2xl font-bold mb-2">Drag & Drop Video</h3>
                            <p className="text-gray-400">or click to browse from your computer</p>

                            {file && (
                                <div className="mt-8 p-4 bg-gray-800 rounded-lg flex items-center gap-3 border border-gray-700">
                                    <FileVideo className="text-indigo-400" />
                                    <span className="font-medium">{file.name}</span>
                                </div>
                            )}
                        </div>
                    )}

                    {isUploading && (
                        <div className="glass-panel rounded-2xl p-12 text-center flex flex-col items-center justify-center min-h-[400px]">
                            <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-6"></div>
                            <h3 className="text-xl font-bold">Uploading & Starting Analysis...</h3>
                            <p className="text-gray-400 mt-2">This may take a moment depending on file size</p>
                        </div>
                    )}

                    {isStreaming && !isUploading && (
                        <div className="glass-panel overflow-hidden bg-black aspect-video rounded-2xl flex items-center justify-center relative">
                            <img
                                src={`${API_BASE}/api/video?t=${streamKey}`}
                                alt="Processed Video Feed"
                                className="w-full h-full object-cover"
                                onError={() => {
                                    if (isStreaming) {
                                        setTimeout(() => setStreamKey(Date.now()), 2000);
                                    }
                                }}
                            />
                            {/* Processing Indicator */}
                            <div className="absolute top-4 right-4 flex items-center gap-2 bg-black/60 px-3 py-1 rounded-full backdrop-blur-md border border-white/10">
                                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></div>
                                <span className="text-xs font-bold tracking-wider text-indigo-400">PROCESSING</span>
                            </div>
                        </div>
                    )}

                    {file && !isStreaming && !isUploading && (
                        <button onClick={handleUpload} className="btn-primary w-full py-4 text-lg">
                            Start AI Analysis
                        </button>
                    )}
                </div>

                <div className="flex flex-col gap-4">
                    <StatsCard
                        title="Current Crowd"
                        value={stats.crowd_count}
                        icon={Activity}
                        color={stats.crowd_count > 30 ? "yellow" : "indigo"}
                    />
                    <StatsCard
                        title="Total Unique Persons"
                        value={stats.unique_count}
                        icon={Activity}
                        color="indigo"
                        delay={0.1}
                    />
                    <StatsCard
                        title="Weapons Logged"
                        value={stats.total_weapons || (stats.weapon_detected ? 1 : 0)}
                        icon={Activity}
                        color={stats.weapon_detected ? "red" : "green"}
                        delay={0.2}
                    />
                </div>
            </div>
        </div>
    );
};

export default UploadVideo;
