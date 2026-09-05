/**
 * RecoveryOS — DeFi Recovery Hunter Gamification Engine
 * Tracks Hunter XP, Levels, Streak Multipliers, and Cryptographic Badges.
 */

import confetti from "canvas-confetti";

export interface HunterBadge {
  id: string;
  title: string;
  description: string;
  icon: string; // icon identifier
  xpReward: number;
  category: "forensics" | "mining" | "guardrail" | "speed";
}

export const ALL_BADGES: HunterBadge[] = [
  {
    id: "GENESIS_ANALYSIS",
    title: "Genesis Analysis",
    description: "Executed your first AI payment failure forensics scan.",
    icon: "ShieldAlert",
    xpReward: 100,
    category: "forensics",
  },
  {
    id: "WHALE_SAVER",
    title: "Whale Rescuer",
    description: "Approved and safeguarded a high-value recovery transaction (> ₹10,000).",
    icon: "Coins",
    xpReward: 350,
    category: "mining",
  },
  {
    id: "ZERO_BREACH",
    title: "Guardian Protocol",
    description: "Successfully processed cases with zero guardrail limit violations.",
    icon: "ShieldCheck",
    xpReward: 250,
    category: "guardrail",
  },
  {
    id: "HASHRATE_SURGE",
    title: "Hashrate Surge",
    description: "Completed a batch stress test yielding positive net incremental alpha.",
    icon: "Cpu",
    xpReward: 400,
    category: "mining",
  },
  {
    id: "LIGHTNING_EXECUTE",
    title: "Lightning Execute",
    description: "Safely deployed recovery adapter without human intervention delays.",
    icon: "Zap",
    xpReward: 200,
    category: "speed",
  },
  {
    id: "CONSENSUS_STREAK",
    title: "Consensus Master",
    description: "Maintained a 5x uninterrupted successful recovery streak.",
    icon: "Flame",
    xpReward: 500,
    category: "mining",
  },
];

export interface HunterState {
  xp: number;
  level: number;
  rankTitle: string;
  nextLevelXP: number;
  currentLevelXP: number;
  streak: number;
  multiplier: number;
  totalBounty: number;
  unlockedBadges: string[];
}

export interface XPToastEvent {
  id: string;
  xpAdded: number;
  reason: string;
  multiplier: number;
  isLevelUp?: boolean;
}

const STORAGE_KEY = "recoveryos_hunter_state";

const LEVEL_THRESHOLDS = [
  { level: 1, xp: 0, title: "Node Validator" },
  { level: 2, xp: 500, title: "Block Sentry" },
  { level: 3, xp: 1500, title: "Hashrate Hunter" },
  { level: 4, xp: 3500, title: "Whale Rescuer" },
  { level: 5, xp: 7500, title: "Consensus Overlord" },
];

function getLevelInfo(xp: number) {
  let current = LEVEL_THRESHOLDS[0];
  let next = LEVEL_THRESHOLDS[1];

  for (let i = LEVEL_THRESHOLDS.length - 1; i >= 0; i--) {
    if (xp >= LEVEL_THRESHOLDS[i].xp) {
      current = LEVEL_THRESHOLDS[i];
      next = LEVEL_THRESHOLDS[i + 1] || { level: current.level, xp: current.xp * 2, title: current.title };
      break;
    }
  }

  return {
    level: current.level,
    rankTitle: current.title,
    currentLevelXP: current.xp,
    nextLevelXP: next.xp,
  };
}

class GamificationManager {
  private state: HunterState;
  private listeners: Set<(state: HunterState) => void> = new Set();
  private toastListeners: Set<(toast: XPToastEvent) => void> = new Set();

  constructor() {
    this.state = this.loadState();
  }

