import { useSession } from "../../../lib/session.jsx";
import Avatar from "../../../components/Avatar.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import DemoData from "./DemoData.jsx";
import MyProfile from "./MyProfile.jsx";
import AuthenticatorCard from "./AuthenticatorCard.jsx";
import PasswordCard from "./PasswordCard.jsx";
import PhotoCard from "./PhotoCard.jsx";
import Sessions from "./Sessions.jsx";
import "./Account.css";

export default function Account() {
  const { me, can } = useSession();
  const u = me.user;
  return (
    <div className="stack">
      <PageHeader lead={<Avatar src={u.avatar_url} initials={u.initials} level={u.level} size={44} />} title={u.display_name}
        subtitle={`${u.title || u.level_label}${u.department ? `, ${u.department}` : ""} · ${u.email}`}
        meta={<span>{me.customer_visibility}</span>} />
      <div className="grid-2">
        <PhotoCard />
        <PasswordCard />
        <Sessions />
      </div>
      <AuthenticatorCard />
      {can("demo.manage") && <DemoData />}
      <MyProfile />
    </div>
  );
}
