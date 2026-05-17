import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { FloatingNav } from './FloatingNav';
import { Worldspace } from '@/components/atmosphere/Worldspace';
import { InvestigationLaunchSequence } from '@/components/atmosphere/InvestigationLaunchSequence';
import { useIntelStore } from '@/store/intel-store';

/**
 * WorkspaceShell — persistent operational chrome.
 *
 *  • Worldspace lives below everything — never unmounts on navigation, so
 *    route changes feel like the camera moving inside one continuous space.
 *  • FloatingNav sits on top of pages but below modal overlays.
 *  • InvestigationLaunchSequence is a non-blocking top strip that surfaces
 *    in-flight custom investigations across all pages.
 *  • Pages render at full viewport between them.
 *
 *  • Sets a global `data-investigation-scan` attribute on <html> whenever
 *    a live investigation is in flight. The CSS layer hooks this to subtly
 *    intensify atmosphere (slight grid breathe, soft scan veil). All
 *    intensification is bound to the REAL backend stream state — there is
 *    no decorative timer.
 *
 *  • Owns the orchestrator connectivity probe. The probe MUST live here
 *    (not inside an optional BackendStatusPill) because every page that
 *    consumes `backendStatus` (CustomInvestigationInput, LiveLaunchpad,
 *    DataSources…) needs the probe running regardless of whether the pill
 *    is mounted. Runs immediately on shell mount, then every 20s.
 */
export function WorkspaceShell() {
  const liveStreamPhase = useIntelStore((s) => s.liveStreamPhase);
  const cognitivePhase = useIntelStore((s) => s.cognitivePhase);
  const checkBackend = useIntelStore((s) => s.checkBackend);
  const loadLivePresets = useIntelStore((s) => s.loadLivePresets);

  // World scan attribute — bound to real investigation state
  useEffect(() => {
    if (typeof document === 'undefined') return;
    const root = document.documentElement;
    const active =
      liveStreamPhase === 'streaming' || cognitivePhase === 'running';
    if (active) {
      root.setAttribute('data-investigation-scan', 'active');
    } else {
      root.removeAttribute('data-investigation-scan');
    }
  }, [liveStreamPhase, cognitivePhase]);

  // Orchestrator connectivity probe — runs for the lifetime of the shell.
  useEffect(() => {
    let cancelled = false;
    let presetsLoaded = false;

    const tick = async () => {
      if (cancelled) return;
      await checkBackend();
      if (cancelled) return;
      // Lazy-load the curated preset list once after the first successful
      // probe so LiveLaunchpad has data without spamming the API.
      const st = useIntelStore.getState();
      if (st.backendStatus && !presetsLoaded && st.livePresets.length === 0) {
        await loadLivePresets();
        presetsLoaded = true;
      }
    };

    tick();
    const id = setInterval(tick, 20_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [checkBackend, loadLivePresets]);

  return (
    <div className="h-screen w-screen overflow-hidden bg-[var(--color-void)] text-[var(--color-text-primary)] relative">
      <Worldspace />
      <FloatingNav />
      <InvestigationLaunchSequence />
      <main className="absolute inset-0 overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
