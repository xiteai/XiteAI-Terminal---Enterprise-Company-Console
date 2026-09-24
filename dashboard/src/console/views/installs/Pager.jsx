import { num } from "../../../lib/format.js";
import Button from "../../../components/Button.jsx";

export default function Pager({ page, pages, total, onPage }) {
  if (pages <= 1) return null;
  return (
    <div className="pager">
      <span className="muted tnum">Page {page} of {pages} · {num(total)} in all</span>
      <div className="pager-btns">
        <Button size="sm" variant="ghost" icon="chevronLeft" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</Button>
        <Button size="sm" variant="ghost" iconRight="chevronRight" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</Button>
      </div>
    </div>
  );
}
