<template>
  <div class="evidence-panel glass">
    <div class="panel-header">
      <h3 class="panel-title">Activation Chain & Source Evidence</h3>
    </div>
    
    <div class="chain-container">
      <div v-for="(step, index) in chain" :key="index" class="chain-step">
        <div class="step-indicator">
          <div class="circle" :class="step.type"></div>
          <div class="line" v-if="index < chain.length - 1"></div>
        </div>
        <div class="step-content">
          <div class="step-title" :class="`text-${step.type}`">{{ step.label }}</div>
          <div class="step-desc">{{ step.description }}</div>
          <div v-if="step.evidence || step.file" class="step-evidence">
            <button class="evidence-btn" @click="$emit('view-source', step.evidence || { path: step.file, startLine: step.line })">
              📄 View in Source <span v-if="getLineText(step)">(L{{ getLineText(step) }})</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SourceEvidence } from '@/types/graph'

interface ChainStep {
  label: string
  description: string
  type: string
  file?: string
  line?: number
  evidence?: SourceEvidence
}

defineProps<{
  chain: ChainStep[]
}>()

const emit = defineEmits<{
  (e: 'view-source', evidence: SourceEvidence): void
}>()

const getLineText = (step: ChainStep) => {
  if (step.evidence && step.evidence.startLine) return step.evidence.startLine
  if (step.line) return step.line
  return null
}
</script>

<style scoped>
.evidence-panel {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel-header {
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 0.75rem;
}

.panel-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.chain-container {
  display: flex;
  flex-direction: column;
}

.chain-step {
  display: flex;
  gap: 1rem;
  position: relative;
}

.step-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 24px;
}

.circle {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--text-muted);
  z-index: 2;
  margin-top: 6px;
}

.circle.namelist { background: var(--accent-amber); }
.circle.package { background: var(--accent-emerald); }
.circle.subroutine { background: var(--accent-blue); }

.line {
  width: 2px;
  flex: 1;
  background: var(--border-subtle);
  margin-top: 4px;
  margin-bottom: 4px;
}

.step-content {
  padding-bottom: 1.25rem;
  flex: 1;
}

.step-title {
  font-weight: 600;
  font-size: 0.95rem;
  margin-bottom: 0.25rem;
}

.step-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.step-evidence {
  margin-top: 0.5rem;
}

.evidence-btn {
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.4);
  color: #60a5fa;
  padding: 0.3rem 0.75rem;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.evidence-btn:hover {
  background: rgba(59, 130, 246, 0.3);
  color: #ffffff;
  transform: translateY(-1px);
}
</style>
