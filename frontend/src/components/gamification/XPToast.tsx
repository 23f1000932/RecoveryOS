import React, { useEffect, useState } from "react";
import { Sparkles, Flame, Trophy } from "lucide-react";
import { gamification, XPToastEvent } from "../../services/gamification";

export const XPToast: React.FC = () => {
  const [toasts, setToasts] = useState<XPToastEvent[]>([]);

  useEffect(() => {
    return gamification.onToast((newToast) => {
      setToasts((prev) => [...prev, newToast]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== newToast.id));
      }, 4000);
    });
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-6 right-6 z-50 flex flex-col gap-3 pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`pointer-events-auto flex items-center gap-3.5 px-4 py-3 rounded-xl border backdrop-blur-xl transition-all duration-300 transform translate-y-0 shadow-2xl ${
            toast.isLevelUp
              ? "bg-gradient-to-r from-[#EA580C]/90 to-[#F7931A]/90 border-[#FFD600] text-white shadow-[0_0_35px_rgba(255,214,0,0.6)] animate-bounce"
              : "bg-[#0F1115]/95 border-[#F7931A]/50 text-white shadow-[0_0_25px_-5px_rgba(247,147,26,0.6)]"
          }`}
        >
          <div className="p-2 rounded-lg bg-black/40 border border-white/10 text-[#FFD600] shrink-0">
            {toast.isLevelUp ? <Trophy size={20} className="animate-spin" /> : <Sparkles size={18} />}
          </div>

          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-heading font-bold text-sm tracking-wide">
                {toast.isLevelUp ? "LEVEL UP ACHIEVED!" : `+${toast.xpAdded} XP`}
              </span>
              {toast.multiplier > 1.0 && !toast.isLevelUp && (
                <span className="flex items-center text-[10px] font-mono text-[#F7931A] font-semibold">
                  <Flame size={12} /> {toast.multiplier}x Multiplier
                </span>
              )}
            </div>
            <span className="text-xs text-[#94A3B8] font-body mt-0.5">{toast.reason}</span>
          </div>
        </div>
      ))}
    </div>
  );
};
