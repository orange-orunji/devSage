import { computed, ref } from 'vue'

// 模块级单例状态：所有组件共享同一份登录态（无需 Pinia）
const token = ref(localStorage.getItem('access_token') || '')
const username = ref(localStorage.getItem('user') || '')
const authed = ref(!!token.value)

// 用户资料（GET /api/auth/me 拉取；localStorage 缓存供首屏秒显）
const displayName = ref(localStorage.getItem('display_name') || '')
const avatarUrl = ref(localStorage.getItem('avatar') || '')
const bio = ref(localStorage.getItem('bio') || '')
const role = ref(localStorage.getItem('role') || 'user')

/** 显示名：昵称优先，回退登录名 */
const shownName = computed(() => displayName.value || username.value)
/** 是否管理员（文档删除等操作仅管理员可用） */
const isAdmin = computed(() => role.value === 'admin')

function setProfileCache(dn, av, b, r) {
    displayName.value = dn
    avatarUrl.value = av
    bio.value = b
    role.value = r || 'user'
    localStorage.setItem('display_name', dn)
    localStorage.setItem('avatar', av)
    localStorage.setItem('bio', b)
    localStorage.setItem('role', role.value)
}

function setAuth(t, u) {
    token.value = t
    username.value = u
    authed.value = true
    localStorage.setItem('access_token', t)
    localStorage.setItem('user', u)
    // 清空上一个账号的资料缓存（由 fetchProfile 重新拉取）
    setProfileCache('', '', '')
}

function logout() {
    token.value = ''
    username.value = ''
    authed.value = false
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setProfileCache('', '', '')
}

/** 登录/注册；模式由 mode 指定（'login' | 'register'） */
async function loginOrRegister(mode, user, pass) {
    const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register'
    const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, password: pass }),
    })
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok) throw new Error(data.detail || '操作失败，请重试')
    if (mode === 'login') {
        setAuth(data.access_token, user)
        return { registered: false }
    }
    return { registered: true }
}

/** 带 token 的请求头（供后续模块使用） */
function authHeaders() {
    return token.value ? { Authorization: 'Bearer ' + token.value } : {}
}

/** 统一鉴权请求封装：自动附带 token；遇 401 清除登录态（自动回登录页）并抛出 */
async function apiFetch(url, options = {}) {
    const resp = await fetch(url, {
        ...options,
        headers: { ...authHeaders(), ...(options.headers || {}) },
    })
    if (resp.status === 401) {
        logout()
        throw new Error('登录已过期，请重新登录')
    }
    return resp
}

// ── 用户资料 ──

/** 拉取当前用户资料（登录后/进入聊天页时调用） */
async function fetchProfile() {
    try {
        const resp = await apiFetch('/api/auth/me')
        if (!resp.ok) return
        const data = await resp.json()
        setProfileCache(data.display_name || '', data.avatar || '', data.bio || '', data.role || 'user')
    } catch (err) {
        console.warn('资料加载失败:', err)
    }
}

/** 更新昵称与个性签名 */
async function updateProfile({ display_name, bio: newBio }) {
    const resp = await apiFetch('/api/auth/me', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ display_name, bio: newBio }),
    })
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok) throw new Error(data.detail || '保存失败')
    setProfileCache(data.display_name || '', data.avatar || '', data.bio || '', data.role || 'user')
}

/** 上传头像（File 对象；不手动设置 Content-Type，由浏览器带 multipart boundary） */
async function uploadAvatar(file) {
    const form = new FormData()
    form.append('file', file)
    const resp = await apiFetch('/api/auth/me/avatar', {
        method: 'POST',
        body: form,
    })
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok) throw new Error(data.detail || '上传失败')
    avatarUrl.value = data.avatar
    localStorage.setItem('avatar', data.avatar)
}

/** 修改密码（需原密码验证） */
async function changePassword(oldPassword, newPassword) {
    const resp = await apiFetch('/api/auth/me/password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    })
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok) throw new Error(data.detail || '修改失败')
}

export function useAuth() {
    return {
        role, isAdmin,
        token, username, authed, shownName, displayName, avatarUrl, bio,
        setAuth, logout, loginOrRegister, authHeaders, apiFetch,
        fetchProfile, updateProfile, uploadAvatar, changePassword,
    }
}
