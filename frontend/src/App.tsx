/**
 * RecoveryOS — Application Router
 *
 * All 6 pages wired to their routes using React Router v6.
 * AppLayout provides the sidebar shell via Outlet.
 */

import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { AuditLogPage } from './pages/AuditLogPage';
import { CaseDetailPage } from './pages/CaseDetail';
import { CommandCenter } from './pages/CommandCenter';
import { PoliciesPage } from './pages/PoliciesPage';
import { RecoveryQueue } from './pages/RecoveryQueue';
import { SimulatorPage } from './pages/SimulatorPage';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          {/* Command Center — primary dashboard */}
          <Route index element={<CommandCenter />} />

          {/* Recovery Queue — case list + case detail */}
          <Route path="recovery-queue" element={<RecoveryQueue />} />
          <Route path="recovery-queue/:caseId" element={<CaseDetailPage />} />

          {/* Simulator — A/B experiment runner */}
          <Route path="simulator" element={<SimulatorPage />} />

          {/* Policies — read-only guardrail config */}
          <Route path="policies" element={<PoliciesPage />} />

          {/* Audit Log — decision trail */}
          <Route path="audit" element={<AuditLogPage />} />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
