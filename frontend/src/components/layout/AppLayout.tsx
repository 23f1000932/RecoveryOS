/**
 * RecoveryOS — Premium Fintech App Layout Shell
 * Pure operational layout for enterprise revenue recovery.
 */

import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import styles from "./AppLayout.module.css";

export function AppLayout() {
  return (
    <div className={styles.layout}>
      {/* Persistent Operational Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className={styles.contentContainer}>
        {/* Top Operational Status Bar */}
        <header className={styles.topHeader}>
          <div className={styles.headerLeft}>
            <div className={styles.engineStatus}>
              <span className={styles.pulseDot} />
              <span>RECOVERY ENGINE</span>
              <span style={{ color: "var(--success-text)", fontWeight: 700 }}>OPERATIONAL</span>
            </div>

            <div className={styles.environmentBadge}>
              <span>PAYMENT ENVIRONMENT:</span>
              <span style={{ color: "#FFFFFF" }}>RAZORPAY TEST MODE</span>
            </div>
          </div>

          <div className={styles.headerRight}>
            <div className={styles.systemMetaItem}>
              <span>API STATUS:</span>
              <span className={styles.systemMetaVal} style={{ color: "var(--success-text)" }}>
                CONNECTED
              </span>
            </div>
            <div className={styles.systemMetaItem}>
              <span>MERCHANT CONTEXT:</span>
              <span className={styles.systemMetaVal}>RAZORPAY_DEMO</span>
            </div>
          </div>
        </header>

        <main className={styles.main} id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default AppLayout;
