import type { ReactElement } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { BootSequence } from '@/pages/BootSequence';
import { Autopilot } from '@/pages/Autopilot';
import { Manual } from '@/pages/Manual';
import { BenchmarkShootout } from '@/pages/BenchmarkShootout';
import { SessionVault } from '@/pages/SessionVault';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';
import { Home } from '@/pages/Home';
import { Alerts } from '@/pages/Alerts';
import { Rings } from '@/pages/Rings';
import { EntityIndex } from '@/pages/EntityIndex';
import { EntityDossier } from '@/pages/EntityDossier';
import { Reports } from '@/pages/Reports';
import { Replay } from '@/pages/Replay';
import { DataSources } from '@/pages/DataSources';
import { Simulate } from '@/pages/Simulate';
import { Methodology } from '@/pages/Methodology';
import { ErrorBoundary } from '@/components/shared/ErrorBoundary';

/**
 * Routing map.
 *
 *   /                   boot sequence (no chrome) — first visit only, then → /home
 *   /autopilot          cinematic theater (no chrome — full-bleed)
 *
 *   --- WorkspaceShell (persistent nav rail) ---
 *   /home               command center
 *   /investigate        manual workstation
 *   /benchmark          benchmark lab
 *   /rings              ring analysis
 *   /alerts             live monitoring
 *   /entities           entity dossier index
 *   /entity/:id         per-entity dossier
 *   /replay  /replay/:id  investigation replay
 *   /reports            dossier index
 *   /reports/:id        case dossier
 *   /sessions           session vault (analyst archive)
 */
/** Helper — wraps a page in a named ErrorBoundary so a render exception
 *  on one route degrades to a panel instead of blacking the whole shell. */
const guard = (name: string, node: ReactElement): ReactElement => (
  <ErrorBoundary name={name}>{node}</ErrorBoundary>
);

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Shell-less */}
        <Route path="/" element={guard('BootSequence', <BootSequence />)} />
        <Route path="/autopilot" element={guard('Autopilot', <Autopilot />)} />

        {/* Operational shell — each route is independently guarded so a
            page-level render error doesn't take down the workspace nav. */}
        <Route element={<WorkspaceShell />}>
          <Route path="/home" element={guard('Home', <Home />)} />
          <Route path="/investigate" element={guard('Manual', <Manual />)} />
          <Route path="/benchmark" element={guard('BenchmarkShootout', <BenchmarkShootout />)} />
          <Route path="/rings" element={guard('Rings', <Rings />)} />
          <Route path="/alerts" element={guard('Alerts', <Alerts />)} />
          <Route path="/entities" element={guard('EntityIndex', <EntityIndex />)} />
          <Route path="/entity/:id" element={guard('EntityDossier', <EntityDossier />)} />
          <Route path="/replay" element={guard('Replay', <Replay />)} />
          <Route path="/replay/:id" element={guard('Replay', <Replay />)} />
          <Route path="/reports" element={guard('Reports', <Reports />)} />
          <Route path="/reports/:id" element={guard('Reports', <Reports />)} />
          <Route path="/sessions" element={guard('SessionVault', <SessionVault />)} />
          <Route path="/sources" element={guard('DataSources', <DataSources />)} />
          <Route path="/simulate" element={guard('Simulate', <Simulate />)} />
          <Route path="/methodology" element={guard('Methodology', <Methodology />)} />
        </Route>

        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
