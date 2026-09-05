import React, { useEffect, useState } from "react";
import { Award, Flame, Zap, Shield, Sparkles } from "lucide-react";
import { gamification, HunterState } from "../../services/gamification";

interface HunterHUDProps {
  onOpenTrophies: () => void;
}

export const HunterHUD: React.FC<HunterHUDProps> = ({ onOpenTrophies }) => {
  const [state, setState] = useState<HunterState>(gamification.getState());

  useEffect(() => {
    return gamification.subscribe(setState);
  }, []);

  const currentLevelMin = state.currentLevelXP;
  const nextLevelMax = state.nextLevelXP;
  const progressInLevel = Math.max(0, state.xp - currentLevelMin);
  const levelSpan = Math.max(1, nextLevelMax - currentLevelMin);
  const progressPercent = Math.min(100, Math.round((progressInLevel / levelSpan) * 100));

  return (
    <div className="flex items-center gap-3 md:gap-5 px-3 py-1.5 rounded-full bg-[#0F1115]/90 border border-white/10 backdrop-blur-md shadow-[0_0_20px_-5px_rgba(247,147,26,0.2)]">
      {/* Rank & Level Badge */}
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#EA580C] to-[#F7931A] flex items-center justify-center text-white font-heading font-bold text-xs shadow-[0_0_12px_rgba(247,147,26,0.6)]">
          {state.level}
        </div>
        <div className="hidden sm:flex flex-col">
          <span className="text-[10px] uppercase font-mono tracking-wider text-[#94A3B8]">
            Hunter Rank
          </span>
          <span className="text-xs font-heading font-semibold text-white">
            {state.rankTitle}
          </span>
        </div>
      </div>

      {/* XP Progress Bar */}
      <div className="hidden lg:flex flex-col gap-1 w-32 xl:w-40">
        <div className="flex justify-between text-[10px] font-mono text-[#94A3B8]">
          <span className="text-[#FFD600] font-semibold">{state.xp} XP</span>
          <span>{nextLevelMax} XP</span>
        </div>
        <div className="w-full h-1.5 rounded-full bg-[#1E293B] overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-[#EA580C] via-[#F7931A] to-[#FFD600] transition-all duration-500 rounded-full shadow-[0_0_8px_rgba(255,214,0,0.5)]"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Streak Combo Multiplier */}
      {state.streak > 0 && (
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#EA580C]/20 border border-[#EA580C]/40 text-[#F7931A] text-xs font-mono font-medium animate-pulse">
          <Flame size={14} className="text-[#F7931A] animate-bounce" />
          <span>{state.streak}x Streak</span>
          {state.multiplier > 1.0 && (
            <span className="text-[#FFD600] font-bold text-[10px] ml-0.5">
              ({state.multiplier}x)
            </span>
          )}
        </div>
      )}

      {/* Trophy Modal Trigger */}
      <button
        onClick={onOpenTrophies}
        type="button"
        title="View Unlocked Cryptographic Badges"
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 hover:border-[#FFD600]/40 text-white hover:text-[#FFD600] text-xs font-heading transition-all duration-200 cursor-pointer"
      >
        <Award size={14} className="text-[#FFD600]" />
        <span className="hidden sm:inline font-medium">Trophies</span>
        <span className="px-1.5 py-0.2 rounded-full bg-[#F7931A]/30 text-[10px] font-mono text-[#FFD600]">
          {state.unlockedBadges.length}
        </span>
      </button>
    </div>
  );
};
