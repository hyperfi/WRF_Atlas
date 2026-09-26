<script setup lang="ts">
import type { TraceStep } from '@/lib/presentation'
defineProps<{ steps: TraceStep[]; selected: string; caption: string }>()
defineEmits<{ inspect: [id: string] }>()
</script>

<template>
  <div class="compact-trace">
    <div class="trace-flow" :class="{ 'four-stops': steps.length === 4 }" :style="{ '--stop-count': steps.length }" aria-label="Trace evidence groups">
      <button v-for="(step, index) in steps" :key="step.id" type="button"
        :class="['trace-stop', step.confidence, { selected: selected === step.id }]"
        :aria-pressed="selected === step.id" @click="$emit('inspect', step.id)">
        <span class="stop-label"><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ step.label }}</span>
        <strong>{{ step.value }}</strong>
        <span class="stop-grade">{{ step.grade || (step.confidence === 'exact' ? 'Direct source' : step.confidence === 'inferred' ? 'Source join' : step.confidence === 'unresolved' ? 'Unresolved' : 'Documentation') }}</span>
      </button>
    </div>
    <p class="trace-caption">{{ caption }}</p>
  </div>
</template>

<style scoped>
.compact-trace { container-type: inline-size; }
.trace-flow { display: grid; grid-template-columns: repeat(var(--stop-count), minmax(0, 1fr)); gap: 12px; }
.trace-stop { position: relative; min-width: 0; padding: 13px 15px; text-align: left; border: 1px solid var(--border-strong); border-radius: 5px; background: var(--bg-inset); color: var(--text-primary); cursor: pointer; }
.trace-stop:not(:last-child)::after { content: '›'; position: absolute; z-index: 1; right: -10px; top: 40%; color: var(--text-muted); }
.trace-stop.selected { border-color: var(--accent-emerald); background: var(--accent-soft); }
.trace-stop:hover { border-color: var(--border-focus); }
.stop-label { display: flex; gap: 9px; color: var(--text-secondary); font-size: .73rem; }
.stop-label > span { color: var(--accent-emerald); font: .68rem var(--font-mono); }
.trace-stop strong { display: block; margin: 8px 0; font: 600 .8rem var(--font-mono); overflow-wrap: anywhere; }
.stop-grade { color: var(--accent-emerald); font-size: .65rem; }
.inferred .stop-grade, .unresolved .stop-grade { color: var(--accent-amber); }
.trace-caption { margin: 10px 0 0; color: var(--text-secondary); font-size: .72rem; line-height: 1.5; }
@media (max-width: 620px) { .trace-flow { grid-template-columns: 1fr; gap: 7px; }.trace-stop:not(:last-child)::after { display: none; }.trace-stop { padding: 10px 12px; } }
@media (max-width: 1100px) { .trace-stop:not(:last-child)::after { display: none; } }
@container (max-width: 650px) { .four-stops { grid-template-columns: repeat(2, minmax(0, 1fr)); }.trace-stop:not(:last-child)::after { display: none; } }
@container (max-width: 400px) { .trace-flow { grid-template-columns: 1fr; } }
</style>
