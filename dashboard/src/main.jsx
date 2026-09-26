import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { MotionConfig } from "framer-motion";
// Type, self-hosted: no request to Google at runtime. Inter for everything;
// codes and versions use its even-width figures, not a second face.
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "./styles/fonts.css";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/art.css";
import App from "./App.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import { ToastProvider } from "./components/Toast.jsx";
import UpdateNotice from "./components/UpdateNotice.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <MotionConfig reducedMotion="user">
      <BrowserRouter>
        <ToastProvider>
          <ErrorBoundary resetKey="app">
            <App />
          </ErrorBoundary>
          <UpdateNotice />
        </ToastProvider>
      </BrowserRouter>
    </MotionConfig>
  </React.StrictMode>,
);
