import { useState } from "react";

export default function UploadPage({ onResults, lang, setLangCode, token }) {
  const [file, setFile] = useState(null);
  const [gender, setGender] = useState("");
  const [age, setAge] = useState("");
  const [outputFormat, setOutputFormat] = useState("screen");
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
    <div className="min-h-screen bg-gray-50 flex flex-col items-center py-10 px-4">
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
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-6 text-center">
          <h1 className="text-3xl font-bold text-blue-700 mb-2">{t.upload.title}</h1>
          <p className="text-gray-600 text-sm">{t.upload.subtitle}</p>
          <p className="text-xs text-gray-400 mt-2">{t.upload.disclaimer}</p>
        </div>

        {!token && (
          <p className="text-center text-sm text-yellow-600 mb-4">
            {t.upload.loginPrompt}
          </p>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow p-6 space-y-5">
          {/* Drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="border-2 border-dashed border-blue-300 rounded-lg p-8 text-center cursor-pointer hover:bg-blue-50 transition"
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

          {/* Gender */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.upload.genderLabel}
            </label>
            <select
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm"
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
              className="w-full border rounded-lg px-3 py-2 text-sm"
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

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-60 transition"
          >
            {loading ? t.upload.analyzing : t.upload.analyzeButton}
          </button>
        </form>
      </div>
    </div>
  );
}
