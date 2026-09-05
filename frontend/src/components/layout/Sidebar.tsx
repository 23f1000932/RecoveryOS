/**
 * RecoveryOS — Premium Fintech Operational Sidebar
 * Strict adherence to Sections 9 and 39 of the Master Specification.
 */

import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Layers,
  FlaskConical,
  ShieldCheck,
  FileText,
  Activity,
} from "lucide-react";
import styles from "./Sidebar.module.css";

interface NavGroup {
  groupLabel: string;
  items: {
    path: string;
    label: string;
    icon: React.ComponentType<{ size?: number; className?: string }>;
  }[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    groupLabel: "Overview",
    items: [
      {
        path: "/",
        label: "Command Center",
        icon: LayoutDashboard,
      },
    ],
  },
  {
    groupLabel: "Recovery",
    items: [
      {
        path: "/recovery-queue",
        label: "Recovery Queue",
        icon: Layers,
      },
    ],
  },
  {
    groupLabel: "Intelligence",
    items: [
      {
        path: "/simulator",
        label: "Recovery Simulator",
        icon: FlaskConical,
      },
    ],
  },
  {
    groupLabel: "Governance",
    items: [
      {
        path: "/policies",
        label: "Guardrails & Policies",
        icon: ShieldCheck,
      },
    ],
  },
  {
    groupLabel: "Audit",
    items: [
      {
        path: "/audit",
        label: "Decision Audit",
        icon: FileText,
      },
    ],
  },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className={styles.sidebar} aria-label="Main navigation">
      {/* Brand Header */}
      <div className={styles.wordmark}>
        <div className={styles.logoContainer}>
          <div className={styles.logoOrb}>
            <Activity size={18} color="#080C14" />
          </div>
          <div>
            <div className={styles.logoText}>
              <span className={styles.brandTitle}>Recovery</span>
              <span className={styles.brandAccent}>OS</span>
            </div>
            <span className={styles.brandDescriptor}>AI Revenue Recovery</span>
          </div>
        </div>
      </div>

      {/* Navigation Sections */}
      <nav className={styles.nav}>
        {NAV_GROUPS.map((group) => (
          <div key={group.groupLabel} className={styles.navSection}>
            <p className={styles.navSectionLabel}>{group.groupLabel}</p>
            <ul className={styles.navList} role="list">
              {group.items.map(({ path, label, icon: Icon }) => (
                <li key={path}>
                  <NavLink
                    to={path}
                    end={path === "/"}
                    className={({ isActive }) =>
                      `${styles.navItem} ${isActive ? styles.navItemActive : ""}`
                    }
                  >
                    <div className={styles.iconWrapper}>
                      <Icon size={16} />
                    </div>
                    <div className={styles.itemText}>
                      <span className={styles.navItemLabel}>{label}</span>
                    </div>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* Operational Footer */}
      <div className={styles.footer}>
        <div className={styles.statusCard}>
          <div className={styles.statusRow}>
            <span className={styles.statusLabel}>Recovery Engine</span>
            <div className={styles.statusIndicator}>
              <span className={styles.statusDot} />
              <span>OPERATIONAL</span>
            </div>
          </div>
          <div className={styles.statusMeta}>
            <span>RAZORPAY TEST MODE</span>
            <span style={{ color: "var(--success-text)" }}>Connected</span>
          </div>
        </div>
        <p className={styles.footerSubtext}>Built for Razorpay payment recovery</p>
      </div>
    </aside>
  );
};

export default Sidebar;
