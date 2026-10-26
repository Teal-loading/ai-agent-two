import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: {
      title: '首页 - Teal AI超级智能体应用平台',
      description: 'Teal AI超级智能体应用平台提供AI运动健康助手和AI超级智能体服务，满足您的各种AI对话需求'
    }
  },
  {
    path: '/fit-app',
    name: 'FitApp',
    component: () => import('../views/FitApp.vue'),
    meta: {
      title: 'AI运动健康助手 - Teal AI超级智能体应用平台',
      description: 'AI运动健康助手是Teal AI超级智能体应用平台的运动与健康管理顾问，帮你解答训练、饮食与康复问题，提供科学建议'
    }
  },
  {
    path: '/super-agent',
    name: 'SuperAgent',
    component: () => import('../views/SuperAgent.vue'),
    meta: {
      title: 'AI超级智能体 - Teal AI超级智能体应用平台',
      description: 'AI超级智能体是Teal AI超级智能体应用平台的全能助手，能解答各类专业问题，提供精准建议和解决方案'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局导航守卫，设置文档标题
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = to.meta.title
  }
  next()
})

export default router
