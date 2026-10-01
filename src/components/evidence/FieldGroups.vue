<script setup lang="ts">
import { computed } from 'vue'
import { registryFieldGroups } from '@/lib/exploration'
import type { GraphNode } from '@/types/graph'
const props = defineProps<{ fields: GraphNode[] }>()
const emit = defineEmits<{ (event: 'select', field: GraphNode): void }>()
const groups = computed(() => registryFieldGroups(props.fields))
</script>

<template>
  <section class="learning-fields" v-if="fields.length">
    <h3>What this branch works with</h3>
    <p>Field meanings and units come from the Registry. Argument matches show a possible handoff; they do not establish who reads or changes a field.</p>
    <div class="field-groups">
      <section v-for="group in groups" :key="group.title">
        <h4>{{ group.title }}</h4>
        <button v-for="field in group.fields.slice(0, 3)" :key="field.id" @click="emit('select', field)">
          <strong>{{ field.label.toUpperCase() }}</strong>
          <span>{{ field.data.description || 'No Registry description' }}</span>
          <small>{{ field.data.units || 'Units not specified' }} · Registry</small>
        </button>
        <details v-if="group.fields.length > 3">
          <summary>{{ group.fields.length - 3 }} more fields</summary>
          <button v-for="field in group.fields.slice(3)" :key="field.id" @click="emit('select', field)">
            <strong>{{ field.label.toUpperCase() }}</strong><span>{{ field.data.description || 'No Registry description' }}</span>
            <small>{{ field.data.units || 'Units not specified' }} · Registry</small>
          </button>
        </details>
      </section>
    </div>
  </section>
</template>

<style scoped>
.learning-fields { margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--border-subtle); }
h3 { font-size: 1rem; }h4 { margin: 16px 0 8px; font-size: .85rem; }
p { max-width: 72ch; margin-top: 8px; color: var(--text-secondary); font-size: .85rem; }
.field-groups { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 210px), 1fr)); gap: 16px; }
button { display: flex; width: 100%; flex-direction: column; gap: 5px; min-height: 44px; padding: 10px 0; background: transparent; border: 0; border-bottom: 1px solid var(--border-subtle); color: var(--text-primary); text-align: left; cursor: pointer; }
button:hover strong { color: var(--accent-emerald); }strong { font: 600 .85rem var(--font-mono); }span { color: var(--text-secondary); font-size: .8rem; text-transform: lowercase; }small { color: var(--text-muted); font-size: .75rem; }
summary { margin-top: 10px; min-height: 36px; cursor: pointer; color: var(--text-secondary); font-size: .8rem; }
</style>
