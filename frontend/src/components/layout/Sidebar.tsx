/**
 * RecoveryOS — Sidebar Navigation Component
 *
 * The editorial, minimal left sidebar. Playfair Display wordmark,
 * Source Sans 3 nav items. No icons except small geometric indicators.
 */

import { NavLink } from 'react-router-dom';
import styles from './Sidebar.module.css';

const NAV_ITEMS = [
  { path: '/', label: 'Command Center', description: 'Financial overview' },
  { path: '/recovery-queue', label: 'Recovery Queue', description: 'Active cases' },
  { path: '/simulator', label: 'Simulator', description: 'A/B experiments' },
  { path: '/policies', label: 'Policies', description: 'Guardrail config' },
  { path: '/audit', label: 'Audit Log', description: 'Decision trail' },
] as const;

export function Sidebar() {
  return (
    <aside className={styles.sidebar} aria-label="Main navigation">
      {/* Wordmark */}
      <div className={styles.wordmark}>
        <span className={styles.wordmarkPrimary}>Recovery</span>
        <span className={styles.wordmarkAccent}>OS</span>
        <span className={styles.wordmarkVersion}>v1.0</span>
      </div>

      {/* Divider */}
      <hr className="editorial-rule" />

      {/* Navigation */}
      <nav className={styles.nav}>
        <p className={`label-mono ${styles.navLabel}`}>Navigation</p>
        <ul className={styles.navList} role="list">
          {NAV_ITEMS.map(({ path, label, description }) => (
            <li key={path}>
              <NavLink
                to={path}
                end={path === '/'}
                className={({ isActive }) =>
                  `${styles.navItem} ${isActive ? styles.navItemActive : ''}`
                }
                aria-current={undefined}
              >
                <span className={styles.navItemIndicator} aria-hidden="true" />
                <span>
                  <span className={styles.navItemLabel}>{label}</span>
                  <span className={styles.navItemDescription}>{description}</span>
                </span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer */}
      <div className={styles.footer}>
        <hr className="editorial-rule" />
        <p className={styles.footerText}>
          Razorpay AI Buildathon 2025
        </p>
      </div>
    </aside>
  );
}
