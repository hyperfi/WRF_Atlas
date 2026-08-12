import { createRouter, createWebHistory } from 'vue-router'
import OverviewView from '@/views/OverviewView.vue'
import NamelistLabView from '@/views/NamelistLabView.vue'
import ExecutionMapView from '@/views/ExecutionMapView.vue'
import PhysicsView from '@/views/PhysicsView.vue'
import VariablesView from '@/views/VariablesView.vue'
import SourceView from '@/views/SourceView.vue'
import GuidedToursView from '@/views/GuidedToursView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'overview', component: OverviewView },
    { path: '/tours', name: 'tours', component: GuidedToursView },
    { path: '/namelist', name: 'namelist', component: NamelistLabView },
    { path: '/execution', name: 'execution', component: ExecutionMapView },
    { path: '/physics', name: 'physics', component: PhysicsView },
    { path: '/physics/:category', name: 'physics-category', component: PhysicsView, props: true },
    { path: '/variables', name: 'variables', component: VariablesView },
    { path: '/source', name: 'source', component: SourceView }
  ]
})

export default router
