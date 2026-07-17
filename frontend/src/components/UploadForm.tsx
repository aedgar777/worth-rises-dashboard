import type { ChangeEvent, CSSProperties } from "react";
import { useEffect, useState } from "react";

interface UploadFormProps {
  loading: boolean;
  progress: number;
  onSubmit: (rawProvider: File) => void;
}

function LoadingEllipsis() {
  const [dotCount, setDotCount] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setDotCount((count) => (count + 1) % 4);
    }, 400);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <span className="upload-ellipsis" aria-hidden="true">
      {".".repeat(dotCount)}
    </span>
  );
}

export function UploadForm({ loading, progress, onSubmit }: UploadFormProps) {
  const [rawProvider, setRawProvider] = useState<File | null>(null);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (rawProvider) {
      onSubmit(rawProvider);
    }
  };

  const buttonStyle = loading
    ? ({ "--upload-progress": `${progress}%` } as CSSProperties)
    : undefined;

  return (
    <form className="upload-form" onSubmit={handleSubmit}>
      <div className="field">
        <input
          id="raw"
          type="file"
          accept=".csv"
          onChange={(e: ChangeEvent<HTMLInputElement>) =>
            setRawProvider(e.target.files?.[0] ?? null)
          }
        />
        <p className="hint">
          Raw telecom provider CSV. Accepts the Worth Rises test format (provider,
          state, county, facility_name, in_state, per_min) or facility-level CSVs
          with in_state_rate and out_of_state_rate columns.
        </p>
      </div>
      <button
        type="submit"
        className={`upload-button${loading ? " is-loading" : ""}`}
        style={buttonStyle}
        disabled={loading || !rawProvider}
        aria-busy={loading}
      >
        <span className="upload-button-label">
          Upload &amp; Generate
          {loading && <LoadingEllipsis />}
        </span>
      </button>
    </form>
  );
}
