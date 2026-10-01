import type { GraphNode } from '../types/graph'

export function rankedSearch(nodes: GraphNode[], query: string, limit = 30): GraphNode[] {
  const term = query.trim().toLowerCase()
  if (!term) return []
  const score = (node: GraphNode) => {
    const label = node.label.toLowerCase()
    if (label === term || node.id.toLowerCase() === term) return 0
    if (label.startsWith(term)) return 1
    if (label.includes(term)) return 2
    return 3
  }
  return nodes.filter(node => node.label.toLowerCase().includes(term) || node.id.toLowerCase().includes(term))
    .sort((a, b) => score(a) - score(b) || a.label.localeCompare(b.label) || a.id.localeCompare(b.id))
    .slice(0, limit)
}

export function entityDestination(node: GraphNode) {
  if (node.type === 'state_variable') return { path: '/variables', query: { field: node.label } }
  if (node.type === 'namelist_option' && node.data.category) return { path: '/namelist', query: { focus: node.label } }
  if (node.type === 'registry_package' && node.data.category) {
    return { path: `/physics/${node.data.category}`, query: { scheme: String(node.data.value) } }
  }
  const file = node.data.file || node.data.path || node.data.source_file
  return { path: '/source', query: { file, line: file ? String(node.data.line || node.data.source_line || 1) : undefined } }
}

export function registryFieldGroups(fields: GraphNode[]) {
  const groups = [
    { title: 'Fluxes and rates', fields: [] as GraphNode[] },
    { title: 'Temperature and moisture', fields: [] as GraphNode[] },
    { title: 'Other model state', fields: [] as GraphNode[] },
  ]
  for (const field of fields) {
    const description = String(field.data.description || '').toLowerCase()
    const index = /flux|rate|tendency|radiation/.test(description) ? 0
      : /temperature|moisture|water|humidity/.test(description) ? 1 : 2
    groups[index]!.fields.push(field)
  }
  return groups.filter(group => group.fields.length)
}
