/**
 * RecoveryOS — App Layout Shell with Bitcoin DeFi Atmosphere & Gamification
 */

import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { HunterHUD } from "../gamification/HunterHUD";
import { TrophyModal } from "../gamification/TrophyModal";
import { XPToast } from "../gamification/XPToast";
import { gamification } from "../../services/gamification";
import type { HunterState } from "../../services/gamification";
import styles from "./AppLayout.module.css";

export function AppLayout() {
  const [isTrophyOpen, setIsTrophyOpen] = useState(false);
  const [hunterState, setHunterState] = useState<HunterState>(gamification.getState());

  useEffect(() => {
    return gamification.subscribe(setHunterState);
  }, []);

  return (
    <div className={styles.layout}>
      {/* Ambient background energy blobs */}
      <div className={styles.ambientGlowTop} aria-hidden="true" />
      <div className={styles.ambientGlowBottom} aria-hidden="true" />

      {/* Persistent Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className={styles.contentContainer}>
        {/* Top Floating Utility & Gamification Bar */}
        <header className={styles.topHeader}>
          <div className={styles.headerNetworkBadge}>
            <span className={styles.pulseDot} />
            <span className="font-mono text-xs text-[#94A3B8]">
              NETWORK: <strong className="text-white">BITCOIN MAINNET / TESTNET</strong>
            </span>
          </div>

          <HunterHUD onOpenTrophies={() => setIsTrophyOpen(true)} />
        </header>

        <main className={styles.main} id="main-content">
          <Outlet />
        </main>
      </div>

      {/* Gamification Floating Elements */}
      <XPToast />
      <TrophyModal
        isOpen={isTrophyOpen}
        onClose={() => setIsTrophyOpen(false)}
        state={hunterState}
      />
    </div>
  );
}

export default AppLayout;
