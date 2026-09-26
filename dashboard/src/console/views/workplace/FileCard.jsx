import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";

// The form at the top of every filing page. The fields differ per kind; the
// frame, the busy state and where the server's "no" appears do not.
export default function FileCard({ title, subtitle, error, busy, onSubmit, submitLabel, children }) {
  return (
    <Card title={title} subtitle={subtitle}>
      <form
        className="wp-form"
        onSubmit={(e) => { e.preventDefault(); onSubmit(); }}
      >
        <div className="wp-fields">{children}</div>
        <ErrorNote error={error} />
        <div className="wp-submit">
          <Button type="submit" variant="primary" busy={busy}>{submitLabel}</Button>
        </div>
      </form>
    </Card>
  );
}
