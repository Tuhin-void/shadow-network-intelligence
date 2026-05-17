import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';

/**
 * ErrorBoundary — catches render-time exceptions and shows a degraded
 * panel instead of unmounting the whole page tree (the cause of the
 * "Sources page goes black after upload" failure mode).
 *
 * Usage:
 *   <ErrorBoundary name="DataSources">
 *     <DataSources />
 *   </ErrorBoundary>
 *
 * The boundary is intentionally NOT silent — it surfaces the actual
 * error message + stack so an evaluator can see what failed. Reset
 * button clears the error state and re-attempts to render the children.
 */

interface Props {
  name: string;
  /** Optional inline fallback (replaces the default panel). */
  fallback?: (err: Error, reset: () => void) => ReactNode;
  children: ReactNode;
}

interface State {
  err: Error | null;
  info: string | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { err: null, info: null };

  static getDerivedStateFromError(err: Error): State {
    return { err, info: null };
  }

  componentDidCatch(err: Error, info: ErrorInfo): void {
    // Log to the dev console so it shows in browser dev tools too.
    // eslint-disable-next-line no-console
    console.error(
      `[ErrorBoundary:${this.props.name}] caught render error:`,
      err,
      info?.componentStack,
    );
    this.setState({ err, info: info?.componentStack ?? null });
  }

  reset = (): void => {
    this.setState({ err: null, info: null });
  };

  render(): ReactNode {
    if (this.state.err) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.err, this.reset);
      }
      return (
        <div className="fill overflow-y-auto scroll-tactical">
          <div className="px-6 pt-16 pb-10 mx-auto" style={{ maxWidth: 880 }}>
            <div className="surface px-5 py-4 border-l-2 border-[var(--color-rose-500)]">
              <div className="flex items-start gap-3">
                <AlertOctagon
                  className="w-4 h-4 text-[var(--color-rose-400)] mt-0.5 shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <div className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-rose-400)]">
                    panel runtime error · {this.props.name}
                  </div>
                  <div className="text-[13px] text-[var(--color-text-bright)] font-light mt-1">
                    {this.state.err.message ||
                      'an unexpected render error occurred'}
                  </div>
                  <p className="text-[11.5px] text-[var(--color-text-secondary)] mt-2 leading-relaxed">
                    The rest of the application is unaffected — navigate via
                    the sidebar or try resetting this panel. If the error
                    persists, the orchestrator API response shape may have
                    changed; rebuild the dashboard or report the issue.
                  </p>
                  {this.state.info && (
                    <details className="mt-3">
                      <summary className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] cursor-pointer hover:text-[var(--color-rose-400)]">
                        component stack
                      </summary>
                      <pre className="mt-2 font-mono text-[10px] text-[var(--color-text-muted)] whitespace-pre-wrap break-all max-h-72 overflow-y-auto panel-soft p-2">
                        {this.state.info}
                      </pre>
                    </details>
                  )}
                  <button
                    onClick={this.reset}
                    className="mt-3 h-7 px-3 inline-flex items-center gap-2 rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.12)] text-[10px] font-mono tracking-[0.26em] uppercase"
                  >
                    <RotateCcw className="w-3 h-3" />
                    reset panel
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
