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
function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Shell-less */}
        <Route path="/" element={<BootSequence />} />
        <Route path="/autopilot" element={<Autopilot />} />

        {/* Operational shell */}
        <Route element={<WorkspaceShell />}>
          <Route path="/home" element={<Home />} />
          <Route path="/investigate" element={<Manual />} />
          <Route path="/benchmark" element={<BenchmarkShootout />} />
          <Route path="/rings" element={<Rings />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/entities" element={<EntityIndex />} />
          <Route path="/entity/:id" element={<EntityDossier />} />
          <Route path="/replay" element={<Replay />} />
          <Route path="/replay/:id" element={<Replay />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/reports/:id" element={<Reports />} />
          <Route path="/sessions" element={<SessionVault />} />
          <Route path="/sources" element={<DataSources />} />
          <Route path="/simulate" element={<Simulate />} />
          <Route path="/methodology" element={<Methodology />} />
        </Route>

        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
