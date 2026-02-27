import React from 'react';
import { NavLink } from 'react-router-dom';
import { ShieldAlert, Video, UploadCloud, LayoutDashboard } from 'lucide-react';

const Navbar = () => {
    return (
        <nav className="sticky top-0 z-50 bg-darker/80 backdrop-blur-md border-b border-white/10 px-6 py-4">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
                <div className="flex items-center gap-3">
                </div>

                <div className="flex items-center gap-6">
                    <NavLink
                        to="/"
                        className={({ isActive }) => `text-sm font-medium transition-colors ${isActive ? 'text-indigo-400' : 'text-gray-400 hover:text-white'}`}
                    >
                        Overview
                    </NavLink>
                    <NavLink
                        to="/live"
                        className={({ isActive }) => `flex items-center gap-2 text-sm font-medium transition-colors ${isActive ? 'text-indigo-400' : 'text-gray-400 hover:text-white'}`}
                    >
                        <Video size={16} /> Live
                    </NavLink>
                    <NavLink
                        to="/upload"
                        className={({ isActive }) => `flex items-center gap-2 text-sm font-medium transition-colors ${isActive ? 'text-indigo-400' : 'text-gray-400 hover:text-white'}`}
                    >
                        <UploadCloud size={16} /> Upload
                    </NavLink>
                    <NavLink
                        to="/dashboard"
                        className={({ isActive }) => `flex items-center gap-2 text-sm font-medium transition-colors ${isActive ? 'text-indigo-400' : 'text-gray-400 hover:text-white'}`}
                    >
                        <LayoutDashboard size={16} /> Dashboard
                    </NavLink>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
