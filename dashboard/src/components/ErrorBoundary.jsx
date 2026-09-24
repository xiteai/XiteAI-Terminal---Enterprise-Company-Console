import { Component } from "react";
import Button from "./Button.jsx";
import Icon from "./Icon.jsx";
import "./ErrorBoundary.css";

// The reason a page can go dead after an action and stay dead until you
// refresh: something a render touched wasn't there (a field the server left
// out, a list not yet loaded), React throws, and with nothing catching it the
// whole page stops responding — clicks, everything. This is the catch: one
// broken view shows a plain error instead, the rest of the console (the
// sidebar, the other pages) keeps working, and Try again re-renders without a
// full reload. `resetKey` (Shell passes the page's route) clears it the
// moment you navigate away, so it never traps you on a page you've left.
export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("A screen stopped responding:", error, info.componentStack);
  }

  componentDidUpdate(prev) {
    if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null });
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="eb">
        <Icon name="alert" size={22} />
        <p className="eb-title">This page hit a snag.</p>
        <p className="eb-text">Nothing else was affected — the sidebar still works. Try again, or reload the page.</p>
        <div className="eb-buttons">
          <Button variant="primary" onClick={() => this.setState({ error: null })}>Try again</Button>
          <Button onClick={() => window.location.reload()}>Reload the page</Button>
        </div>
      </div>
    );
  }
}
