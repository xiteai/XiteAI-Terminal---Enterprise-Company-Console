import { api } from "../../../lib/api.js";
import { useData } from "../../../lib/useData.js";
import ProfileSections from "../people/ProfileSections.jsx";

// What the company holds about you, exactly as HR sees it.
export default function MyProfile() {
  const { data } = useData(() => api.get("/api/account/profile"), []);
  if (!data) return null;
  return (
    <section className="acc-profile">
      <header className="acc-profile-head">
        <h2 className="t-h2">Your profile</h2>
        <p className="t-note">What XiteAI holds about you, from your sign-up. Ask HR if something needs changing.</p>
      </header>
      <div className="acc-profile-grid">
        <ProfileSections person={{ ...data, full: true, manager: null, reports: [], decided_by: null }} />
      </div>
    </section>
  );
}
