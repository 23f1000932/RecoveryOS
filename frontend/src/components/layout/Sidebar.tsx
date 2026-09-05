/**
 * RecoveryOS — Bitcoin DeFi Sidebar Navigation
 */

import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Layers,
  Cpu,
  ShieldCheck,
  FileCode2,
  Zap,
} from "lucide-react";
import styles from "./Sidebar.module.css";

const NAV_ITEMS = [
  {
    path: "/",
    label: "Command Center",
    description: "Financial Alpha & Metrics",
    icon: LayoutDashboard,
  },
  {
    path: "/recovery-queue",
    label: "Recovery Queue",
    description: "Real-time Interventions",
    icon: Layers,
  },
  {
    path: "/simulator",
    label: "Mining Simulator",
    description: "Stress Test & A/B Engine",
    icon: Cpu,
  },
  {
    path: "/policies",
    label: "Smart Guardrails",
    description: "Policy & Limit Engine",
    icon: ShieldCheck,
  },
  {
    path: "/audit",
    label: "Ledger Audit",
    description: "Immutable Decision Trail",
    icon: FileCode2,
  },
] as const;

export const Sidebar: React.FC = () => {
  return (
    <aside className={styles.sidebar} aria-label="Main navigation">
      {/* Brand Header */}
      <div className={styles.wordmark}>
        <div className={styles.logoContainer}>
          <div className={styles.logoOrb}>
            <Zap size={16} className="text-[#030304] fill-[#030304]" />
          </div>
          <div>
            <div className={styles.logoText}>
              <span className={styles.brandTitle}>Recovery</span>
              <span className={styles.brandAccent}>OS</span>
            </div>
            <span className={styles.rigBadge}>DEFI MINING RIG</span>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className={styles.nav}>
        <p className={styles.navSectionLabel}>Core Protocol</p>
        <ul className={styles.navList} role="list">
          {NAV_ITEMS.map(({ path, label, description, icon: Icon }) => (
            <li key={path}>
              <NavLink
                to={path}
                end={path === "/"}
                className={({ isActive }) =>
                  `${styles.navItem} ${isActive ? styles.navItemActive : ""}`
                }
              >
                <div className={styles.iconWrapper}>
                  <Icon size={17} />
                </div>
                <div className={styles.itemText}>
                  <span className={styles.navItemLabel}>{label}</span>
                  <span className={styles.navItemDescription}>{description}</span>
                </div>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Cryptographic Rig Status Footer */}
      <div className={styles.footer}>
        <div className={styles.statusBox}>
          <div className={styles.statusRow}>
            <span className={styles.statusDot} />
            <span className={styles.statusText}>ENGINE ONLINE</span>
          </div>
          <div className={styles.systemMetrics}>
            <span>BLOCK: 840,219</span>
            <span>PING: 14ms</span>
          </div>
        </div>
        <p className={styles.copyrightText}>Razorpay AI Buildathon</p>
      </div>
    </aside>
  );
};
export default Sidebar;
