// Join class names, skipping falsy ones: cx("btn", on && "on").
export const cx = (...parts) => parts.filter(Boolean).join(" ");
