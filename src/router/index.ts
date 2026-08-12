import { createRouter, createWebHashHistory } from 'vue-router'
import OverviewView from '@/views/OverviewView.vue'

const NamelistLabView = () => import('@/views/NamelistLabView.vue')
const ExecutionMapView = () => import('@/views/ExecutionMapView.vue')
const PhysicsView = () => import('@/views/PhysicsView.vue')
const VariablesView = () => import('@/views/VariablesView.vue')
const SourceView = () => import('@/views/SourceView.vue')
const GuidedToursView = () => import('@/views/GuidedToursView.vue')
const VersionCompareView = () => import('@/views/VersionCompareView.vue')

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'overview', component: OverviewView },
    { path: '/tours', name: 'tours', component: GuidedToursView },
    { path: '/namelist', name: 'namelist', component: NamelistLabView },
    { path: '/execution', name: 'execution', component: ExecutionMapView },
    { path: '/physics', name: 'physics', component: PhysicsView },
    { path: '/physics/:category', name: 'physics-category', component: PhysicsView, props: true },
    { path: '/variables', name: 'variables', component: VariablesView },
    { path: '/compare', name: 'compare', component: VersionCompareView },
    { path: '/source', name: 'source', component: SourceView }
  ]
})

export default router
