export interface NamelistAssignment {
  group: string
  name: string
  firstIndex: number
  values: string[]
  valueStart: number
  valueEnd: number
}

export interface NamelistGroup {
  name: string
  end: number
}

export interface ParsedNamelist {
  assignments: NamelistAssignment[]
  groups: NamelistGroup[]
  maxDomain: number
  warnings: string[]
}

// Keep offsets stable while excluding comments and quoted values from syntax scans.
function maskSyntax(text: string): string {
  const chars = [...text]
  let quote: string | null = null
  let comment = false
  for (let i = 0; i < chars.length; i += 1) {
    const char = chars[i]
    if (char === '\n') {
      comment = false
      continue
    }
    if (comment) {
      chars[i] = ' '
      continue
    }
    if (quote) {
      chars[i] = ' '
      if (char === quote) {
        if (chars[i + 1] === quote) {
          chars[++i] = ' '
        } else {
          quote = null
        }
      }
      continue
    }
    if (char === '!') {
      chars[i] = ' '
      comment = true
    } else if (char === "'" || char === '"') {
      chars[i] = ' '
      quote = char
    }
  }
  return chars.join('')
}

function withoutComments(text: string): string {
  const chars = [...text]
  let quote: string | null = null
  let comment = false
  for (let i = 0; i < chars.length; i += 1) {
    const char = chars[i]
    if (char === '\n') {
      comment = false
      continue
    }
    if (comment) {
      chars[i] = ' '
    } else if (quote) {
      if (char === quote) {
        if (chars[i + 1] === quote) i += 1
        else quote = null
      }
    } else if (char === "'" || char === '"') {
      quote = char
    } else if (char === '!') {
      chars[i] = ' '
      comment = true
    }
  }
  return chars.join('')
}

interface ValueSpan { start: number; end: number; values: string[] }

function valueSpans(text: string): ValueSpan[] {
  const clean = withoutComments(text.replace(/&\s*(?:\r?\n)?\s*&?/g, match => ' '.repeat(match.length)))
  const masked = maskSyntax(clean)
  const spans: ValueSpan[] = []
  let start = 0
  for (let i = 0; i <= clean.length; i += 1) {
    if (i !== clean.length && masked[i] !== ',') continue
    const section = clean.slice(start, i)
    const leading = section.search(/\S/)
    const token = section.trim()
    if (token) {
      const repeat = token.match(/^(\d+)\s*\*\s*(.+)$/s)
      const values = repeat && Number(repeat[1]) <= 100
        ? Array(Number(repeat[1])).fill(repeat[2].trim()) as string[]
        : [token]
      spans.push({ start: start + leading, end: i - (section.length - section.trimEnd().length), values })
    }
    start = i + 1
  }
  return spans
}

const splitValues = (text: string): string[] => valueSpans(text).flatMap(span => span.values)

export function parseNamelist(text: string): ParsedNamelist {
  const syntax = maskSyntax(text)
  const assignments: NamelistAssignment[] = []
  const groups: NamelistGroup[] = []
  const warnings: string[] = []
  const header = /&([a-z][\w]*)\b/gi
  let found: RegExpExecArray | null
  while ((found = header.exec(syntax))) {
    if (found[1].toLowerCase() === 'end') continue
    const group = found[1].toLowerCase()
    const bodyStart = header.lastIndex
    const slash = syntax.indexOf('/', bodyStart)
    const ampEnd = syntax.slice(bodyStart).search(/&end\b/i)
    const alternateEnd = ampEnd < 0 ? -1 : bodyStart + ampEnd
    const end = slash < 0 ? alternateEnd : alternateEnd < 0 ? slash : Math.min(slash, alternateEnd)
    if (end < 0) {
      warnings.push(`&${group} has no closing / or &end; its entries were not imported.`)
      continue
    }
    groups.push({ name: group, end })
    const bodySyntax = syntax.slice(bodyStart, end)
    const matches = [...bodySyntax.matchAll(/\b([a-z][\w]*)(?:\s*\(\s*(\d+)\s*\))?\s*=/gi)]
    for (let i = 0; i < matches.length; i += 1) {
      const match = matches[i]
      const valueStart = bodyStart + (match.index || 0) + match[0].length
      const valueEnd = i + 1 < matches.length ? bodyStart + (matches[i + 1].index || 0) : end
      assignments.push({
        group,
        name: match[1].toLowerCase(),
        firstIndex: Number(match[2] || 1),
        values: splitValues(text.slice(valueStart, valueEnd)),
        valueStart,
        valueEnd,
      })
    }
    header.lastIndex = end + (syntax[end] === '/' ? 1 : 4)
  }
  const maxDomRaw = getNamelistValue({ assignments, groups, maxDomain: 1, warnings }, 'domains', 'max_dom', 1)
  const maxDom = Number(maxDomRaw)
  const maxDomain = Number.isInteger(maxDom) && maxDom > 0 && maxDom <= 100
    ? maxDom
    : Math.max(1, ...assignments.filter(item => item.group === 'physics').map(item => item.firstIndex + item.values.length - 1))
  return { assignments, groups, maxDomain, warnings }
}

export function getNamelistValue(parsed: ParsedNamelist, group: string, name: string, domain = 1): string | undefined {
  const matches = parsed.assignments.filter(item => item.group === group.toLowerCase() && item.name === name.toLowerCase())
  for (const item of matches.reverse()) {
    const offset = domain - item.firstIndex
    if (offset >= 0 && offset < item.values.length) return item.values[offset]
  }
  return undefined
}

export function unquoteNamelist(value: string | undefined): string | undefined {
  if (!value) return undefined
  const trimmed = value.trim()
  if ((trimmed.startsWith("'") && trimmed.endsWith("'")) || (trimmed.startsWith('"') && trimmed.endsWith('"'))) {
    return trimmed.slice(1, -1)
  }
  return trimmed
}

export function updateNamelistValue(text: string, group: string, name: string, domain: number, value: string): string {
  const parsed = parseNamelist(text)
  const normalizedGroup = group.toLowerCase()
  const normalizedName = name.toLowerCase()
  const assignment = [...parsed.assignments].reverse().find(item =>
    item.group === normalizedGroup && item.name === normalizedName &&
    domain >= item.firstIndex && domain < item.firstIndex + item.values.length)
  if (assignment) {
    const segment = text.slice(assignment.valueStart, assignment.valueEnd)
    let remaining = domain - assignment.firstIndex
    for (const span of valueSpans(segment)) {
      if (remaining >= span.values.length) {
        remaining -= span.values.length
        continue
      }
      const replacement = [...span.values]
      replacement[remaining] = value
      const start = assignment.valueStart + span.start
      const end = assignment.valueStart + span.end
      return text.slice(0, start) + replacement.join(', ') + text.slice(end)
    }
  }
  const targetGroup = parsed.groups.find(item => item.name === normalizedGroup)
  const indexedName = domain === 1 ? normalizedName : `${normalizedName}(${domain})`
  if (targetGroup) {
    return text.slice(0, targetGroup.end) + `  ${indexedName} = ${value},\n` + text.slice(targetGroup.end)
  }
  return `${text.trimEnd()}\n&${normalizedGroup}\n  ${indexedName} = ${value},\n/\n`
}
