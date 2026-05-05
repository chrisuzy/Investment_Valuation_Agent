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
  adminWhoami, setAdminToken, adminClearSection, adminDeleteFile,
} from '../api/client';
import type { DatasetStatus, RefreshReport, FileManifestEntry } from '../api/client';

type UploadKind = 'markets-dataset' | 'damodaran' | 'industry-lookup';

interface PerFileResult {
  name: string;
  ok: boolean;
  savedAs?: string;
  error?: string;
  sizeBytes?: number;
}

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
  // Per-upload-zone feedback. Keyed by UploadKind so each section can
  // display only its own file outcomes.
  const [uploadResults, setUploadResults] = useState<Record<UploadKind, PerFileResult[]>>({
    'markets-dataset': [],
    'damodaran': [],
    'industry-lookup': [],
  });
  // Per-section set of filenames the user has ticked in the file table,
  // for multi-select delete. Using Set (not array) so toggle is O(1).
  const [selectedFiles, setSelectedFiles] = useState<Record<UploadKind, Set<string>>>({
    'markets-dataset': new Set(),
    'damodaran': new Set(),
    'industry-lookup': new Set(),
  });

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
    // Reset this section's results — show a fresh list for this batch.
    setUploadResults((prev) => ({ ...prev, [kind]: [] }));

    const results: PerFileResult[] = [];
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      try {
        const resp = await adminUploadFile(kind, f);
        results.push({
          name: f.name, ok: true, savedAs: resp.filename, sizeBytes: resp.size_bytes,
        });
      } catch (e) {
        // Extract the useful detail — axios wraps the backend's 400/413 body.
        let msg = String(e);
        if (e && typeof e === 'object' && 'response' in e) {
          const axErr = e as { response?: { data?: { detail?: string } } };
          msg = axErr.response?.data?.detail || msg;
        } else if (e instanceof Error) {
          msg = e.message;
        }
        results.push({ name: f.name, ok: false, error: msg });
      }
      // Live-update so the user sees progress file-by-file instead of a
      // single blob at the end.
      setUploadResults((prev) => ({ ...prev, [kind]: [...results] }));
    }
    await refreshStatus();
    setBusy(null);
  }, [refreshStatus]);

  const onClearSection = useCallback(async (kind: UploadKind) => {
    const label = { 'markets-dataset': 'markets dataset',
                    'damodaran': 'Damodaran reference data',
                    'industry-lookup': 'industry lookup' }[kind];
    if (!confirm(`Delete ALL files in "${label}"? This cannot be undone. (The database will stay intact until you click Rebuild.)`)) return;
    setBusy(`clear-${kind}`);
    try {
      const r = await adminClearSection(kind);
      // Reset per-section upload results too so stale ✓/✗ lines go away
      setUploadResults((prev) => ({ ...prev, [kind]: [] }));
      await refreshStatus();
      setReport({ kind: `clear-${kind}`, report: { status: r.status, warnings: [`Removed ${r.count} file(s): ${r.removed.join(', ')}`] } });
    } catch (e) {
      setReport({ kind: `clear-${kind}-error`, report: { status: 'error', warnings: [String(e)] } });
    } finally {
      setBusy(null);
    }
  }, [refreshStatus]);

  const onDeleteFile = useCallback(async (kind: UploadKind, filename: string) => {
    if (!confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    setBusy(`delete-${kind}-${filename}`);
    try {
      await adminDeleteFile(kind, filename);
      setSelectedFiles((prev) => {
        const next = new Set(prev[kind]); next.delete(filename);
        return { ...prev, [kind]: next };
      });
      await refreshStatus();
    } catch (e) {
      setReport({ kind: `delete-${kind}-error`, report: { status: 'error', warnings: [String(e)] } });
    } finally {
      setBusy(null);
    }
  }, [refreshStatus]);

  const toggleFileSelection = useCallback((kind: UploadKind, filename: string) => {
    setSelectedFiles((prev) => {
      const next = new Set(prev[kind]);
      if (next.has(filename)) next.delete(filename);
      else next.add(filename);
      return { ...prev, [kind]: next };
    });
  }, []);

  const toggleSelectAll = useCallback((kind: UploadKind, allFilenames: string[]) => {
    setSelectedFiles((prev) => {
      const current = prev[kind];
      // If every file is already selected → clear. Else → select all.
      const allSelected = allFilenames.length > 0 && allFilenames.every((n) => current.has(n));
      return { ...prev, [kind]: allSelected ? new Set() : new Set(allFilenames) };
    });
  }, []);

  const onDeleteSelected = useCallback(async (kind: UploadKind) => {
    const toDelete = Array.from(selectedFiles[kind]);
    if (toDelete.length === 0) return;
    if (!confirm(`Delete ${toDelete.length} selected file${toDelete.length === 1 ? '' : 's'}? This cannot be undone.`)) return;
    setBusy(`delete-selected-${kind}`);
    const failed: string[] = [];
    for (const f of toDelete) {
      try {
        await adminDeleteFile(kind, f);
      } catch {
        failed.push(f);
      }
    }
    setSelectedFiles((prev) => ({ ...prev, [kind]: new Set(failed) }));  // keep failed ones ticked
    if (failed.length > 0) {
      setReport({ kind: `delete-selected-${kind}-error`, report: { status: 'error', warnings: [`Failed to delete: ${failed.join(', ')}`] } });
    }
    await refreshStatus();
    setBusy(null);
  }, [selectedFiles, refreshStatus]);

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
        onClearSection={onClearSection}
        onDeleteFile={onDeleteFile}
        onDeleteSelected={onDeleteSelected}
        onToggleSelect={toggleFileSelection}
        onToggleSelectAll={toggleSelectAll}
        selectedFiles={selectedFiles}
        results={uploadResults}
      >
        <div className="flex items-center gap-4 pt-2 text-xs flex-wrap">
          <div>
            Active DB:&nbsp;
            {status.database.exists ? (
              <>
                <span className="font-mono">{status.database.company_count.toLocaleString()}</span> companies,
                {' '}<span className="font-mono">{status.database.size_human}</span>
                {status.database.is_seed ? (
                  <span className="ml-1 text-amber-700 font-semibold">(serving shipped seed)</span>
                ) : (
                  <span className="ml-1 text-emerald-700 font-semibold">(admin-built, local)</span>
                )}
              </>
            ) : <span className="text-slate-500">(not built)</span>}
          </div>
          <button
            onClick={() => onRefresh('database')}
            disabled={busy !== null}
            className="ml-auto px-3 py-1.5 bg-blue-600 text-white rounded-md text-xs hover:bg-blue-700 disabled:opacity-40"
          >
            {busy === 'refresh-database' ? '…' : '↻ Rebuild database + seed'}
          </button>
        </div>

        {/* Dual-DB detail block — admin (private) and seed (published). */}
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] font-mono">
          <div className="bg-slate-50 border border-slate-200 rounded p-2">
            <div className="text-[10px] uppercase text-slate-500 mb-1">
              Admin DB (local, gitignored)
            </div>
            {status.database.admin_db_exists ? (
              <>
                <div className="truncate" title={status.database.admin_db_path}>{status.database.admin_db_path}</div>
                <div>{status.database.admin_db_size_human} · mtime {status.database.admin_db_mtime?.replace('T', ' ')}</div>
              </>
            ) : <div className="text-slate-500">(not built)</div>}
          </div>
          <div className="bg-emerald-50 border border-emerald-200 rounded p-2">
            <div className="text-[10px] uppercase text-emerald-700 mb-1">
              Public Seed (committed to repo)
            </div>
            {status.database.seed_exists ? (
              <>
                <div className="truncate" title={status.database.seed_path}>{status.database.seed_path}</div>
                <div>{status.database.seed_size_human} · mtime {status.database.seed_mtime?.replace('T', ' ')}</div>
                <div className="text-emerald-700 mt-1 text-[10px]">
                  After rebuild, git add / commit / push to publish.
                </div>
              </>
            ) : <div className="text-slate-500">(not yet generated)</div>}
          </div>
        </div>

        {status.last_ingest && (
          <div className="mt-2 text-[11px] text-slate-500 font-mono">
            Last ingest: {status.last_ingest.timestamp_utc?.replace('T', ' ').slice(0, 19)} ·
            {' '}{status.last_ingest.duration_ms}ms · {status.last_ingest.n_companies.toLocaleString()} companies
            {status.last_ingest.unmapped_columns.length > 0 && (
              <span className="text-amber-700"> · {status.last_ingest.unmapped_columns.length} unmapped cols</span>
            )}
          </div>
        )}
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
        onClearSection={onClearSection}
        onDeleteFile={onDeleteFile}
        onDeleteSelected={onDeleteSelected}
        onToggleSelect={toggleFileSelection}
        onToggleSelectAll={toggleSelectAll}
        selectedFiles={selectedFiles}
        results={uploadResults}
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
        onClearSection={onClearSection}
        onDeleteFile={onDeleteFile}
        onDeleteSelected={onDeleteSelected}
        onToggleSelect={toggleFileSelection}
        onToggleSelectAll={toggleSelectAll}
        selectedFiles={selectedFiles}
        results={uploadResults}
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
  title, subtitle, files, kind, accept, uploadHelp, multiple, busy,
  onDrop, onClearSection, onDeleteFile, onDeleteSelected,
  onToggleSelect, onToggleSelectAll, selectedFiles, results, children,
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
  onClearSection: (kind: UploadKind) => void;
  onDeleteFile: (kind: UploadKind, filename: string) => void;
  onDeleteSelected: (kind: UploadKind) => void;
  onToggleSelect: (kind: UploadKind, filename: string) => void;
  onToggleSelectAll: (kind: UploadKind, allFilenames: string[]) => void;
  selectedFiles: Record<UploadKind, Set<string>>;
  results: Record<UploadKind, PerFileResult[]>;
  children?: React.ReactNode;
}) {
  const [dragOver, setDragOver] = useState(false);
  const myResults = results[kind];
  const successCount = myResults.filter(r => r.ok).length;
  const failCount = myResults.filter(r => !r.ok).length;
  const selected = selectedFiles[kind];
  const allFilenames = files.map((f) => f.name);
  const allSelected = allFilenames.length > 0 && allFilenames.every((n) => selected.has(n));
  const someSelected = selected.size > 0;

  return (
    <section className="bg-white border border-slate-200 rounded-md p-4">
      <div className="flex items-baseline justify-between mb-1 gap-3">
        <h2 className="font-semibold">{title}</h2>
        {files.length > 0 && (
          <div className="flex items-center gap-4 text-[11px]">
            {someSelected && (
              <button
                onClick={() => onDeleteSelected(kind)}
                disabled={busy !== null}
                className="text-red-700 hover:text-red-800 font-semibold hover:underline disabled:opacity-40"
                title="Delete the checked files. Database stays intact until you click Rebuild."
              >
                {busy === `delete-selected-${kind}` ? 'Deleting…' : `🗑 Delete selected (${selected.size})`}
              </button>
            )}
            <button
              onClick={() => onClearSection(kind)}
              disabled={busy !== null}
              className="text-red-600 hover:text-red-700 hover:underline disabled:opacity-40"
              title="Delete every file in this section."
            >
              {busy === `clear-${kind}` ? 'Deleting…' : `🗑 Delete all ${files.length} file${files.length === 1 ? '' : 's'}`}
            </button>
          </div>
        )}
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

      {/* Per-file result list for the most recent upload batch. Stays visible
          after the upload finishes so the operator can see which files were
          accepted, which were renamed ("foo (1).xls" → "foo.xls"), and which
          were rejected with the reason inline. */}
      {myResults.length > 0 && (
        <div className="mt-3 border border-slate-200 rounded-md overflow-hidden">
          <div className={`px-2 py-1 text-[11px] font-semibold ${
            failCount > 0 ? 'bg-amber-50 text-amber-900 border-b border-amber-200' : 'bg-emerald-50 text-emerald-900 border-b border-emerald-200'
          }`}>
            {successCount} uploaded
            {failCount > 0 && <>, <span className="text-red-700">{failCount} rejected</span></>}
          </div>
          <ul className="text-xs font-mono divide-y divide-slate-100">
            {myResults.map((r, i) => (
              <li key={i} className={`px-2 py-1 flex items-start gap-2 ${r.ok ? '' : 'bg-red-50/60'}`}>
                <span className={r.ok ? 'text-emerald-600' : 'text-red-600'}>
                  {r.ok ? '✓' : '✗'}
                </span>
                <span className="flex-1 break-all">
                  <span className={r.ok ? 'text-slate-700' : 'text-red-900'}>{r.name}</span>
                  {r.ok && r.savedAs && r.savedAs !== r.name && (
                    <span className="text-slate-500"> → saved as {r.savedAs}</span>
                  )}
                  {!r.ok && r.error && (
                    <div className="text-red-700 text-[11px] mt-0.5 whitespace-pre-wrap">{r.error}</div>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {files.length > 0 && (
        <div className="mt-3 text-xs font-mono border border-slate-200 rounded-md overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-[10px] text-slate-500 uppercase">
                <th className="px-2 py-1 text-left" style={{ width: '2rem' }}>
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(el) => { if (el) el.indeterminate = someSelected && !allSelected; }}
                    onChange={() => onToggleSelectAll(kind, allFilenames)}
                    className="cursor-pointer"
                    title={allSelected ? 'Clear all' : 'Select all'}
                  />
                </th>
                <th className="px-2 py-1 text-left font-normal">File</th>
                <th className="px-2 py-1 text-right font-normal" style={{ width: '5rem' }}>Size</th>
                <th className="px-2 py-1 text-right font-normal" style={{ width: '11rem' }}>Modified</th>
                <th style={{ width: '2.5rem' }}></th>
              </tr>
            </thead>
            <tbody>
              {files.map((f) => {
                const deleteBusy = busy === `delete-${kind}-${f.name}`;
                const isSelected = selected.has(f.name);
                return (
                  <tr key={f.name} className={`border-b border-slate-100 last:border-0 ${isSelected ? 'bg-amber-50' : ''}`}>
                    <td className="px-2 py-1">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggleSelect(kind, f.name)}
                        className="cursor-pointer"
                      />
                    </td>
                    <td className="px-2 py-1 text-slate-700 break-all">{f.name}</td>
                    <td className="px-2 py-1 text-right text-slate-500">
                      {fmtBytes(f.size_bytes)}
                    </td>
                    <td className="px-2 py-1 text-right text-slate-500">
                      {f.mtime.replace('T', ' ').slice(0, 16)}
                    </td>
                    <td className="px-2 py-1 text-right">
                      <button
                        onClick={() => onDeleteFile(kind, f.name)}
                        disabled={busy !== null}
                        className="text-red-500 hover:text-red-700 disabled:opacity-30 text-base leading-none"
                        title={`Delete ${f.name}`}
                      >
                        {deleteBusy ? '…' : '🗑'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {children}
    </section>
  );
}
