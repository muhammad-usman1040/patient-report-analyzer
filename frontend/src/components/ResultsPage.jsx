import { useState } from "react";

export default function ResultsPage({ data, lang, onBack }) {
  const t = lang;
  const { result_state, parameters = data.flagged_parameters || [], conditions = [], disclaimer, unsupported_message, multiple_reports_message } = data;
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState("");

  const statusColor = (status) => {
    if (status === "high") return "bg-red-100 text-red-700 border-red-300";
    if (status === "low") return "bg-yellow-100 text-yellow-700 border-yellow-300";
    return "bg-green-100 text-green-700 border-green-300";
  };

  const statusIcon = (status) => {
    if (status === "high") return "↑";
    if (status === "low") return "↓";
    return "✓";
  };

  const statusLabel = (status) => {
    if (status === "high") return t.results.statusHigh;
    if (status === "low") return t.results.statusLow;
    return t.results.statusNormal;
  };

  async function handleDownloadPDF() {
    setPdfLoading(true);
    setPdfError("");
    try {
      const res = await fetch("/api/generate-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          result_state,
          flagged_parameters: parameters,
          conditions,
          disclaimer,
          language: t._code ?? "en",
        }),
      });
      if (!res.ok) {
        const err = await res.text();
        setPdfError(`${t.results.pdfError}: ${err}`);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${result_state}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setPdfError(`${t.results.pdfError}: ${e.message}`);
    } finally {
      setPdfLoading(false);
    }
  }

  return (
    <div className="app-shell min-h-screen py-8 px-4 sm:py-12">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="results-heading">
          <div className="section-kicker">REPORT REVIEW</div>
          <h1 className="text-2xl font-bold">{t.results.title}</h1>
        </div>

        {/* Analyzed parameters */}
        {parameters.length > 0 && (
          <section>
            <h2 className="font-semibold results-section-title mb-2">{t.results.analyzedParams}</h2>
            <div className="space-y-2">
              {parameters.map((p) => (
                <div
                  key={p.name}
                  className={`result-row flex items-center justify-between border rounded-lg px-4 py-3 ${statusColor(p.status)}`}
                >
                  <span className="font-medium">{p.name}</span>
                  <span className="text-sm">
                    {p.value} {p.unit}
                    <span
                      className="ml-2 font-semibold"
                      aria-label={statusLabel(p.status)}
                    >
                      {statusIcon(p.status)} [{statusLabel(p.status)}]
                    </span>
                    <span className="ml-2 text-xs opacity-70">
                      ({p.normal_min}–{p.normal_max})
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {unsupported_message && (
          <section className="info-alert bg-gray-100 border rounded-lg p-4 text-sm">
            {unsupported_message}
          </section>
        )}

        {multiple_reports_message && (
          <section className="warning-alert bg-yellow-50 border rounded-lg p-4 text-sm">
            {multiple_reports_message}
          </section>
        )}

        {parameters.some((parameter) => parameter.unit_unverified) && (
          <section className="warning-alert bg-yellow-50 border rounded-lg p-4 text-sm">
            Some units could not be verified automatically. Please double-check those results.
          </section>
        )}

        {/* Result state */}
        <section className="result-card rounded-xl p-5 sm:p-6">
          {result_state === "all_normal" && (
            <p className="text-green-600 font-medium">{t.results.allNormal}</p>
          )}
          {result_state === "insufficient_evidence" && (
            <p className="text-gray-500 italic">{t.results.insufficientEvidence}</p>
          )}
          {result_state === "possible_conditions" && conditions.length > 0 && (
            <div>
              <h2 className="font-semibold results-section-title mb-3">{t.results.possibleConditions}</h2>
              <div className="space-y-3">
                {conditions.map((c) => (
                  <div key={c.name} className="condition-card border rounded-lg p-4">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold condition-name">
                        {c.name.replace(/_/g, " ")}
                      </span>
                      <span className="text-sm condition-confidence">
                        {t.results.confidence}: {Math.round(c.confidence * 100)}%
                      </span>
                    </div>
                    {c.supporting_indicators?.length > 0 && (
                      <p className="text-xs text-gray-500 mt-1">
                        {t.results.supportingIndicators}: {c.supporting_indicators.join(", ")}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Disclaimer */}
        <div className="warning-alert border rounded-lg p-4 text-sm">
          ⚕️ {disclaimer || t.results.disclaimer}
        </div>

        {/* PDF error */}
        {pdfError && (
          <p className="text-red-500 text-sm">{pdfError}</p>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onBack}
            className="secondary-button flex-1 border py-2.5 rounded-lg"
          >
            {t.results.backToUpload}
          </button>
          <button
            onClick={handleDownloadPDF}
            disabled={pdfLoading}
            className="primary-button flex-1 text-white py-2.5 rounded-lg disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {pdfLoading ? t.results.generatingPDF : t.results.downloadPDF}
          </button>
        </div>
      </div>
    </div>
  );
}
