import { forwardRef, useState } from "react";
import { cx } from "../../lib/cx.js";

// The one big field: a soft floating pill, as in Stephen's onboarding, with an
// optional fixed suffix (the email domain) and a show/hide for passwords.
const PillInput = forwardRef(function PillInput(
  { value, onChange, onEnter, placeholder, type = "text", suffix, error, label, textarea, lower, ...rest },
  ref,
) {
  const [reveal, setReveal] = useState(false);
  const isPw = type === "password";
  const Tag = textarea ? "textarea" : "input";
  return (
    <label className={cx("pill", error && "pill-error", textarea && "pill-area")}>
      {label && <span className="pill-label">{label}</span>}
      <span className="pill-box">
        <Tag
          ref={ref}
          className="pill-input"
          type={isPw && reveal ? "text" : type}
          value={value || ""}
          placeholder={placeholder}
          spellCheck={false}
          aria-invalid={error ? true : undefined}
          onChange={(e) => onChange(lower ? e.target.value.toLowerCase().replace(/\s/g, "") : e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (!textarea || e.ctrlKey || e.metaKey)) { e.preventDefault(); onEnter?.(); }
          }}
          {...rest}
        />
        {suffix && <span className="pill-suffix">{suffix}</span>}
        {isPw && (
          <button type="button" className="pill-show" onClick={() => setReveal((r) => !r)}>
            {reveal ? "Hide" : "Show"}
          </button>
        )}
      </span>
      {error && <span className="pill-note" role="alert">{error}</span>}
    </label>
  );
});

export default PillInput;
