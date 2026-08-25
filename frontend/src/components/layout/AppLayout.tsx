/**
 * RecoveryOS — App Layout Shell
 * Sidebar + main content area.
 */

import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import styles from './AppLayout.module.css';

export function AppLayout() {
  return (
    <div className={styles.layout}>
      <Sidebar />
      <main className={styles.main} id="main-content">
        <Outlet />
      </main>
    </div>
  );
}
