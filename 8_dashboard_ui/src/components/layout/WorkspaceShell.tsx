import { Outlet } from 'react-router-dom';
import { FloatingNav } from './FloatingNav';
import { Worldspace } from '@/components/atmosphere/Worldspace';

/**
 * WorkspaceShell — persistent operational chrome.
 *
 *  • Worldspace lives below everything — never unmounts on navigation, so
 *    route changes feel like the camera moving inside one continuous space.
 *  • FloatingNav sits on top of pages but below modal overlays.
 *  • Pages render at full viewport between them.
 */
export function WorkspaceShell() {
  return (
    <div className="h-screen w-screen overflow-hidden bg-[var(--color-void)] text-[var(--color-text-primary)] relative">
      <Worldspace />
      <FloatingNav />
      <main className="absolute inset-0 overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
