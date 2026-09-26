import { useRef, useState } from "react";
import Icon from "../../components/Icon.jsx";

const OUT = 360;          // square, small enough that even a big photo compresses to well under the server's cap

function readFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

// A centre-cropped, resized square, compressed client-side before it ever
// reaches the server — a photo, not a multi-megabyte file upload.
async function toAvatar(file) {
  const raw = await readFile(file);
  const img = await loadImage(raw);
  const side = Math.min(img.width, img.height);
  const sx = (img.width - side) / 2;
  const sy = (img.height - side) / 2;
  const canvas = document.createElement("canvas");
  canvas.width = OUT;
  canvas.height = OUT;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, sx, sy, side, side, 0, 0, OUT, OUT);
  return canvas.toDataURL("image/jpeg", 0.85);
}

export default function PhotoCapture({ value, onChange, error }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState(null);

  const pick = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!file.type.startsWith("image/")) { setLocalError("That's not an image."); return; }
    setBusy(true);
    setLocalError(null);
    try {
      onChange(await toAvatar(file));
    } catch {
      setLocalError("Couldn't read that photo. Try another.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="jphoto">
      <button type="button" className="jphoto-well" onClick={() => inputRef.current?.click()} disabled={busy}>
        {value ? <img src={value} alt="Your photo" /> : (
          <span className="jphoto-empty">
            <Icon name="user" size={28} />
            <span>{busy ? "Working…" : "Add photo"}</span>
          </span>
        )}
      </button>
      <input ref={inputRef} type="file" accept="image/*" capture="user" hidden onChange={pick} />
      <div className="jphoto-actions">
        <button type="button" className="jphoto-btn" onClick={() => inputRef.current?.click()}>
          {value ? "Retake" : "Take or choose a photo"}
        </button>
        {value && <button type="button" className="jphoto-btn jphoto-clear" onClick={() => onChange("")}>Remove</button>}
      </div>
      {(error || localError) && <p className="pill-note" role="alert">{error || localError}</p>}
    </div>
  );
}
