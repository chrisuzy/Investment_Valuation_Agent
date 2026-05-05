import { useState, useRef, useEffect } from 'react';
import {
  searchCompanies, downloadTemplate, fetchFromFile,
  companyExists, valueFromDatabase, adminWhoami,
} from '../api/client';
import type { SearchResult } from '../api/client';
import type { ValuationResponse } from '../types/valuation';

/**
 * 4-step onboarding wizard for starting a new valuation.
 *
 *   Step 1 — Search & select a company
 *   Step 2 — Download the pre-filled data template (ticker baked in)
 *   Step 3 — User fills the template locally (Excel + Capital IQ plugin)
 *   Step 4 — Upload the completed file; backend runs the valuation
 *
 * Only the current step is visible. Completed steps collapse to a compact
 * summary with a "change" link for back-nav. The user cannot skip ahead.
 */

type Step = 1 | 2 | 3 | 4;

interface Props {
  onComplete: (response: ValuationResponse) => void;
  onDemo: () => void;
}

export default function OnboardingWizard({ onComplete, onDemo }: Props) {
  const [step, setStep] = useState<Step>(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [selectedCompany, setSelectedCompany] = useState<SearchResult | null>(null);

  const [templateDownloaded, setTemplateDownloaded] = useState(false);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);

  // DB-backed path: when the selected company is in the ingested markets DB,
  // offer an instant valuation without the template round-trip.
  const [dbStatus, setDbStatus] = useState<{ inDb: boolean; dataAsOf: string | null } | null>(null);
  const [loadingFromDb, setLoadingFromDb] = useState(false);

  // Whether this deployment has admin configured (i.e. the author's own
  // instance). Determines whether step 2 shows the download button
  // (author flow) or just the "contact the maintainer" 4-step
  // instructions (public-clone flow).
  const [adminConfigured, setAdminConfigured] = useState(false);
  useEffect(() => {
    adminWhoami().then(w => setAdminConfigured(w.configured)).catch(() => setAdminConfigured(false));
  }, []);

  useEffect(() => {
    if (!selectedCompany) { setDbStatus(null); return; }
    let cancelled = false;
    companyExists(selectedCompany.exchange_ticker)
      .then((r) => { if (!cancelled) setDbStatus({ inDb: r.in_database, dataAsOf: r.data_as_of }); })
      .catch(() => { if (!cancelled) setDbStatus({ inDb: false, dataAsOf: null }); });
    return () => { cancelled = true; };
  }, [selectedCompany]);

  async function triggerValueFromDb() {
    if (!selectedCompany) return;
    setLoadingFromDb(true);
    setError(null);
    try {
      const resp = await valueFromDatabase(selectedCompany.exchange_ticker);
      onComplete(resp);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Database valuation failed');
    } finally {
      setLoadingFromDb(false);
    }
  }

  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── step 1: search ──
  async function runSearch() {
    const q = searchQuery.trim();
    if (!q) return;
    setSearching(true);
    setError(null);
    setSearchResults(null);
    try {
      const results = await searchCompanies(q);
      setSearchResults(results);
      if (results.length === 1) {
        // Auto-select when unique — one click saves a step
        setSelectedCompany(results[0]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setSearching(false);
    }
  }

  function pickCompany(c: SearchResult) {
    setSelectedCompany(c);
  }

  function proceedToStep2() {
    if (!selectedCompany) return;
    setStep(2);
    setError(null);
  }

  // ── step 2: download template ──
  async function triggerDownload() {
    if (!selectedCompany) return;
    setDownloadingTemplate(true);
    setError(null);
    try {
      await downloadTemplate(selectedCompany.exchange_ticker);
      setTemplateDownloaded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Download failed');
    } finally {
      setDownloadingTemplate(false);
    }
  }

  function proceedToStep3() {
    setStep(3);
    setError(null);
  }

  // ── step 3: user fills locally, then clicks "Ready to upload" ──
  function proceedToStep4() {
    setStep(4);
    setError(null);
  }

  // ── step 4: upload ──
  async function handleFile(file: File) {
    if (!file) return;
    // Reject non-Excel files up front — saves a round-trip.
    const okExt = /\.(xlsx|xls)$/i.test(file.name);
    if (!okExt) {
      setError('Please upload a .xlsx or .xls file.');
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const resp = await fetchFromFile(file, 'US', 0.0425);
      onComplete(resp);
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axErr = err as { response?: { data?: { detail?: string } } };
        setError(axErr.response?.data?.detail || 'Failed to load file');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load file');
      }
    } finally {
      setUploading(false);
    }
  }

  const handleUploadChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // Reset the input so re-uploading the same file fires onChange again.
    e.target.value = '';
  };

  function goBack(target: Step) {
    setStep(target);
    setError(null);
  }

  // ── breadcrumb stepper ──
  const steps: { num: Step; title: string; subtitle: string }[] = [
    { num: 1, title: 'Find company', subtitle: selectedCompany ? selectedCompany.company_name : '' },
    { num: 2, title: 'Download template', subtitle: templateDownloaded ? `${selectedCompany?.exchange_ticker || ''} pre-filled` : '' },
    { num: 3, title: 'Fill locally', subtitle: 'Excel + Capital IQ plugin' },
    { num: 4, title: 'Upload result', subtitle: '' },
  ];

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-800 mb-1">Investment Valuation Agent</h1>
        <p className="text-gray-500 text-sm">
          Let's set up a new valuation. Follow the four steps below.
        </p>
      </div>

      {/* Progress stepper */}
      <div className="flex items-center gap-0">
        {steps.map((s, i) => {
          const active = s.num === step;
          const done = s.num < step;
          const bg = done ? 'bg-green-600' : active ? 'bg-blue-600' : 'bg-gray-300';
          const textColor = done || active ? 'text-gray-900 font-semibold' : 'text-gray-400';
          return (
            <div key={s.num} className="flex items-center flex-1">
              <div className="flex flex-col items-center flex-1 cursor-pointer" onClick={() => done && goBack(s.num)}>
                <div className={`w-8 h-8 rounded-full ${bg} text-white flex items-center justify-center text-sm font-bold shrink-0`}>
                  {done ? '✓' : s.num}
                </div>
                <div className={`mt-1.5 text-xs ${textColor} text-center`}>{s.title}</div>
                {s.subtitle && (
                  <div className="text-[10px] text-gray-400 text-center max-w-[120px] truncate">{s.subtitle}</div>
                )}
              </div>
              {i < steps.length - 1 && (
                <div className={`h-0.5 ${done ? 'bg-green-600' : 'bg-gray-200'} flex-1 mt-[-22px]`} />
              )}
            </div>
          );
        })}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      {/* Step content */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        {step === 1 && (
          <StepOne
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            searching={searching}
            searchResults={searchResults}
            selectedCompany={selectedCompany}
            onSearch={runSearch}
            onPick={pickCompany}
            onProceed={proceedToStep2}
          />
        )}
        {step === 2 && selectedCompany && (
          <StepTwo
            company={selectedCompany}
            downloadingTemplate={downloadingTemplate}
            templateDownloaded={templateDownloaded}
            onDownload={triggerDownload}
            // Admin path: go to step 3 (fill locally) then step 4 (upload).
            // Public path: step 3 (fill locally) is meaningless, skip to step 4.
            onProceed={adminConfigured ? proceedToStep3 : proceedToStep4}
            onBack={() => goBack(1)}
            dbStatus={dbStatus}
            loadingFromDb={loadingFromDb}
            onValueFromDb={triggerValueFromDb}
            adminConfigured={adminConfigured}
          />
        )}
        {step === 3 && selectedCompany && (
          <StepThree
            company={selectedCompany}
            onProceed={proceedToStep4}
            onBack={() => goBack(2)}
          />
        )}
        {step === 4 && (
          <StepFour
            company={selectedCompany}
            uploading={uploading}
            fileInputRef={fileInputRef}
            onUploadChange={handleUploadChange}
            onDropFile={handleFile}
            onBack={() => goBack(selectedCompany ? 3 : 1)}
          />
        )}
      </div>

      {/* Footer shortcuts */}
      <div className="flex items-center justify-center gap-4 text-xs text-gray-400">
        <button
          onClick={onDemo}
          className="text-gray-500 hover:text-gray-700 underline"
        >
          Or try the demo data
        </button>
        {step !== 4 && (
          <>
            <span>·</span>
            <button
              onClick={() => goBack(4)}
              className="text-gray-500 hover:text-gray-700 underline"
            >
              I already have a filled template — skip to upload
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Step 1 — Find company
// ──────────────────────────────────────────────────────────────────────
function StepOne({
  searchQuery, setSearchQuery, searching, searchResults, selectedCompany,
  onSearch, onPick, onProceed,
}: {
  searchQuery: string; setSearchQuery: (s: string) => void;
  searching: boolean; searchResults: SearchResult[] | null;
  selectedCompany: SearchResult | null;
  onSearch: () => void;
  onPick: (c: SearchResult) => void;
  onProceed: () => void;
}) {
  return (
    <div className="p-6 space-y-4">
      <div>
        <h2 className="text-lg font-bold text-gray-800 mb-1">Step 1 — Find the company</h2>
        <p className="text-xs text-gray-500">
          Search by ticker, company name, or <code className="bg-gray-100 px-1 rounded text-[11px]">Exchange:Ticker</code> format.
          Examples: <code className="bg-gray-100 px-1 rounded text-[11px]">NVDA</code>, <code className="bg-gray-100 px-1 rounded text-[11px]">Alibaba</code>, <code className="bg-gray-100 px-1 rounded text-[11px]">SEHK:992</code>.
        </p>
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
          placeholder="Ticker or company name…"
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          autoFocus
        />
        <button
          onClick={onSearch}
          disabled={!searchQuery.trim() || searching}
          className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:bg-gray-300"
        >
          {searching ? 'Searching…' : 'Search'}
        </button>
      </div>

      {searchResults && (
        <div>
          {searchResults.length === 0 ? (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-900">
              No matches. Try a different ticker or spelling, or use the exchange-prefix format like <code className="bg-white px-1 rounded">NasdaqGS:MSFT</code>.
            </div>
          ) : (
            <div>
              <div className="text-xs text-gray-500 mb-2">
                {searchResults.length} {searchResults.length === 1 ? 'match' : 'matches'} — select the correct one:
              </div>
              <div className="border border-gray-200 rounded-lg overflow-hidden max-h-72 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-[11px] text-gray-500 sticky top-0">
                    <tr>
                      <th className="px-3 py-1.5 text-left">Exchange:Ticker</th>
                      <th className="px-3 py-1.5 text-left">Company</th>
                      <th className="px-3 py-1.5 text-left">Country</th>
                      <th className="px-3 py-1.5 text-left">Industry</th>
                    </tr>
                  </thead>
                  <tbody>
                    {searchResults.map((r) => {
                      const isSelected = selectedCompany?.exchange_ticker === r.exchange_ticker;
                      return (
                        <tr
                          key={r.exchange_ticker}
                          onClick={() => onPick(r)}
                          className={`cursor-pointer border-b border-gray-100 last:border-0 ${
                            isSelected ? 'bg-blue-100 font-semibold' : 'hover:bg-blue-50'
                          }`}
                        >
                          <td className="px-3 py-2 font-mono text-xs">{r.exchange_ticker}</td>
                          <td className="px-3 py-2">{r.company_name}</td>
                          <td className="px-3 py-2 text-xs">{r.country}</td>
                          <td className="px-3 py-2 text-xs">{r.industry}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {selectedCompany && (
        <div className="flex justify-end pt-2 border-t border-gray-100">
          <button
            onClick={onProceed}
            className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700"
          >
            Continue to template download →
          </button>
        </div>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Step 2 — Download template
// ──────────────────────────────────────────────────────────────────────
function StepTwo({
  company, downloadingTemplate, templateDownloaded,
  onDownload, onProceed, onBack,
  dbStatus, loadingFromDb, onValueFromDb,
  adminConfigured,
}: {
  company: SearchResult;
  downloadingTemplate: boolean;
  templateDownloaded: boolean;
  onDownload: () => void;
  onProceed: () => void;
  onBack: () => void;
  dbStatus: { inDb: boolean; dataAsOf: string | null } | null;
  loadingFromDb: boolean;
  onValueFromDb: () => void;
  adminConfigured: boolean;
}) {
  return (
    <div className="p-6 space-y-4">
      <div>
        <h2 className="text-lg font-bold text-gray-800 mb-1">Step 2 — Get the data</h2>
      </div>

      {/* Company summary card */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="text-xs text-blue-700 uppercase font-semibold mb-1">Selected company</div>
        <div className="font-bold text-blue-900 text-lg">{company.company_name}</div>
        <div className="text-sm text-blue-700 mt-1">
          <span className="font-mono">{company.exchange_ticker}</span>
          <span className="mx-2 text-blue-400">·</span>
          {company.country}
          <span className="mx-2 text-blue-400">·</span>
          {company.industry}
        </div>
      </div>

      {/* Database-backed fast path — shown when ticker is in the ingested DB. */}
      {dbStatus?.inDb && (
        <div className="bg-emerald-50 border border-emerald-300 rounded-lg p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-xs text-emerald-800 uppercase font-semibold mb-1">
                ⚡ Instant — from database
              </div>
              <div className="text-sm text-emerald-900">
                This company is in the ingested markets dataset. You can skip the data
                upload entirely.
              </div>
              {dbStatus.dataAsOf && (
                <div className="text-[11px] text-emerald-700 mt-1">
                  Data as of {dbStatus.dataAsOf}
                </div>
              )}
            </div>
            <button
              onClick={onValueFromDb}
              disabled={loadingFromDb}
              className="shrink-0 px-5 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 disabled:bg-gray-300"
            >
              {loadingFromDb ? 'Running valuation…' : '→ Value from Database'}
            </button>
          </div>
        </div>
      )}

      {/* Public path — not in DB, no admin. Single-sentence contact
          instruction. No template download, no data-provider mention. */}
      {!adminConfigured && dbStatus && !dbStatus.inDb && (
        <div className="bg-slate-50 border border-slate-300 rounded-lg p-4">
          <p className="text-sm text-slate-700 leading-relaxed">
            Email the repository maintainer with the ticker above; they'll send back a data
            file you can upload in the next step.
          </p>
        </div>
      )}

      {/* Admin / author path — template download flow. Only visible on
          deployments where AD_CC_ADMIN_TOKEN is set. */}
      {adminConfigured && (
        <div className="flex flex-col items-center gap-3 py-4">
          {!templateDownloaded ? (
            <>
              <button
                onClick={onDownload}
                disabled={downloadingTemplate}
                className="px-6 py-3 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700 disabled:bg-gray-300 flex items-center gap-2"
              >
                {downloadingTemplate ? <>Generating template…</> : <>📥 Download pre-filled template</>}
              </button>
              <p className="text-[11px] text-gray-500">
                Admin-only affordance on this deployment.
              </p>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 text-green-700 text-sm font-semibold">
                <span>✓</span>
                <span>Template downloaded — check your Downloads folder.</span>
              </div>
              <button onClick={onDownload} className="text-xs text-gray-500 underline hover:text-gray-700">
                Download again
              </button>
            </>
          )}
        </div>
      )}

      <div className="flex justify-between pt-2 border-t border-gray-100">
        <button onClick={onBack} className="text-sm text-gray-500 hover:text-gray-700">
          ← Change company
        </button>
        <button
          onClick={onProceed}
          // Admin path: wait for download. Public path: always enabled.
          disabled={adminConfigured && !templateDownloaded}
          className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:bg-gray-300"
        >
          {adminConfigured ? 'Next: fill it locally →' : 'Next: upload data file →'}
        </button>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Step 3 — Instructions for filling locally
// ──────────────────────────────────────────────────────────────────────
function StepThree({
  company, onProceed, onBack,
}: {
  company: SearchResult;
  onProceed: () => void;
  onBack: () => void;
}) {
  return (
    <div className="p-6 space-y-4">
      <div>
        <h2 className="text-lg font-bold text-gray-800 mb-1">Step 3 — Fill the template locally</h2>
        <p className="text-xs text-gray-500">
          Open the downloaded file on a machine that has <b>Microsoft Excel</b> with the
          <b> Capital IQ plug-in</b> installed and authenticated. This step runs locally on your
          computer — the server doesn't need to be involved.
        </p>
      </div>

      <ol className="space-y-3 text-sm">
        <li className="flex gap-3">
          <span className="shrink-0 bg-gray-200 text-gray-700 rounded-full w-7 h-7 flex items-center justify-center text-xs font-bold">1</span>
          <div>
            <div className="font-semibold text-gray-800">Open the downloaded file in Excel</div>
            <div className="text-xs text-gray-500 mt-0.5">
              Double-click <code className="bg-gray-100 px-1 rounded">CIQ_Fetch_Template.xlsx</code>. Make sure the Capital IQ
              add-in is loaded (check Excel's Add-ins tab — you should see "S&P Capital IQ").
            </div>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="shrink-0 bg-gray-200 text-gray-700 rounded-full w-7 h-7 flex items-center justify-center text-xs font-bold">2</span>
          <div>
            <div className="font-semibold text-gray-800">Wait for the formulas to resolve</div>
            <div className="text-xs text-gray-500 mt-0.5">
              You'll see <code className="bg-gray-100 px-1 rounded">#GETTING_DATA</code> in most cells initially.
              It takes 10–30 seconds for Capital IQ to fetch everything.
              If you're not already logged in, the plug-in will prompt you.
            </div>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="shrink-0 bg-gray-200 text-gray-700 rounded-full w-7 h-7 flex items-center justify-center text-xs font-bold">3</span>
          <div>
            <div className="font-semibold text-gray-800">Verify B1 shows <span className="font-mono">{company.exchange_ticker}</span></div>
            <div className="text-xs text-gray-500 mt-0.5">
              The ticker should already be pre-filled. If you want to value a different company,
              change B1 and the whole sheet re-resolves.
            </div>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="shrink-0 bg-gray-200 text-gray-700 rounded-full w-7 h-7 flex items-center justify-center text-xs font-bold">4</span>
          <div>
            <div className="font-semibold text-gray-800">Save the file (Ctrl+S)</div>
            <div className="text-xs text-gray-500 mt-0.5">
              Keep the <code className="bg-gray-100 px-1 rounded">.xlsx</code> format. This bakes the resolved values
              into the file so the server can read them without needing Capital IQ itself.
            </div>
          </div>
        </li>
      </ol>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-900">
        <div className="font-semibold mb-1">💡 No Capital IQ access?</div>
        <div>
          The template is just an Excel workbook with a documented schema. You can populate the
          values manually from any data source — annual reports, Bloomberg, FactSet, or the
          company's 10-K. See <code className="bg-white px-1 rounded">docs/DATA_FETCH_SCHEMA.md</code> for
          field-by-field instructions.
        </div>
      </div>

      <div className="flex justify-between pt-2 border-t border-gray-100">
        <button
          onClick={onBack}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ← Download again
        </button>
        <button
          onClick={onProceed}
          className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700"
        >
          I've filled the template →
        </button>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Step 4 — Upload
// ──────────────────────────────────────────────────────────────────────
function StepFour({
  company, uploading, fileInputRef, onUploadChange, onDropFile, onBack,
}: {
  /** Null when the user jumped directly to upload via the "skip" shortcut. */
  company: SearchResult | null;
  uploading: boolean;
  fileInputRef: React.RefObject<HTMLInputElement>;
  onUploadChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDropFile: (file: File) => void;
  onBack: () => void;
}) {
  const [dragging, setDragging] = useState(false);

  const handleDragOver = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();            // mandatory — else browser opens the file
    e.stopPropagation();
    if (!dragging) setDragging(true);
  };
  const handleDragLeave = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
  };
  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) onDropFile(file);
  };

  const zoneState = uploading
    ? 'border-blue-400 bg-blue-50'
    : dragging
      ? 'border-blue-600 bg-blue-100'
      : 'border-gray-300 hover:border-blue-500 hover:bg-blue-50/50';

  return (
    <div className="p-6 space-y-4">
      <div>
        <h2 className="text-lg font-bold text-gray-800 mb-1">Step 4 — Upload the completed file</h2>
        <p className="text-xs text-gray-500">
          Drop the <code className="bg-gray-100 px-1 rounded text-[11px]">CIQ_Fetch_Template.xlsx</code> you saved in
          Step 3 into the zone below. The server parses it, runs the full M1–M6 valuation
          pipeline, and takes you to the results in a few seconds.
        </p>
      </div>

      {company ? (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-900">
          <span className="font-semibold">Uploading for:</span>{' '}
          {company.company_name} <span className="font-mono text-blue-700">({company.exchange_ticker})</span>
        </div>
      ) : (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-900">
          <span className="font-semibold">Skip-to-upload mode.</span>{' '}
          No company pre-selected — the backend will read the ticker from cell <code className="font-mono">B1</code> of
          your <code className="font-mono">CIQ_Fetch_Template.xlsx</code>.
        </div>
      )}

      <label
        htmlFor="upload-filled-xlsx"
        onDragOver={handleDragOver}
        onDragEnter={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`block border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${zoneState}`}
      >
        <input
          ref={fileInputRef}
          id="upload-filled-xlsx"
          type="file"
          accept=".xlsx,.xls"
          onChange={onUploadChange}
          disabled={uploading}
          className="hidden"
        />
        {uploading ? (
          <>
            <div className="text-4xl mb-2">⏳</div>
            <div className="text-sm font-semibold text-blue-900">Parsing + valuing…</div>
            <div className="text-xs text-blue-600 mt-1">This usually takes 2–5 seconds.</div>
          </>
        ) : dragging ? (
          <>
            <div className="text-4xl mb-2">📥</div>
            <div className="text-sm font-semibold text-blue-900">Release to upload</div>
          </>
        ) : (
          <>
            <div className="text-4xl mb-2">📤</div>
            <div className="text-sm font-semibold text-gray-800">
              Click to choose the filled template
            </div>
            <div className="text-xs text-gray-500 mt-1">
              or drag & drop an <code className="bg-white px-1 rounded">.xlsx</code> file here
            </div>
          </>
        )}
      </label>

      <div className="flex justify-between pt-2 border-t border-gray-100">
        <button
          onClick={onBack}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ← Back to instructions
        </button>
      </div>
    </div>
  );
}
