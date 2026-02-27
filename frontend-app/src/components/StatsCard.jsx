import React from 'react';
import { motion } from 'framer-motion';

const StatsCard = ({ title, value, icon: Icon, color = "indigo", delay = 0 }) => {
    const colorMap = {
        indigo: "text-indigo-400 bg-indigo-400/10 border-indigo-500/20",
        green: "text-green-400 bg-green-400/10 border-green-500/20",
        red: "text-red-400 bg-red-400/10 border-red-500/20",
        yellow: "text-yellow-400 bg-yellow-400/10 border-yellow-500/20",
    };

    const styleClasses = colorMap[color] || colorMap.indigo;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay }}
            className={`glass-panel p-6 border flex flex-col items-center justify-center text-center ${styleClasses}`}
        >
            <div className="mb-4 p-3 rounded-full bg-black/20">
                <Icon size={28} />
            </div>
            <div className="text-4xl font-bold mb-1 tracking-tight">{value}</div>
            <div className="text-sm font-medium uppercase tracking-wider opacity-80">{title}</div>
        </motion.div>
    );
};

export default StatsCard;
