import { Component, type ErrorInfo, type ReactNode } from "react";

/**
 * Lightweight containment for a single UI section. A throw inside `children`
 * renders `fallback` instead of unmounting the whole page (and with it the
 * global navigation). This is defense-in-depth only — the underlying data
 * shape should still be normalized so it never throws in the first place.
 */
export default class ErrorBoundary extends Component<
  { children: ReactNode; fallback?: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("UI section failed to render", error, info.componentStack);
  }

  render() {
    if (this.state.failed) return this.props.fallback ?? null;
    return this.props.children;
  }
}
