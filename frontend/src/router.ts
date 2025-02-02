import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
// import ChatView from './views/ChatView.vue';
const ChatView = () => import('./views/ChatView.vue');

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Chat',
    component: ChatView,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;