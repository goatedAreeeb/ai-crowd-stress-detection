import React, { createContext, useContext, useEffect, useRef, useState } from 'react';

const WebSocketContext = createContext();

export const WebSocketProvider = ({ children }) => {
    const ws = useRef(null);
    const [isConnected, setIsConnected] = useState(false);
    const [stats, setStats] = useState({
        crowd_count: 0,
        unique_count: 0,
        weapon_detected: false,
        risk_level: 'NORMAL',
        fps: 0,
        message: '',
        status: 'Offline',
        stress_score: 0,
        total_weapons: 0
    });

    useEffect(() => {
        // Connect to WebSocket once at app level
        ws.current = new WebSocket(`ws://localhost:8000/ws/live`);

        ws.current.onopen = () => {
            console.log('WebSocket connected');
            setIsConnected(true);
        };

        ws.current.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('WebSocket message:', data);
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
            setIsConnected(false);
        };

        ws.current.onclose = () => {
            console.log('WebSocket closed');
            setIsConnected(false);
        };

        // Cleanup on unmount - don't close, keep connection alive
        return () => {
            // Only close if the app is actually unmounting
            // This prevents closing when components navigate
        };
    }, []);

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
