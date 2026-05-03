import { Component, type ReactNode, type ErrorInfo } from 'react';
import { Link } from 'react-router-dom';

/**
 * Guard against any single page throwing during render so the whole app
 * doesn't unmount (which would wipe `data` state in App.tsx and force the
 * user to re-upload the CIQ file).
 *
 * Wrap the <Routes> block in App.tsx with this. When a page throws:
 *  - the sidebar and wizard state are preserved (App didn't crash)
 *  - user sees a fallback with a "Back to Input Sheet" link
 *  - the raw error is shown for debugging
 *  - a reset button allows retrying the same page (resets `error` state)
 *
 * The `resetKey` prop lets the caller force a reset when `data` changes,
 * so a successful re-upload clears any stale boundary state automatically.
 */

interface Props {
  children: ReactNode;
  /** When this value changes, the boundary clears any caught error. */
  resetKey?: unknown;
}

interface State {
  error: Error | null;
  info: ErrorInfo | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, info: null };

  static getDerivedStateFromError(error: Error): State {
    return { error, info: null };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Keep the stack in devtools console for debugging
    console.error('[ErrorBoundary] page crashed:', error, info);
    this.setState({ error, info });
  }

  componentDidUpdate(prevProps: Props) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null, info: null });
    }
  }

  private handleReset = () => {
    this.setState({ error: null, info: null });
  };

  render() {
    if (!this.state.error) return this.props.children;

    const message = this.state.error.message || String(this.state.error);
    const componentStack = this.state.info?.componentStack?.trim() ?? '';

    return (
      <div className="max-w-3xl mx-auto my-8 p-6 bg-white border border-rose-200 rounded-lg shadow-sm">
        <div className="flex items-start gap-3">
          <div className="text-3xl leading-none">⚠</div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-rose-700">This page crashed</h2>
            <p className="text-sm text-slate-600 mt-1">
              Your valuation data and other pages are still intact — only this page hit an error while rendering.
              Use the buttons below to recover, or open DevTools console for the full stack trace.
            </p>
          </div>
        </div>

        <div className="mt-4 rounded-md bg-slate-50 border border-slate-200 p-3">
          <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Error</div>
          <pre className="text-xs text-rose-700 whitespace-pre-wrap font-mono">{message}</pre>
          {componentStack && (
            <>
              <div className="text-xs text-slate-500 uppercase tracking-wide mt-3 mb-1">Where</div>
              <pre className="text-[10px] text-slate-600 whitespace-pre-wrap font-mono overflow-x-auto max-h-40">{componentStack}</pre>
            </>
          )}
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            to="/"
            onClick={this.handleReset}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            ← Back to Input Sheet
          </Link>
          <button
            onClick={this.handleReset}
            className="px-3 py-1.5 text-sm bg-slate-100 text-slate-700 rounded border border-slate-300 hover:bg-slate-200"
          >
            Retry this page
          </button>
        </div>
      </div>
    );
  }
}
