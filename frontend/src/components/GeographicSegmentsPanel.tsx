import { useEffect, useState, useMemo } from 'react';
import type { ValuationResponse, GeographicSegment } from '../types/valuation';
import type { PatchValue } from '../api/client';
import axios from 'axios';

/**
 * Geographic segments panel — Cost of Capital page.
 *
 * Shows CIQ-fetched segments (pre-computed %), the resolver's suggested
 * Damodaran mapping, and a dropdown per row for manual override.
 *
 * Dropdown options = 180 countries + 10 regions (from /api/erp-catalog),
 * each labeled with its total ERP. User picks at a glance; blended ERP
 * preview recomputes live.
 */

interface ErpOption {
  name: string;
  total_erp: number;
  kind: "country" | "region";
  base_erp?: number;
  crp?: number;
}

interface Props {
  data: ValuationResponse;
  onPatch?: (path: string, value: PatchValue) => void | Promise<void>;
}

export default function GeographicSegmentsPanel({ data, onPatch }: Props) {
  const segments = data.inputs.methodology_choices?.geographic_segments ?? [];
  const [catalog, setCatalog] = useState<{ countries: ErpOption[]; regions: ErpOption[] } | null>(null);
  const [saving, setSaving] = useState(false);
  const [draftOverrides, setDraftOverrides] = useState<Record<number, string>>({});

  // Load the ERP catalog once
  useEffect(() => {
    let cancelled = false;
    axios.get('/api/erp-catalog').then(r => {
      if (cancelled) return;
      setCatalog({
        countries: (r.data.countries || []).map((c: ErpOption) => ({ ...c, kind: "country" as const })),
        regions: (r.data.regions || []).map((r: ErpOption) => ({ ...r, kind: "region" as const })),
      });
    }).catch(() => setCatalog({ countries: [], regions: [] }));
    return () => { cancelled = true; };
  }, []);

  // Build the combined dropdown options (regions first — fewer, broader)
  const options = useMemo<ErpOption[]>(() => {
    if (!catalog) return [];
    return [...catalog.regions, ...catalog.countries];
  }, [catalog]);

  if (segments.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded p-3 text-xs text-gray-600">
        <div className="font-semibold text-gray-800 mb-1">No geographic segments fetched from CIQ</div>
        <div>
          Your uploaded template does not contain the <code className="bg-white px-1 py-0.5 rounded text-[10px]">IQ_GEO_SEG_NAME_ABS</code> /
          <code className="bg-white px-1 py-0.5 rounded text-[10px]">IQ_GEO_SEG_REV_ABS</code> rows.
          Download the latest template from <code className="bg-white px-1 py-0.5 rounded text-[10px]">knowledge_base/ciq_fetches/CIQ_Fetch_Template.xlsx</code>,
          populate it in Excel with your ticker, and re-upload.
        </div>
      </div>
    );
  }

  const erpApproach = data.inputs.methodology_choices?.erp_approach;
  const usingBlended = erpApproach === "operating_countries" || erpApproach === "operating_regions";
  const currentErp = data.cost_of_capital?.equity_risk_premium ?? null;

  // Current (stored) blended ERP, derived from whatever resolution each segment has
  const blendedStored = useMemo(() => {
    let total = 0;
    let w = 0;
    for (const s of segments) {
      const erp = s.resolution?.erp;
      const pct = s.pct ?? 0;
      if (erp != null) {
        total += pct * erp;
        w += pct;
      }
    }
    return w > 0 ? total / w : null;
  }, [segments]);

  // Draft blended ERP — preview as user changes dropdowns (before submit)
  const blendedDraft = useMemo(() => {
    if (!catalog) return blendedStored;
    let total = 0;
    let w = 0;
    for (let i = 0; i < segments.length; i++) {
      const s = segments[i];
      const draft = draftOverrides[i];
      let erp: number | null = null;
      if (draft) {
        const opt = options.find(o => `${o.kind}:${o.name}` === draft);
        erp = opt?.total_erp ?? null;
      } else {
        erp = s.resolution?.erp ?? null;
      }
      const pct = s.pct ?? 0;
      if (erp != null) {
        total += pct * erp;
        w += pct;
      }
    }
    return w > 0 ? total / w : null;
  }, [segments, draftOverrides, options, catalog, blendedStored]);

  const submitOverrides = async () => {
    if (!onPatch) return;
    setSaving(true);
    try {
      // Build updated segments array
      const updated = segments.map((s, i) => {
        const draft = draftOverrides[i];
        if (!draft) return s;
        const [kind, ...rest] = draft.split(':');
        const name = rest.join(':');
        const opt = options.find(o => o.name === name && o.kind === kind);
        if (!opt) return s;
        return {
          ...s,
          resolution: {
            raw_name: s.name,
            mapped_to: opt.name,
            mapped_kind: opt.kind,
            erp: opt.total_erp,
            members: [],
            confidence: 1.0,          // manual override = full confidence
            source: "user",
            note: `User-mapped to ${opt.kind} '${opt.name}' (ERP ${(opt.total_erp * 100).toFixed(2)}%)`,
          },
        };
      });
      await onPatch("methodology_choices.geographic_segments", updated as unknown as unknown[]);
      setDraftOverrides({});
    } finally {
      setSaving(false);
    }
  };

  const fmtPct = (v: number | null | undefined) =>
    v == null ? "—" : `${(v * 100).toFixed(2)}%`;

  return (
    <section className="bg-white border border-gray-300 rounded-md shadow-sm">
      <header className="px-4 py-2 bg-gray-100 border-b border-gray-300 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-gray-800">Geographic Revenue Mix</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            CIQ-fetched segments with pre-calculated revenue %. Use the dropdown
            to manually map each row to a Damodaran country or region. Blended
            ERP feeds the "Operating countries" ERP approach in WACC.
          </p>
        </div>
        {!usingBlended && onPatch && (
          <button
            onClick={() => onPatch("methodology_choices.erp_approach", "operating_countries")}
            className="shrink-0 px-3 py-1.5 text-xs font-semibold bg-indigo-600 text-white rounded hover:bg-indigo-700"
            title={`Currently using ERP approach "${erpApproach}" (ERP ${currentErp ? (currentErp*100).toFixed(2)+"%" : "?"}). Click to switch to operating-countries so WACC uses the blended ERP computed below.`}
          >
            Use blended ERP in WACC →
          </button>
        )}
        {usingBlended && (
          <div className="shrink-0 text-xs bg-emerald-50 border border-emerald-200 text-emerald-700 px-2 py-1 rounded font-semibold">
            ✓ Active in WACC
          </div>
        )}
      </header>
      <div className="p-4 space-y-3">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-2 py-1">Segment (from CIQ)</th>
              <th className="text-right px-2 py-1">Revenue</th>
              <th className="text-right px-2 py-1">% of total</th>
              <th className="text-left px-2 py-1">Current mapping</th>
              <th className="text-right px-2 py-1">ERP used</th>
              <th className="text-left px-2 py-1">Manual override</th>
            </tr>
          </thead>
          <tbody>
            {segments.map((s, i) => {
              const r = s.resolution;
              const conf = r?.confidence ?? 0;
              const dot = conf >= 0.9 ? "bg-green-500" : conf >= 0.5 ? "bg-amber-500" : "bg-red-500";
              const draft = draftOverrides[i] ?? "";
              const tooltipComposite = r?.members?.length
                ? r.members.map(m => `  ${m.to} (${m.kind}): ${(m.weight*100).toFixed(0)}% × ${fmtPct(m.erp)}`).join('\n')
                : "";
              return (
                <tr key={i} className="border-b border-gray-100 hover:bg-sky-50/30">
                  <td className="px-2 py-1.5 font-medium">{s.name}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{s.revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{s.pct != null ? (s.pct * 100).toFixed(1) + '%' : "—"}</td>
                  <td className="px-2 py-1.5">
                    <div className="flex items-center gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
                      <span className={r?.mapped_kind === "unresolved" ? "text-red-600 font-semibold" : ""}
                            title={tooltipComposite || r?.note || ""}>
                        {r?.mapped_to || "(unresolved)"}
                        {r?.mapped_kind === "composite" && ` (composite of ${r.members.length})`}
                      </span>
                      {r?.source === "user" && (
                        <span className="ml-1 px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 text-[10px] font-semibold">
                          user
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{fmtPct(r?.erp)}</td>
                  <td className="px-2 py-1.5">
                    <select
                      value={draft}
                      onChange={e => setDraftOverrides(d => ({ ...d, [i]: e.target.value }))}
                      className="w-full max-w-xs border border-gray-300 rounded px-1 py-0.5 text-xs"
                    >
                      <option value="">— keep auto suggestion —</option>
                      {catalog && (
                        <>
                          <optgroup label={`Regions (${catalog.regions.length})`}>
                            {catalog.regions.map(o => (
                              <option key={`r:${o.name}`} value={`region:${o.name}`}>
                                {o.name} ({fmtPct(o.total_erp)})
                              </option>
                            ))}
                          </optgroup>
                          <optgroup label={`Countries (${catalog.countries.length})`}>
                            {catalog.countries.map(o => (
                              <option key={`c:${o.name}`} value={`country:${o.name}`}>
                                {o.name} ({fmtPct(o.total_erp)})
                              </option>
                            ))}
                          </optgroup>
                        </>
                      )}
                    </select>
                  </td>
                </tr>
              );
            })}
            <tr className="border-t-2 border-gray-300 bg-indigo-50 font-bold">
              <td className="px-2 py-1.5">Blended ERP</td>
              <td colSpan={3} className="px-2 py-1.5 text-xs text-gray-600 italic">
                Revenue-weighted across resolved segments
              </td>
              <td className="px-2 py-1.5 text-right tabular-nums text-indigo-900">
                {fmtPct(blendedStored)}
                {blendedDraft !== blendedStored && blendedDraft != null && (
                  <span className="ml-2 text-indigo-600 text-[10px]">
                    (preview: {fmtPct(blendedDraft)})
                  </span>
                )}
              </td>
              <td className="px-2 py-1.5">
                {Object.keys(draftOverrides).length > 0 && (
                  <button
                    disabled={saving || !onPatch}
                    onClick={submitOverrides}
                    className="px-2 py-0.5 bg-indigo-600 text-white rounded text-xs hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {saving ? 'Saving…' : `Apply ${Object.keys(draftOverrides).length} override(s)`}
                  </button>
                )}
              </td>
            </tr>
          </tbody>
        </table>

        <div className="text-[11px] text-gray-500 leading-relaxed">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-500 mr-1" /> high confidence (≥ 0.9)
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-500 ml-3 mr-1" /> composite / weak default (0.5–0.9)
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-500 ml-3 mr-1" /> unresolved (needs your input)
          {' · '}
          To use the blended ERP in WACC: set the ERP approach on the Cost of Capital panel to "Operating countries" or "Operating regions".
        </div>
      </div>
    </section>
  );
}
