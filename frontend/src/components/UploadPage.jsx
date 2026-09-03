import { useState } from "react";

const SUPPORTED_PANELS = [
  ["CBC", "Complete Blood Count"],
  ["Blood Glucose", "Fasting/Random + HbA1c"],
  ["Lipid Profile", "Cholesterol"],
  ["LFT", "Liver Function Test"],
  ["KFT/RFT", "Kidney Function"],
  ["Thyroid Profile", ""],
  ["Urinalysis", "Urine R/E"],
  ["Vitamin D & B12", ""],
  ["Electrolytes", ""],
  ["CRP/ESR", "Inflammation Markers"],
];

export default function UploadPage({ onResults, lang, setLangCode, token }) {
  const [file, setFile] = useState(null);
  const [gender, setGender] = useState("");
  const [age, setAge] = useState("");
  const [outputFormat, setOutputFormat] = useState("screen");
  const [abnormalOnly, setAbnormalOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const t = lang;

  function handleFileChange(e) {
    setFile(e.target.files[0] || null);
    setError("");
  }

  function handleDrop(e) {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) { setFile(dropped); setError(""); }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) { setError(t.upload.noFileSelected); return; }

    setLoading(true);
    setError("");

    const formData = new FormData();
    formData.append("file", file);
    if (gender) formData.append("gender", gender);
    if (age) formData.append("age", age);
    formData.append("output_format", outputFormat);
    formData.append("abnormal_only", abnormalOnly ? "true" : "false");

    const headers = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    try {
      const resp = await fetch("/api/analyze-report", {
        method: "POST",
        headers,
        body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || t.upload.analysisFailed);
      }
      const data = await resp.json();
      onResults(data, outputFormat);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell min-h-screen flex flex-col items-center py-8 px-4 sm:py-12">
      <div className="w-full max-w-xl">
        {/* Language toggle */}
        <div className="flex justify-end mb-4">
          <button
            onClick={() => setLangCode(t._code === "en" ? "ur" : "en")}
            className="text-sm px-3 py-1 rounded border border-blue-500 text-blue-600 hover:bg-blue-50"
          >
            {t._code === "en" ? "اردو" : "English"}
          </button>
        </div>

        {/* Intro banner */}
        <div className="intro-panel rounded-xl p-6 sm:p-8 mb-6">
          <div className="eyebrow mb-3">PATIENT REPORT ANALYZER</div>
          <h1 className="text-3xl font-bold mb-2">{t.upload.title}</h1>
          <p className="intro-copy text-sm">{t.upload.subtitle}</p>
          <p className="intro-note text-xs mt-3">{t.upload.disclaimer}</p>
        </div>

        {!token && (
          <p className="text-center text-sm text-yellow-600 mb-4">
            {t.upload.loginPrompt}
          </p>
        )}

        <form onSubmit={handleSubmit} className="upload-card rounded-xl p-5 sm:p-7 space-y-5">
          {/* Drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="drop-zone border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition"
            onClick={() => document.getElementById("file-input").click()}
          >
            <input
              id="file-input"
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.txt"
              className="hidden"
              onChange={handleFileChange}
            />
            {file ? (
              <p className="text-green-600 font-medium">{file.name}</p>
            ) : (
              <>
                <p className="text-gray-500">{t.upload.dragDrop}</p>
                <p className="text-xs text-gray-400 mt-1">{t.upload.supportedFormats}</p>
              </>
            )}
          </div>

          <section className="supported-panel rounded-lg p-5" aria-labelledby="supported-tests-title">
            <div className="section-kicker mb-2">SUPPORTED TESTS</div>
            <h2 id="supported-tests-title" className="text-lg font-semibold mb-2">
              Analyze these 10 test panels
            </h2>
            <p className="supported-disclaimer text-sm mb-4">
              This tool currently supports the 10 test panels listed below. Results for any other test type are not guaranteed to be accurate.
            </p>
            <div className="supported-grid">
              {SUPPORTED_PANELS.map(([name, detail], index) => (
                <div className="supported-test" key={name}>
                  <span className="test-number">{String(index + 1).padStart(2, "0")}</span>
                  <span>
                    <strong>{name}</strong>
                    {detail && <small>{detail}</small>}
                  </span>
                </div>
              ))}
            </div>
          </section>

          {/* Gender */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.upload.genderLabel}
            </label>
            <select
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              className="form-control w-full rounded-lg px-3 py-2 text-sm"
            >
              <option value="">—</option>
              <option value="male">{t.upload.genderMale}</option>
              <option value="female">{t.upload.genderFemale}</option>
            </select>
          </div>

          {/* Age */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.upload.ageLabel}
            </label>
            <input
              type="number"
              min="0"
              max="120"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              placeholder={t.upload.agePlaceholder}
              className="form-control w-full rounded-lg px-3 py-2 text-sm"
            />
          </div>

          {/* Output format */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.upload.outputFormatLabel}
            </label>
            <div className="flex gap-4">
              {["screen", "pdf"].map((fmt) => (
                <label key={fmt} className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="radio"
                    value={fmt}
                    checked={outputFormat === fmt}
                    onChange={() => setOutputFormat(fmt)}
                  />
                  {fmt === "screen" ? t.upload.outputFormatScreen : t.upload.outputFormatPDF}
                </label>
              ))}
            </div>
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={abnormalOnly}
              onChange={(e) => setAbnormalOnly(e.target.checked)}
            />
            {t.upload.abnormalOnly}
          </label>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="primary-button w-full text-white py-2.5 rounded-lg font-semibold transition"
          >
            {loading ? t.upload.analyzing : t.upload.analyzeButton}
          </button>
        </form>
      </div>
    </div>
  );
}
