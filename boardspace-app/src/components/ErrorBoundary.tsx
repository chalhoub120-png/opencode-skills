import { Component, type ErrorInfo, type ReactNode } from 'react';

type Props = { children: ReactNode };
type State = { failed: boolean };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Keep diagnostics useful without sending private workspace content to a logger.
    console.error('Unhandled application rendering error', error.name, info.componentStack);
  }

  render() {
    if (this.state.failed) {
      return <main className="fatal-state"><div className="brand-mark">B</div><h1>Something went wrong</h1><p>Your workspace data has not been deleted. Reload the page to try again.</p><button className="button button-primary" onClick={() => window.location.reload()} type="button">Reload app</button></main>;
    }
    return this.props.children;
  }
}
