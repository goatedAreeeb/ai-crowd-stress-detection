import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';

const WebSocketContext = createContext();

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS_URL = API_BASE.replace(/^http/, 'ws') + '/ws/live';

export const WebSocketProvider = ({ children }) => {
    const ws = useRef(null);
    const reconnectTimer = useRef(null);
    const [isConnected, setIsConnected] = useState(false);
    const [stats, setStats] = useState({
        crowd_count: 0,
        unique_count: 0,
        weapon_detected: false,
        risk_level: 'NORMAL',
        fps: 0,
        message: '',
        status: 'Connecting...',
        stress_score: 0,
        total_weapons: 0
    });

    const connect = useCallback(() => {
        // Clean up any existing connection
        if (ws.current && ws.current.readyState < 2) {
            ws.current.close();
        }

        try {
            ws.current = new WebSocket(WS_URL);

            ws.current.onopen = () => {
                console.log('WebSocket connected');
                setIsConnected(true);
            };

            ws.current.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    setStats(prevStats => ({
                        ...prevStats,
                        ...data
                    }));
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e);
                }
            };

            ws.current.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            ws.current.onclose = () => {
                console.log('WebSocket closed, reconnecting in 3s...');
                setIsConnected(false);
                setStats(prev => ({ ...prev, status: 'Connecting...' }));
                // Auto-reconnect after 3 seconds
                reconnectTimer.current = setTimeout(connect, 3000);
            };
        } catch (e) {
            console.error('WebSocket connection failed:', e);
            reconnectTimer.current = setTimeout(connect, 3000);
        }
    }, []);

    useEffect(() => {
        connect();

        return () => {
            if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
            if (ws.current) ws.current.close();
        };
    }, [connect]);

    const value = {
        ws: ws.current,
        isConnected,
        stats,
    };

    return (
        <WebSocketContext.Provider value={value}>
            {children}
        </WebSocketContext.Provider>
    );
};

export const useWebSocket = () => {
    const context = useContext(WebSocketContext);
    if (!context) {
        throw new Error('useWebSocket must be used within WebSocketProvider');
    }
    return context;
};
