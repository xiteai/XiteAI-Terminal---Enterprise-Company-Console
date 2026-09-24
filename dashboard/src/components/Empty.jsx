import Icon from "./Icon.jsx";
import "./Empty.css";

// `icon` is accepted for older callers but not drawn: the words carry it.
// eslint-disable-next-line no-unused-vars
export default function Empty({ icon, title, children, action }) {
  return (
    <div className="empty">
      <p className="empty-title">{title}</p>
      {children && <p className="empty-text">{children}</p>}
      {action && <div className="empty-action">{action}</div>}
    </div>
  );
}

export function ErrorNote({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="error-note" role="alert">
      <Icon name="alert" size={16} />
      <span>{error.message || String(error)}</span>
      {onRetry && <button onClick={onRetry}>Try again</button>}
    </div>
  );
}
