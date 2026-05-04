/**
 * Admin Data Sources page — the ONE place an operator uploads new screener
 * files, new Damodaran releases, or a refreshed industry lookup. Refresh
 * buttons trigger deterministic-Python ingest; refresh summary rendered
 * inline so operator can read the report without SSH.
 *
 * Access: requires AD_CC_ADMIN_TOKEN env var set on the server + the
 * corresponding token stored in localStorage (see setAdminToken). Non-admin
 * users never reach this route — the sidebar hides the link entirely.
 *
 * Zero LLM in the refresh loop; see plan §6d/§6g.
 */

import { useEffect, useState, useCallback } from 'react';
import {
  adminDatasetStatus, adminUploadFile, adminRefreshDatabase, adminRefreshKnowledgeBase,
  adminWhoami, setAdminToken,
} from '../api/client';
import type { DatasetStatus, RefreshReport, FileManifestEntry } from '../api/client';

type UploadKind = 'markets-dataset' | 'damodaran' | 'industry-lookup';

function fmtBytes(n: number): string {
  if (n < 1024) return `${n}B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)}KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)}MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(1)}GB`;
}

export default function AdminDataSources() {
  const [status, setStatus] = useState<DatasetStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [report, setReport] = useState<{ kind: string; report: RefreshReport } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [tokenInput, setTokenInput] = useState('');

  const refreshStatus = useCallback(async () => {
    setLoading(true);
    setAuthError(null);
    try {
      const who = await adminWhoami();
      if (!who.configured) {
        setAuthError('Admin features are not configured on the server. Set AD_CC_ADMIN_TOKEN env var and restart.');
        setLoading(false);
        return;
      }
      if (!who.admin) {
        setAuthError('Enter your admin token to manage data sources.');
        setLoading(false);
        return;
      }
      const s = await adminDatasetStatus();
      setStatus(s);
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refreshStatus(); }, [refreshStatus]);

  const onDrop = useCallback(async (kind: UploadKind, files: FileList | null) => {
    if (!files || files.length === 0) return;
    setBusy(`upload-${kind}`);
    try {
      for (let i = 0; i < files.length; i++) {
        await adminUploadFile(kind, files[i]);
      }
      await refreshStatus();
    } catch (e) {
      setReport({ kind: `upload-${kind}-error`, report: { status: 'error', warnings: [String(e)] } });
    } finally {
      setBusy(null);
    }
  }, [refreshStatus]);

  const onRefresh = async (which: 'database' | 'knowledge-base') => {
    setBusy(`refresh-${which}`);
    try {
      const r = which === 'database'
        ? await adminRefreshDatabase()
        : await adminRefreshKnowledgeBase();
      setReport({ kind: which, report: r });
      await refreshStatus();
    } catch (e) {
      setReport({ kind: `refresh-${which}-error`, report: { status: 'error', warnings: [String(e)] } });
    } finally {
      setBusy(null);
    }
  };

  const saveToken = () => {
    if (tokenInput.trim()) {
      setAdminToken(tokenInput.trim());
      setTokenInput('');
      void refreshStatus();
    }
  };

  if (loading) {
    return <div className="p-6 text-slate-600 text-sm">Loading admin status…</div>;
  }

  if (authError) {
    return (
      <div className="max-w-lg mx-auto p-6 space-y-4">
        <h1 className="text-xl font-bold">Admin Data Sources</h1>
        <div className="bg-amber-50 border border-amber-300 rounded-md p-3 text-sm text-amber-900">
          {authError}
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-sm text-slate-700">Admin token:</label>
          <input
            type="password"
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') saveToken(); }}
            placeholder="paste AD_CC_ADMIN_TOKEN value"
            className="border border-slate-300 rounded-md px-3 py-2 font-mono text-sm"
          />
          <button
            onClick={saveToken}
            disabled={!tokenInput.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-40"
          >
            Save & verify
          </button>
          <button
            onClick={() => { setAdminToken(null); void refreshStatus(); }}
            className="text-xs text-slate-500 hover:text-slate-700"
          >
            Clear stored token
          </button>
        </div>
      </div>
    );
  }

  if (!status) return null;

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Data Sources</h1>
        <button
          onClick={() => { setAdminToken(null); void refreshStatus(); }}
          className="text-xs text-slate-500 hover:text-slate-700"
          title="Clear the stored admin token from this browser."
        >
          Sign out
        </button>
      </div>

      <p className="text-sm text-slate-600">
        Upload new data files by dropping them into the relevant section. Files save to
        the server filesystem; click the refresh button to rebuild the database or reload
        the in-memory singletons. All operations are deterministic Python — no LLM.
      </p>

      {/* === SECTION 1 — Markets Dataset === */}
      <DataSourceSection
        title="Markets Dataset — CIQ Screener"
        subtitle={`Folder: ${status.markets_dataset.folder}`}
        files={status.markets_dataset.files}
        kind="markets-dataset"
        accept=".xls,.xlsx"
        uploadHelp="Filename must match ginzu_cc_<screener>_<part>.xls (e.g. ginzu_cc_1_1.xls)"
        multiple={true}
        busy={busy}
        onDrop={onDrop}
      >
        <div className="flex items-center gap-4 pt-2 text-xs">
          <div>
            Database:&nbsp;
            {status.database.exists ? (
              <>
                <span className="font-mono">{status.database.company_count.toLocaleString()}</span> companies,
                {' '}<span className="font-mono">{status.database.size_human}</span>
              </>
            ) : <span className="text-slate-500">(not built)</span>}
          </div>
          {status.last_ingest && (
            <div className="text-slate-500">
              Last built: <span className="font-mono">{status.last_ingest.timestamp_utc?.replace('T', ' ').slice(0, 19)}</span> ·
              {' '}<span className="font-mono">{status.last_ingest.duration_ms}ms</span>
            </div>
          )}
          <button
            onClick={() => onRefresh('database')}
            disabled={busy !== null}
            className="ml-auto px-3 py-1.5 bg-blue-600 text-white rounded-md text-xs hover:bg-blue-700 disabled:opacity-40"
          >
            {busy === 'refresh-database' ? '…' : '↻ Rebuild database'}
          </button>
        </div>
      </DataSourceSection>

      {/* === SECTION 2 — Damodaran reference data === */}
      <DataSourceSection
        title="Damodaran Reference Data"
        subtitle={`Folder: ${status.knowledge_base_damodaran.folder}`}
        files={status.knowledge_base_damodaran.files}
        kind="damodaran"
        accept=".xls,.xlsx"
        uploadHelp="Any of the Damodaran annual-update files (betaGlobal.xls, capex.xls, margin.xls, countrystats.xls, etc.). Filename determines which slot it replaces."
        multiple={true}
        busy={busy}
        onDrop={onDrop}
      >
        <div className="flex items-center gap-4 pt-2 text-xs">
          <div>{status.knowledge_base_damodaran.files.length} files</div>
          <button
            onClick={() => onRefresh('knowledge-base')}
            disabled={busy !== null}
            className="ml-auto px-3 py-1.5 bg-blue-600 text-white rounded-md text-xs hover:bg-blue-700 disabled:opacity-40"
          >
            {busy === 'refresh-knowledge-base' ? '…' : '↻ Reload Damodaran + industry lookup'}
          </button>
        </div>
      </DataSourceSection>

      {/* === SECTION 3 — Industry lookup === */}
      <DataSourceSection
        title="Industry Lookup"
        subtitle={`Folder: ${status.industry_lookup.folder}`}
        files={status.industry_lookup.files}
        kind="industry-lookup"
        accept=".xlsx"
        uploadHelp="indname.xlsx — ticker → Damodaran industry mapping."
        multiple={false}
        busy={busy}
        onDrop={onDrop}
      />

      {/* === Last refresh report === */}
      {report && (
        <section className="bg-slate-50 border border-slate-200 rounded-md p-4 text-xs">
          <h2 className="font-semibold text-sm mb-2">Last refresh — {report.kind}</h2>
          <pre className="whitespace-pre-wrap font-mono text-[11px] text-slate-800 overflow-x-auto">
            {JSON.stringify(report.report, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// DataSourceSection — reusable section with drop zone + file list
// ---------------------------------------------------------------------------

function DataSourceSection({
  title, subtitle, files, kind, accept, uploadHelp, multiple, busy, onDrop, children,
}: {
  title: string;
  subtitle: string;
  files: FileManifestEntry[];
  kind: UploadKind;
  accept: string;
  uploadHelp: string;
  multiple: boolean;
  busy: string | null;
  onDrop: (kind: UploadKind, files: FileList | null) => void;
  children?: React.ReactNode;
}) {
  const [dragOver, setDragOver] = useState(false);

  return (
    <section className="bg-white border border-slate-200 rounded-md p-4">
      <div className="flex items-baseline justify-between mb-1">
        <h2 className="font-semibold">{title}</h2>
      </div>
      <div className="text-xs text-slate-500 font-mono mb-3">{subtitle}</div>

      <label
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          onDrop(kind, e.dataTransfer.files);
        }}
        className={`block border-2 border-dashed rounded-md p-6 text-center cursor-pointer transition-colors ${
          dragOver ? 'border-blue-500 bg-blue-50' : 'border-slate-300 bg-slate-50 hover:bg-slate-100'
        } ${busy === `upload-${kind}` ? 'opacity-50' : ''}`}
      >
        <input
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={(e) => onDrop(kind, e.target.files)}
          className="hidden"
        />
        <div className="text-sm text-slate-700">
          {busy === `upload-${kind}` ? 'Uploading…' : '📁 Drop files here or click to browse'}
        </div>
        <div className="text-[11px] text-slate-500 mt-1">{uploadHelp}</div>
      </label>

      {files.length > 0 && (
        <div className="mt-3 text-xs font-mono border border-slate-200 rounded-md overflow-hidden">
          <table className="w-full">
            <tbody>
              {files.map((f) => (
                <tr key={f.name} className="border-b border-slate-100 last:border-0">
                  <td className="px-2 py-1 text-slate-700">{f.name}</td>
                  <td className="px-2 py-1 text-right text-slate-500" style={{ width: '5rem' }}>
                    {fmtBytes(f.size_bytes)}
                  </td>
                  <td className="px-2 py-1 text-right text-slate-500" style={{ width: '11rem' }}>
                    {f.mtime.replace('T', ' ').slice(0, 16)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {children}
    </section>
  );
}
