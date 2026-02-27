import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import StatsCard from '../components/StatsCard';
import { Users, ShieldAlert, Activity } from 'lucide-react';
import { useWebSocket } from '../contexts/WebSocketContext';

const Dashboard = () => {
    const { stats } = useWebSocket();
    const [historyData, setHistoryData] = useState([]);

    useEffect(() => {
        if (stats.status !== "Offline" && stats.status !== "Initializing...") {
            // Add to history for chart
            setHistoryData(prev => {
                const newData = [...prev, {
                    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                    crowd: stats.crowd_count,
                    risk: stats.stress_score || (stats.risk_level === 'CRITICAL' ? 100 : stats.risk_level === 'WARNING' ? 60 : 20)
                }];
                if (newData.length > 50) return newData.slice(newData.length - 50); // keep last 50 points
                return newData;
            });
        }
    }, [stats]);

    return (
        <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="mb-8">
                <h1 className="text-3xl font-bold tracking-tight">System Intelligence Dashboard</h1>
                <p className="text-gray-400 mt-1">Historical analytics and real-time event logging</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <StatsCard title="Current Live Crowd" value={stats.crowd_count} icon={Users} color="indigo" />
                <StatsCard title="Total Unique Persons" value={stats.unique_count} icon={Activity} color="green" />
                <StatsCard title="Total Weapons Detected" value={stats.total_weapons || 0} icon={ShieldAlert} color={stats.total_weapons > 0 ? "red" : "indigo"} />
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                {/* Crowd Graph */}
                <div className="glass-panel p-6 border-white/5">
                    <h3 className="text-xl font-bold mb-6">Real-Time Crowd Density</h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={historyData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                                <defs>
                                    <linearGradient id="colorCrowd" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#818cf8" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#818cf8" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <XAxis dataKey="time" stroke="#6b7280" fontSize={12} tickMargin={10} />
                                <YAxis stroke="#6b7280" fontSize={12} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '8px' }}
                                    itemStyle={{ color: '#c7d2fe' }}
                                />
                                <Area type="monotone" dataKey="crowd" stroke="#818cf8" strokeWidth={3} fillOpacity={1} fill="url(#colorCrowd)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Risk Graph */}
                <div className="glass-panel p-6 border-white/5">
                    <h3 className="text-xl font-bold mb-6">Security Risk Level (%)</h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={historyData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                                <XAxis dataKey="time" stroke="#6b7280" fontSize={12} tickMargin={10} />
                                <YAxis stroke="#6b7280" fontSize={12} domain={[0, 100]} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '8px' }}
                                />
                                <Line type="stepAfter" dataKey="risk" stroke="#ef4444" strokeWidth={3} dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
