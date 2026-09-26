// Turning a chosen file into an avatar, in the browser.
//
// The crop and compress happen here rather than on the server so a 12 MB
// phone photo never crosses the network: what leaves is a square a few tens
// of kilobytes wide. Shared by sign-up and the account page, so both send
// exactly the same shape and the server only has to know one rule.

const OUT = 360;

const readFile = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(reader.result);
  reader.onerror = reject;
  reader.readAsDataURL(file);
});

const loadImage = (src) => new Promise((resolve, reject) => {
  const img = new Image();
  img.onload = () => resolve(img);
  img.onerror = reject;
  img.src = src;
});

// Centre-cropped square, resized, JPEG. Returns a data URL.
export async function toAvatar(file) {
  const raw = await readFile(file);
  const img = await loadImage(raw);
  const side = Math.min(img.width, img.height);
  const canvas = document.createElement("canvas");
  canvas.width = OUT;
  canvas.height = OUT;
  canvas.getContext("2d").drawImage(
    img, (img.width - side) / 2, (img.height - side) / 2, side, side, 0, 0, OUT, OUT);
  return canvas.toDataURL("image/jpeg", 0.85);
}
