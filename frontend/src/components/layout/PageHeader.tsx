/**
 * RecoveryOS — Page Header Component (Premium Fintech Aesthetic)
 */

import React, { type ReactNode } from "react";
import styles from "./PageHeader.module.css";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  label?: string;            // Monospace eyebrow label
  actions?: ReactNode;       // CTAs / controls
}

export const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, label, actions }) => {
  return (
    <header className={styles.header}>
      <div className={styles.content}>
        {label && (
          <div className={styles.labelWrapper}>
            <span className={styles.labelDot} />
            <p className={styles.label}>{label}</p>
          </div>
        )}
        <h1 className={styles.title}>{title}</h1>
        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
      </div>
      {actions && <div className={styles.actions}>{actions}</div>}
    </header>
  );
};

export default PageHeader;
