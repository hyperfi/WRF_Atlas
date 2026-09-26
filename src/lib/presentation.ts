export type EvidenceConfidence = 'exact' | 'inferred' | 'documentation' | 'unresolved'
export interface TraceStep {
  id: string
  label: string
  value: string
  confidence: EvidenceConfidence
  grade?: string
}

// A bounded excerpt keeps large WRF files out of the evidence drawer's DOM.
export function sourceExcerpt(text: string, startLine = 1, endLine = startLine) {
  const lines = text.split(/\r?\n/)
  const start = Math.min(lines.length, Math.max(1, Math.floor(startLine) || 1))
  const end = Math.min(lines.length, Math.max(start, Math.floor(endLine) || start))
  const first = Math.max(1, start - 6)
  const last = Math.min(lines.length, Math.min(end, start + 100) + 6)
  return {
    outOfRange: startLine > lines.length,
    truncated: end > start + 100,
    lines: lines.slice(first - 1, last).map((text, index) => ({
      number: first + index, text, highlighted: startLine <= lines.length && first + index >= start && first + index <= end,
    })),
  }
}

export function uniqueTargets<T extends { target: string }>(edges: T[]) {
  const seen = new Set<string>()
  return edges.filter(edge => {
    if (seen.has(edge.target)) return false
    seen.add(edge.target)
    return true
  })
}
