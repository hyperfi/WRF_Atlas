import { defineStore } from 'pinia'
import { ref, nextTick } from 'vue'
import type { SourceEvidence } from '@/types/graph'
import type { EvidenceConfidence } from '@/lib/presentation'

export const useEvidenceStore = defineStore('evidence', () => {
  const selection = ref<{
    evidence: SourceEvidence
    title: string
    confidence: EvidenceConfidence
    explanation: string
    returnTo?: string
  } | null>(null)
  let returnFocus: HTMLElement | null = null
  const open = (evidence: SourceEvidence, title = 'Source evidence', confidence: EvidenceConfidence = 'exact', explanation = '', returnTo?: string) => {
    if (!selection.value) returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    selection.value = { evidence, title, confidence, explanation, returnTo }
  }
  const close = () => {
    const target = returnFocus
    selection.value = null
    returnFocus = null
    nextTick(() => target?.focus())
  }
  return { selection, open, close }
})
