import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, CheckCircle, Info } from 'lucide-react';

const AlertBanner = ({ level, message }) => {
    if (level === 'NORMAL' || !message) return null;

    const config = {
        WARNING: {
            bg: 'bg-yellow-500/20',
            border: 'border-yellow-500/50',
            text: 'text-yellow-400',
            icon: <Info size={24} className="text-yellow-400" />
        },
        CRITICAL: {
            bg: 'bg-red-500/20',
            border: 'border-red-500/50',
            text: 'text-red-400',
            icon: <AlertTriangle size={24} className="text-red-400 animate-pulse-fast" />
        }
    };

    const style = config[level] || config.WARNING;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className={`flex items-center gap-4 p-4 rounded-xl border ${style.bg} ${style.border} shadow-lg mb-6 backdrop-blur-md`}
            >
                {style.icon}
                <span className={`text-lg font-semibold tracking-wide ${style.text}`}>
                    {message}
                </span>
            </motion.div>
        </AnimatePresence>
    );
};

export default AlertBanner;
