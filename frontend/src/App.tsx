import { UploadForm } from "./components/UploadForm";
import { MapView } from "./components/MapView";
import { DataTable } from "./components/DataTable";
import { useDashboard } from "./hooks/useDashboard";
import "./App.css";

function App() {
  const { loading, progress, error, uploadId, results, view, setView, handleUpload } = useDashboard();

  return (
    <div className="app">
      <header className="hero">
        <div>
          <p className="eyebrow">Worth Rises · Staff Technologist Assignment</p>
          <h1>Prison & Jail Telecom Rate Explorer</h1>
          <p className="subtitle">
            Upload raw provider telecom data. The backend matches each facility to the
            built-in jurisdiction list, writes results to Cloud SQL, and renders them
            on a map or table.
          </p>
        </div>
      </header>

      <main>
        <section className="panel">
          <h2>Upload Data</h2>
          <UploadForm loading={loading} progress={progress} onSubmit={handleUpload} />
          {error && <p className="error">{error}</p>}
        </section>

        {results.length > 0 && (
          <section className="panel">
            <div className="view-tabs">
              <h2>Explore Results</h2>
              <div className="tabs">
                <button
                  type="button"
                  className={view === "map" ? "active" : ""}
                  onClick={() => setView("map")}
                >
                  Map
                </button>
                <button
                  type="button"
                  className={view === "table" ? "active" : ""}
                  onClick={() => setView("table")}
                >
                  Tables
                </button>
              </div>
            </div>
            {view === "map" && <MapView results={results} />}
            {view === "table" && uploadId != null && (
              <DataTable results={results} uploadId={uploadId} />
            )}
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
