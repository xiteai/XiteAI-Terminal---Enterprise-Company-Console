import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Spinner from "./components/Spinner.jsx";

// Five doors: the public customer panel, the legal surface, sign-in, joining
// the team, and the console. Each loads on its own so the customer page never
// ships console code.
const PublicPage = lazy(() => import("./pages/public/PublicPage.jsx"));
const CareersPage = lazy(() => import("./pages/careers/CareersPage.jsx"));
const RoleDetail = lazy(() => import("./pages/careers/RoleDetail.jsx"));
const LegalHub = lazy(() => import("./site/legal/LegalHub.jsx"));
const Privacy = lazy(() => import("./site/legal/Privacy.jsx"));
const Terms = lazy(() => import("./site/legal/Terms.jsx"));
const LoginPage = lazy(() => import("./pages/login/LoginPage.jsx"));
const JoinPage = lazy(() => import("./pages/join/JoinPage.jsx"));
const Console = lazy(() => import("./console/Console.jsx"));

function Loading() {
  return (
    <div style={{ height: "100vh", display: "grid", placeItems: "center", color: "var(--muted)" }}>
      <Spinner size={20} delay={300} />
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/" element={<PublicPage />} />
        <Route path="/careers" element={<CareersPage />} />
        <Route path="/careers/:id" element={<RoleDetail />} />
        <Route path="/legal" element={<LegalHub />} />
        <Route path="/legal/privacy" element={<Privacy />} />
        <Route path="/legal/terms" element={<Terms />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/join" element={<JoinPage />} />
        <Route path="/console/*" element={<Console />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
