import { useRef, useState } from "react";
import { api } from "../../../lib/api.js";
import { toAvatar } from "../../../lib/photo.js";
import { useSession } from "../../../lib/session.jsx";
import Avatar from "../../../components/Avatar.jsx";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import { useToast } from "../../../components/Toast.jsx";

// Your photo. Cropped square and compressed here before it's sent, so a
// twelve-megabyte phone picture never crosses the network.
export default function PhotoCard() {
  const toast = useToast();
  const { me, refresh } = useSession();
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const current = me.user.avatar_url;

  const pick = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!file.type.startsWith("image/")) { setError({ message: "That's not an image." }); return; }
    setBusy(true);
    setError(null);
    try {
      await api.put("/api/account/photo", { photo: await toAvatar(file) });
      await refresh();
      toast("Photo updated.");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.del("/api/account/photo");
      await refresh();
      toast("Photo removed.");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Photo" subtitle="Shows beside your name across the console.">
      <div className="ac-photo">
        <Avatar src={current} initials={me.user.initials} level={me.user.level} size={72} />
        <div className="ac-photo-actions">
          <Button size="sm" busy={busy} onClick={() => inputRef.current?.click()}>
            {current ? "Change photo" : "Add a photo"}
          </Button>
          {current && <Button size="sm" variant="quiet" onClick={remove} disabled={busy}>Remove</Button>}
          <input ref={inputRef} type="file" accept="image/*" hidden onChange={pick} />
        </div>
      </div>
      <ErrorNote error={error} />
    </Card>
  );
}
