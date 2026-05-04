/**
 * Reverse-calculation helpers for the three-story joint examination.
 *
 * Grounded in `docs/Ginzu understanding/three_story_joint_examination.md §3`.
 * These functions are pure — no side effects, no session state. Display only.
 */

/** DuPont-derived: Required_ROIC = margin × Sales/Capital. */
export function requiredROIC(
  margin: number | null | undefined,
  sc: number | null | undefined,
): number | null {
  if (margin == null || sc == null) return null;
  return margin * sc;
}

/**
 * Reverse-derived: Required_S_C = target_ROIC / margin.
 * Answers: "given my margin story, what S/C do I need to produce this ROIC?"
 *
 * `roicAnchor` is typically historical 5-yr avg ROIC. If undefined/null
 * or margin is zero/missing, returns null.
 */
export function requiredSC(
  roicAnchor: number | null | undefined,
  margin: number | null | undefined,
): number | null {
  if (roicAnchor == null || margin == null || margin === 0) return null;
  return roicAnchor / margin;
}

/**
 * Factual gap statement between an actual computed value and a reference.
 * Unit is 'pp' for percentages (displayed with × 100) or '×' for ratios.
 * Returns a signed string like '+6pp' or '-0.5×', or '—' if either side missing.
 */
export function gapStatement(
  actual: number | null | undefined,
  reference: number | null | undefined,
  unit: 'pp' | '×',
): string {
  if (actual == null || reference == null) return '—';
  const delta = actual - reference;
  const sign = delta >= 0 ? '+' : '';
  if (unit === 'pp') {
    return `${sign}${(delta * 100).toFixed(1)}pp`;
  }
  return `${sign}${delta.toFixed(2)}×`;
}
