import React from "react";
import {
  X,
  Award,
  ShieldCheck,
  Coins,
  Cpu,
  Zap,
  Flame,
  Lock,
  CheckCircle2,
  ShieldAlert,
} from "lucide-react";
import { ALL_BADGES, HunterBadge, HunterState } from "../../services/gamification";

interface TrophyModalProps {
  isOpen: boolean;
  onClose: () => void;
  state: HunterState;
}

const BADGE_ICONS: Record<string, React.ReactNode> = {
  ShieldAlert: <ShieldAlert size={20} />,
  Coins: <Coins size={20} />,
  ShieldCheck: <ShieldCheck size={20} />,
  Cpu: <Cpu size={20} />,
  Zap: <Zap size={20} />,
  Flame: <Flame size={20} />,
};

export const TrophyModal: React.FC<TrophyModalProps> = ({ isOpen, onClose, state }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-[#0F1115] border border-white/15 p-6 md:p-8 shadow-[0_0_60px_-10px_rgba(247,147,26,0.3)]">
        {/* Header */}
        <div className="flex items-center justify-between pb-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-[#EA580C]/20 to-[#F7931A]/20 border border-[#F7931A]/40 text-[#FFD600] shadow-[0_0_15px_rgba(247,147,26,0.4)]">
              <Award size={24} />
            </div>
            <div>
              <h2 className="text-xl font-heading font-bold text-white tracking-wide">
                Recovery Hunter Trophies
              </h2>
              <p className="text-xs font-mono text-[#94A3B8]">
                CRYPTOGRAPHIC ACHIEVEMENTS &amp; MINING PROOFS
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-[#94A3B8] hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
          >
            <X size={20} />
          </button>
        </div>

        {/* Hunter Status Overview */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 my-6">
          <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
            <span className="text-[11px] font-mono text-[#94A3B8] uppercase">Hunter Rank</span>
            <div className="text-lg font-heading font-bold text-white mt-1 flex items-center gap-2">
              <span className="text-[#F7931A]">Lvl {state.level}</span>
              <span className="text-xs text-[#94A3B8]">({state.rankTitle})</span>
            </div>
          </div>
          <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
            <span className="text-[11px] font-mono text-[#94A3B8] uppercase">Total XP</span>
            <div className="text-lg font-mono font-bold text-[#FFD600] mt-1">
              {state.xp.toLocaleString()} XP
            </div>
          </div>
          <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
            <span className="text-[11px] font-mono text-[#94A3B8] uppercase">Streak Multiplier</span>
            <div className="text-lg font-mono font-bold text-[#F7931A] mt-1 flex items-center gap-1.5">
              <Flame size={18} className="text-[#EA580C]" />
              {state.multiplier}x Multiplier
            </div>
          </div>
        </div>

        {/* Badges Grid */}
        <div className="space-y-3">
          <h3 className="text-xs font-mono uppercase tracking-wider text-[#94A3B8]">
            Badges Catalog ({state.unlockedBadges.length} / {ALL_BADGES.length} Unlocked)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {ALL_BADGES.map((badge: HunterBadge) => {
              const isUnlocked = state.unlockedBadges.includes(badge.id);
              return (
                <div
                  key={badge.id}
                  className={`p-4 rounded-xl border transition-all duration-300 flex items-start gap-3.5 ${
                    isUnlocked
                      ? "bg-gradient-to-br from-[#171A21] to-[#0F1115] border-[#F7931A]/40 shadow-[0_0_20px_-5px_rgba(247,147,26,0.15)]"
                      : "bg-white/[0.02] border-white/5 opacity-60"
                  }`}
                >
                  <div
                    className={`p-2.5 rounded-lg border flex items-center justify-center shrink-0 ${
                      isUnlocked
                        ? "bg-[#EA580C]/20 border-[#F7931A]/60 text-[#FFD600] shadow-[0_0_10px_rgba(247,147,26,0.5)]"
                        : "bg-white/5 border-white/10 text-white/40"
                    }`}
                  >
                    {isUnlocked ? BADGE_ICONS[badge.icon] || <Award size={20} /> : <Lock size={20} />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <h4
                        className={`text-sm font-heading font-semibold truncate ${
                          isUnlocked ? "text-white" : "text-white/60"
                        }`}
                      >
                        {badge.title}
                      </h4>
                      {isUnlocked && (
                        <span className="flex items-center gap-1 text-[10px] font-mono text-[#34D399]">
                          <CheckCircle2 size={12} />
                          UNLOCKED
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[#94A3B8] mt-1 leading-relaxed">
                      {badge.description}
                    </p>
                    <div className="mt-2 text-[10px] font-mono text-[#FFD600]">
                      +{badge.xpReward} XP Bounty
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
