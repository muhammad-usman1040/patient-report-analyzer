import { useState, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

export default function HistoryPage({ lang, token }) {
  const t = lang;
  const [history, setHistory] = useState(null);
  const [selectedParam, setSelectedParam] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    fetch("/api/history", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then((data) => setHistory(data))
      .catch(() => {
        setError(t.history.loadError);
      })
      .finally(() => setLoading(false));
  }, [token]);

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        {t.history.loginRequired}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400">
        {t.history.loading}
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm max-w-md w-full text-center">
          {error}
        </div>
      </div>
    );
  }

  if (!history) return null;

  const reports = history?.reports || [];
  const trendParams = Object.keys(history.trends || {});
  const activeParam = selectedParam || trendParams[0] || null;
  const trendData = activeParam ? (history.trends[activeParam] || []) : [];

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold text-blue-700">{t.history.title}</h1>

        {reports.length === 0 ? (
          <p className="text-gray-500">{t.history.noHistory}</p>
        ) : (
          <>
            {/* Report list */}
            <section className="space-y-3">
              {reports.map((r) => (
                <div key={r.id} className="bg-white rounded-xl shadow p-4 flex justify-between items-start">
                  <div>
                    <p className="text-sm text-gray-500">
                      {t.history.date}: {new Date(r.report_date).toLocaleDateString()}
                    </p>
                    {r.conditions.length > 0 ? (
                      <p className="text-sm font-medium text-orange-700 mt-1">
                        {t.history.conditions}: {r.conditions.map((c) => c.replace(/_/g, " ")).join(", ")}
                      </p>
                    ) : (
                      <p className="text-sm text-green-600 mt-1">{t.history.allNormal}</p>
                    )}
                  </div>
                </div>
              ))}
            </section>

            {/* Trend charts */}
            {trendParams.length > 0 && (
              <section className="bg-white rounded-xl shadow p-5">
                <h2 className="font-semibold text-gray-700 mb-3">{t.history.trends}</h2>
                <div className="flex flex-wrap gap-2 mb-4">
                  {trendParams.map((p) => (
                    <button
                      key={p}
                      onClick={() => setSelectedParam(p)}
                      className={`px-3 py-1 rounded-full text-sm border ${
                        activeParam === p
                          ? "bg-blue-600 text-white border-blue-600"
                          : "text-gray-600 border-gray-300 hover:bg-gray-50"
                      }`}
                    >
                      {p.replace(/_/g, " ")}
                    </button>
                  ))}
                </div>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="value"
                      name={activeParam?.replace(/_/g, " ")}
                      stroke="#2563eb"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}
