/**
 * RecoveryOS — Application Router
 *
 * All 6 operational pages wired to their routes using React Router v6.
 * AppLayout provides the operational sidebar shell via Outlet.
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
          {/* Command Center — primary financial dashboard */}
          <Route index element={<CommandCenter />} />

          {/* Recovery Queue — case list + case forensic detail */}
          <Route path="recovery-queue" element={<RecoveryQueue />} />
          <Route path="recovery-queue/:caseId" element={<CaseDetailPage />} />

          {/* Recovery Simulation Lab — A/B evaluation against baseline retry */}
          <Route path="simulator" element={<SimulatorPage />} />

          {/* Guardrails & Policies — merchant policy and financial bounds */}
          <Route path="policies" element={<PoliciesPage />} />

          {/* Decision Audit — complete decision & verification timeline */}
          <Route path="audit" element={<AuditLogPage />} />
          <Route path="audit/:caseId" element={<AuditLogPage />} />

          {/* Catch-all redirect to Command Center */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
