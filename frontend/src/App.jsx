import { useState } from "react";
import UploadPage from "./components/UploadPage.jsx";
import ResultsPage from "./components/ResultsPage.jsx";
import HistoryPage from "./components/HistoryPage.jsx";
import en from "./locales/en.json";
import ur from "./locales/ur.json";

const LOCALES = { en, ur };

export default function App() {
  const [page, setPage] = useState("upload");
  const [results, setResults] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem("token") || "");
  const [langCode, setLangCode] = useState("en");
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authError, setAuthError] = useState("");

  const lang = LOCALES[langCode] || en;
  const t = lang;
  const isRtl = langCode === "ur";

  function handleResults(data, outputFormat) {
    setResults({ data, outputFormat });
    setPage("results");
  }

  function handleBack() {
    setResults(null);
    setPage("upload");
  }

  function handleLogout() {
    setToken("");
    localStorage.removeItem("token");
  }

  async function handleAuthSubmit(e) {
    e.preventDefault();
    setAuthError("");
    const endpoint = authMode === "login" ? "/api/auth/login" : "/api/auth/register";
    try {
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail, password: authPassword }),
      });
      if (!resp.ok) {
        setAuthError(authMode === "login" ? t.auth.loginError : t.auth.registerError);
        return;
      }
      const data = await resp.json();
      if (data.access_token) {
        setToken(data.access_token);
        localStorage.setItem("token", data.access_token);
        setShowAuth(false);
        setAuthEmail("");
        setAuthPassword("");
      }
    } catch {
      setAuthError(authMode === "login" ? t.auth.loginError : t.auth.registerError);
    }
  }

  return (
    <div dir={isRtl ? "rtl" : "ltr"} className="font-sans">
      {/* Nav */}
      <nav className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex gap-4">
          <button
            onClick={() => setPage("upload")}
            className={`text-sm font-medium ${page === "upload" ? "text-blue-600" : "text-gray-600 hover:text-blue-500"}`}
          >
            {t.nav.upload}
          </button>
          <button
            onClick={() => setPage("history")}
            className={`text-sm font-medium ${page === "history" ? "text-blue-600" : "text-gray-600 hover:text-blue-500"}`}
          >
            {t.nav.history}
          </button>
        </div>
        <div className="flex items-center gap-3">
          {token ? (
            <button
              onClick={handleLogout}
              className="text-sm text-gray-600 hover:text-red-500"
            >
              {t.nav.logout}
            </button>
          ) : (
            <>
              <button
                onClick={() => { setAuthMode("login"); setShowAuth(true); }}
                className="text-sm text-blue-600 hover:underline"
              >
                {t.nav.login}
              </button>
              <button
                onClick={() => { setAuthMode("register"); setShowAuth(true); }}
                className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
              >
                {t.nav.register}
              </button>
            </>
          )}
        </div>
      </nav>

      {/* Pages */}
      {page === "upload" && (
        <UploadPage
          onResults={handleResults}
          lang={lang}
          setLangCode={setLangCode}
          token={token}
        />
      )}
      {page === "results" && results && (
        <ResultsPage
          data={results.data}
          lang={lang}
          onBack={handleBack}
        />
      )}
      {page === "history" && (
        <HistoryPage lang={lang} token={token} />
      )}

      {/* Auth modal */}
      {showAuth && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-sm">
            <h2 className="text-lg font-bold text-gray-800 mb-4">
              {authMode === "login" ? t.auth.loginTitle : t.auth.registerTitle}
            </h2>
            <form onSubmit={handleAuthSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t.auth.emailLabel}
                </label>
                <input
                  type="email"
                  required
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t.auth.passwordLabel}
                </label>
                <input
                  type="password"
                  required
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              {authError && <p className="text-red-500 text-sm">{authError}</p>}
              <button
                type="submit"
                className="w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700"
              >
                {authMode === "login" ? t.auth.loginButton : t.auth.registerButton}
              </button>
            </form>
            <p className="text-center text-sm text-gray-500 mt-4">
              <button
                onClick={() => { setAuthMode(authMode === "login" ? "register" : "login"); setAuthError(""); }}
                className="text-blue-600 hover:underline"
              >
                {authMode === "login" ? t.auth.switchToRegister : t.auth.switchToLogin}
              </button>
            </p>
            <button
              onClick={() => { setShowAuth(false); setAuthError(""); }}
              className="absolute top-3 right-4 text-gray-400 hover:text-gray-600 text-lg"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
