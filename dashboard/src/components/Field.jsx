import { forwardRef, useId } from "react";
import { cx } from "../lib/cx.js";
import Icon from "./Icon.jsx";
import "./Field.css";

// A labelled input. `suffix` sits inside the box (e.g. "@xos1.com"); `error`
// replaces the hint and turns the box red; `textarea` swaps the element.
const Field = forwardRef(function Field(
  { label, hint, error, icon, suffix, prefix, textarea = false, className, id, ...rest },
  ref,
) {
  const auto = useId();
  const fieldId = id || auto;
  const Tag = textarea ? "textarea" : "input";
  return (
    <label className={cx("field", error && "field-error", icon === "search" && "field-search", className)} htmlFor={fieldId}>
      {label && <span className="field-label">{label}</span>}
      <span className={cx("field-box", textarea && "field-box-area")}>
        {icon && <Icon name={icon} size={16} className="field-icon" />}
        {prefix && <span className="field-affix">{prefix}</span>}
        <Tag
          ref={ref}
          id={fieldId}
          className="field-input"
          aria-invalid={error ? true : undefined}
          aria-describedby={error || hint ? `${fieldId}-note` : undefined}
          {...rest}
        />
        {suffix && <span className="field-affix field-suffix">{suffix}</span>}
      </span>
      {(error || hint) && (
        <span id={`${fieldId}-note`} className={cx("field-note", error && "field-note-error")}>
          {error || hint}
        </span>
      )}
    </label>
  );
});

export default Field;