  private loadState(): HunterState {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        const info = getLevelInfo(parsed.xp || 0);
        return {
          xp: parsed.xp || 0,
          level: info.level,
          rankTitle: info.rankTitle,
          currentLevelXP: info.currentLevelXP,
          nextLevelXP: info.nextLevelXP,
          streak: parsed.streak || 0,
          multiplier: parsed.multiplier || 1.0,
          totalBounty: parsed.totalBounty || 0,
          unlockedBadges: parsed.unlockedBadges || [],
        };
      }
    } catch {
      // ignore parsing error
    }

    const info = getLevelInfo(150); // initial starter XP
    return {
      xp: 150,
      level: info.level,
      rankTitle: info.rankTitle,
      currentLevelXP: info.currentLevelXP,
      nextLevelXP: info.nextLevelXP,
      streak: 1,
      multiplier: 1.0,
      totalBounty: 0,
      unlockedBadges: ["GENESIS_ANALYSIS"],
    };
  }

  private persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
    } catch {
      // ignore storage quota error
    }
    this.listeners.forEach((l) => l({ ...this.state }));
  }

  public getState(): HunterState {
    return { ...this.state };
  }

  public subscribe(fn: (state: HunterState) => void): () => void {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  }

  public onToast(fn: (toast: XPToastEvent) => void): () => void {
    this.toastListeners.add(fn);
    return () => {
      this.toastListeners.delete(fn);
    };
  }

  public addXP(baseXP: number, reason: string, bountyAmount: number = 0) {
    const prevLevel = this.state.level;
    const earnedXP = Math.round(baseXP * this.state.multiplier);
    const newXP = this.state.xp + earnedXP;
    const newBounty = this.state.totalBounty + bountyAmount;

    // Check level progression
    const levelInfo = getLevelInfo(newXP);
    const isLevelUp = levelInfo.level > prevLevel;

    this.state = {
      ...this.state,
      xp: newXP,
      level: levelInfo.level,
      rankTitle: levelInfo.rankTitle,
      currentLevelXP: levelInfo.currentLevelXP,
      nextLevelXP: levelInfo.nextLevelXP,
      totalBounty: newBounty,
    };

    this.persist();

    // Trigger toast
    const toast: XPToastEvent = {
      id: Math.random().toString(36).substring(2, 9),
      xpAdded: earnedXP,
      reason,
      multiplier: this.state.multiplier,
      isLevelUp,
    };
    this.toastListeners.forEach((fn) => fn(toast));

    if (isLevelUp) {
      this.fireCelebration(true);
    }
  }

  public incrementStreak() {
    const nextStreak = this.state.streak + 1;
    // Multiplier scales: 1x, 1.2x, 1.5x, 2.0x, max 3.0x
    let nextMult = 1.0;
    if (nextStreak >= 5) nextMult = 3.0;
    else if (nextStreak >= 4) nextMult = 2.0;
    else if (nextStreak >= 3) nextMult = 1.5;
    else if (nextStreak >= 2) nextMult = 1.2;

    this.state = {
      ...this.state,
      streak: nextStreak,
      multiplier: nextMult,
    };
    this.persist();

    if (nextStreak === 5) {
      this.unlockBadge("CONSENSUS_STREAK");
    }
  }

  public resetStreak() {
    if (this.state.streak > 0) {
      this.state = {
        ...this.state,
        streak: 0,
        multiplier: 1.0,
      };
      this.persist();
    }
  }

  public unlockBadge(badgeId: string) {
    if (!this.state.unlockedBadges.includes(badgeId)) {
      const badge = ALL_BADGES.find((b) => b.id === badgeId);
      this.state = {
        ...this.state,
        unlockedBadges: [...this.state.unlockedBadges, badgeId],
      };
      this.persist();

      if (badge) {
        this.addXP(badge.xpReward, `Badge Unlocked: ${badge.title}`);
        this.fireCelebration(false);
      }
    }
  }

  public fireCelebration(isMajor: boolean = false) {
    try {
      const colors = ["#F7931A", "#EA580C", "#FFD600", "#FFFFFF"];
      if (isMajor) {
        confetti({
          particleCount: 80,
          spread: 80,
          origin: { y: 0.6 },
          colors,
          disableForReducedMotion: true,
        });
      } else {
        confetti({
          particleCount: 35,
          spread: 50,
          origin: { y: 0.7 },
          colors,
          disableForReducedMotion: true,
        });
      }
    } catch {
      // ignore
    }
  }
}

export const gamification = new GamificationManager();
