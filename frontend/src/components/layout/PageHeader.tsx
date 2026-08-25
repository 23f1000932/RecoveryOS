/**
 * RecoveryOS — Page Header Component
 * Consistent editorial header for all pages.
 * Title in Playfair Display, subtitle in Source Sans 3.
 */

import type { ReactNode } from 'react';
import styles from './PageHeader.module.css';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  label?: string;            // IBM Plex Mono eyebrow label
  actions?: ReactNode;       // Buttons / controls for the right side
}

export function PageHeader({ title, subtitle, label, actions }: PageHeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.content}>
        {label && (
          <p className={`label-mono ${styles.label}`} aria-hidden="true">
            {label}
          </p>
        )}
        <h1 className={styles.title}>{title}</h1>
        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
      </div>
      {actions && <div className={styles.actions}>{actions}</div>}
      <hr className="editorial-rule" style={{ marginTop: '1.5rem' }} />
    </header>
  );
}
