import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import LandingPage from './pages/LandingPage';
import UploadVideo from './pages/UploadVideo';
import LiveDetection from './pages/LiveDetection';
import Dashboard from './pages/Dashboard';
import { WebSocketProvider } from './contexts/WebSocketContext';

function App() {
    return (
        <BrowserRouter>
            <WebSocketProvider>
                <div className="min-h-screen flex flex-col bg-darker text-white">
                    <Navbar />
                    <main className="flex-1">
                        <Routes>
                            <Route path="/" element={<LandingPage />} />
                            <Route path="/upload" element={<UploadVideo />} />
                            <Route path="/live" element={<LiveDetection />} />
                            <Route path="/dashboard" element={<Dashboard />} />
                        </Routes>
                    </main>
                </div>
            </WebSocketProvider>
        </BrowserRouter>
    );
}

export default App;
