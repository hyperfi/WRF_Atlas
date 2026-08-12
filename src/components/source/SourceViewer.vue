<template>
  <div class="source-viewer glass-panel">
    <div class="viewer-header">
      <div class="file-info">
        <span class="file-icon">📄</span>
        <span class="file-path">{{ filePath || 'No file selected' }}</span>
        <span class="line-count" v-if="formattedLines.length">{{ formattedLines.length }} lines</span>
      </div>
      
      <div class="viewer-actions">
        <div class="goto-line" v-if="formattedLines.length">
          <input 
            v-model.number="targetLine" 
            type="number" 
            placeholder="Line..." 
            class="line-input" 
            @keydown.enter="scrollToTargetLine"
          />
          <button class="action-btn" @click="scrollToTargetLine">Go</button>
        </div>
      </div>
    </div>
    
    <div class="viewer-content" ref="scrollContainer">
      <div class="code-container" v-if="formattedLines.length">
        <div 
          v-for="(line, idx) in formattedLines" 
          :key="idx" 
          :id="`line-${idx + 1}`"
          class="source-line"
          :class="{ 
            'highlighted': isHighlighted(idx + 1),
            'target-line': (idx + 1) === targetLine 
          }"
        >
          <div class="source-line-num">{{ idx + 1 }}</div>
          <div class="source-line-content" v-html="highlightFortran(line)"></div>
        </div>
      </div>

      <div v-else-if="loading" class="loading-state">
        <div class="spinner"></div>
        <span>Loading source file...</span>
      </div>

      <div v-else class="empty-state">
        Select a file from the sidebar to view source code.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps<{
  filePath?: string
  sourceCode?: string
  loading?: boolean
  highlightLines?: number[]
  initialLine?: number
}>()

const scrollContainer = ref<HTMLElement | null>(null)
const targetLine = ref<number | null>(props.initialLine || null)

const formattedLines = computed(() => {
  if (!props.sourceCode) return []
  return props.sourceCode.split('\n')
})

const isHighlighted = (lineNum: number) => {
  if (!props.highlightLines) return false
  return props.highlightLines.includes(lineNum)
}

const scrollToTargetLine = () => {
  if (!targetLine.value) return
  const lineEl = document.getElementById(`line-${targetLine.value}`)
  if (lineEl) {
    lineEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

watch(() => props.initialLine, (newLine) => {
  if (newLine) {
    targetLine.value = newLine
    nextTick(scrollToTargetLine)
  }
})

watch(() => props.sourceCode, () => {
  if (props.initialLine) {
    nextTick(scrollToTargetLine)
  }
})

// Basic Fortran syntax highlighter
const highlightFortran = (code: string) => {
  if (!code) return '&nbsp;'
  
  // Escape HTML characters
  let escaped = code
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Fortran comments
  const commentIdx = escaped.indexOf('!')
  if (commentIdx !== -1) {
    const mainCode = escaped.substring(0, commentIdx)
    const comment = escaped.substring(commentIdx)
    return highlightCodeOnly(mainCode) + `<span class="fortran-comment">${comment}</span>`
  }

  return highlightCodeOnly(escaped)
}

const highlightCodeOnly = (code: string) => {
  return code
    // Strings
    .replace(/('.*?'|".*?")/g, '<span class="fortran-string">$1</span>')
    // Preprocessor
    .replace(/(^\s*#\w+)/g, '<span class="fortran-preproc">$1</span>')
    // Keywords
    .replace(/\b(SUBROUTINE|MODULE|PROGRAM|FUNCTION|IF|THEN|ELSE|END|DO|WHILE|SELECT|CASE|CALL|USE|ONLY|IMPLICIT|NONE|RETURN|CONTAINS|INCLUDE)\b/gi, '<span class="fortran-keyword">$&</span>')
    // Types
    .replace(/\b(INTEGER|REAL|LOGICAL|CHARACTER|TYPE|INTENT|DIMENSION|ALLOCATABLE|POINTER|PARAMETER)\b/gi, '<span class="fortran-type">$&</span>')
}
</script>

<style scoped>
.source-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(0, 0, 0, 0.2);
}

.file-info {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.file-icon {
  font-size: 1.1rem;
}

.file-path {
  font-weight: 600;
  color: var(--accent-blue);
}

.line-count {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.08);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.viewer-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.goto-line {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.line-input {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  color: var(--text-primary);
  font-size: 0.8rem;
  width: 80px;
  outline: none;
  font-family: var(--font-mono);
}

.action-btn {
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.4);
  color: #60a5fa;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
}

.action-btn:hover {
  background: rgba(59, 130, 246, 0.4);
}

.viewer-content {
  flex: 1;
  overflow: auto;
  background: #070a18;
  font-family: var(--font-mono);
  font-size: 0.82rem;
  line-height: 1.6;
}

.code-container {
  min-width: max-content;
  display: flex;
  flex-direction: column;
}

.source-line {
  display: flex;
  padding: 0 0.5rem;
  transition: background 0.15s;
}

.source-line:hover {
  background: rgba(255, 255, 255, 0.04);
}

.source-line.highlighted {
  background: rgba(245, 158, 11, 0.18);
  border-left: 3px solid var(--accent-amber);
}

.source-line.target-line {
  background: rgba(59, 130, 246, 0.25);
  border-left: 3px solid var(--accent-blue);
}

.source-line-num {
  width: 55px;
  user-select: none;
  color: #475569;
  text-align: right;
  padding-right: 1.25rem;
  flex-shrink: 0;

}

.source-line-content {
  color: #e2e8f0;
  white-space: pre;
}

/* Syntax Highlighting Colors */
:deep(.fortran-keyword) {
  color: #ec4899;
  font-weight: bold;
}

:deep(.fortran-type) {
  color: #3b82f6;
  font-weight: bold;
}

:deep(.fortran-string) {
  color: #10b981;
}

:deep(.fortran-comment) {
  color: #64748b;
  font-style: italic;
}

:deep(.fortran-preproc) {
  color: #f59e0b;
  font-weight: bold;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  color: var(--text-muted);
  gap: 1rem;
}
</style>
