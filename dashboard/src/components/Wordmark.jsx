import { cx } from "../lib/cx.js";
import "./Wordmark.css";

// The company mark: XiteAI's X, the name, and which tool this is.
export default function Wordmark({ sub = "Terminal", inline = false, size = 26 }) {
  return (
    <span className={cx("wordmark", inline && "wordmark-inline")}>
      <img className="wordmark-logo" src="/brand/xiteai.png" alt="" style={{ width: size, height: size }} />
      <span className="wordmark-name">
        <b>XiteAI</b>
        {sub && <small>{sub}</small>}
      </span>
    </span>
  );
}
