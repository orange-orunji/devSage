<script setup>
import { ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const { loginOrRegister } = useAuth()

const authMode = ref('login')
const usernameInput = ref('')
const passwordInput = ref('')
const msg = ref('')
const msgClass = ref('auth-msg')
const submitting = ref(false)

function switchTab(mode) {
    authMode.value = mode
    msg.value = ''
    msgClass.value = 'auth-msg'
}

async function onSubmit() {
    if (!usernameInput.value.trim() || !passwordInput.value) return
    submitting.value = true
    msg.value = ''
    msgClass.value = 'auth-msg'
    try {
        const res = await loginOrRegister(authMode.value, usernameInput.value.trim(), passwordInput.value)
        if (res.registered) {
            msgClass.value = 'auth-msg success'
            msg.value = '注册成功，请登录。'
            authMode.value = 'login'
        }
        // 登录成功 → useAuth 内 authed=true → App 切换到 ChatView
    } catch (err) {
        msgClass.value = 'auth-msg error'
        msg.value = err.message
    } finally {
        submitting.value = false
    }
}
</script>

<template>
    <div class="auth-layout">
        <aside class="auth-brand">
            <div class="brand-mark">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                </svg>
            </div>
            <h1>智维台 · OpsDesk</h1>
            <p class="auth-brand-desc">面向企业 IT 服务台的智能知识协同系统，<br>让知识触手可及。</p>
            <ul class="auth-brand-points">
                <li>文档检索与智能问答</li>
                <li>多轮对话上下文理解</li>
                <li>敏感操作人工审批</li>
            </ul>
        </aside>

        <main class="auth-panel">
            <div class="auth-form-wrap">
                <h2>{{ authMode === 'login' ? '登录' : '注册' }}</h2>
                <p class="auth-form-sub">使用您的账号继续访问知识库</p>
                <div class="auth-tabs" role="tablist">
                    <button type="button" :class="{ active: authMode === 'login' }" @click="switchTab('login')">登录</button>
                    <button type="button" :class="{ active: authMode === 'register' }" @click="switchTab('register')">注册</button>
                </div>
                <form @submit.prevent="onSubmit" novalidate>
                    <div class="form-group">
                        <label for="auth-username">用户名</label>
                        <input type="text" id="auth-username" v-model="usernameInput"
                               placeholder="请输入用户名" required autocomplete="username">
                    </div>
                    <div class="form-group">
                        <label for="auth-password">密码</label>
                        <input type="password" id="auth-password" v-model="passwordInput"
                               placeholder="请输入密码" required autocomplete="current-password">
                    </div>
                    <button type="submit" class="btn btn-primary btn-block" :disabled="submitting">
                        {{ submitting ? '处理中...' : (authMode === 'login' ? '登录' : '注册') }}
                    </button>
                    <div :class="msgClass">{{ msg }}</div>
                </form>
            </div>
        </main>
    </div>
</template>
