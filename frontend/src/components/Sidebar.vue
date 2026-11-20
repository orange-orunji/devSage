<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useSessions } from '../composables/useSessions'

const props = defineProps({
    open: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'open-settings'])

const { logout, shownName, avatarUrl, bio } = useAuth()
const {
    searchText, sessionGroups, currentSessionId, titleOf,
    loadSessions, createSession, switchSession, deleteSession, renameSession,
    togglePin, isPinned,
} = useSessions()

const initial = computed(() => (shownName.value.charAt(0) || '?').toUpperCase())

async function onNew() {
    createSession()
    await loadSessions()
    emit('close')
}

async function onSwitch(sessionId) {
    await switchSession(sessionId)
    emit('close')   // 移动端：选择后收起抽屉（桌面端无感）
}

// ── 内联重命名（双击会话名或点重命名图标） ──
const editingId = ref('')
const editingName = ref('')

function startEdit(sessionId) {
    editingId.value = sessionId
    editingName.value = titleOf(sessionId)
}

async function commitEdit(sessionId) {
    if (editingId.value !== sessionId) return
    const name = editingName.value.trim()
    editingId.value = ''
    if (!name || name === titleOf(sessionId)) return
    try {
        await renameSession(sessionId, name)
    } catch (err) {
        alert(err.message)
    }
}

watch(editingId, (v) => {
    if (!v) return
    nextTick(() => {
        const el = document.querySelector('.session-rename-input')
        el?.focus()
        el?.select()
    })
})

async function onDelete(sessionId) {
    if (!confirm(`确定要删除会话 "${sessionId}" 吗？`)) return
    try {
        await deleteSession(sessionId)
    } catch (err) {
        alert(err.message)
    }
}
</script>

<template>
    <aside class="sidebar" :class="{ open: props.open }">
        <div class="sidebar-header">
            <div class="brand-mini">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                </svg>
                <span>智维台 · OpsDesk</span>
            </div>
            <button class="btn-logout" @click="logout" title="退出登录">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                    <polyline points="16 17 21 12 16 7"/>
                    <line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
                <span>退出</span>
            </button>
        </div>

        <div class="sidebar-user" @click="emit('open-settings')" title="个人设置">
            <div class="avatar">
                <img v-if="avatarUrl" :src="avatarUrl" class="avatar-img" alt="头像" />
                <span v-else>{{ initial }}</span>
            </div>
            <div class="sidebar-user-info">
                <span class="sidebar-username">{{ shownName }}</span>
                <span class="sidebar-user-role">{{ bio || '普通用户' }}</span>
            </div>
            <button class="btn-gear" title="个人设置">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="3"/>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                </svg>
            </button>
        </div>

        <div class="sidebar-section">
            <button class="btn-new-session" @click="onNew">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19"/>
                    <line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                新建会话
            </button>
        </div>

        <div class="sidebar-section-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            我的会话
        </div>

        <div class="session-search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input v-model="searchText" type="text" placeholder="搜索会话…" />
        </div>

        <div class="session-list">
            <div v-if="sessionGroups.length === 0" class="session-list-hint">
                {{ searchText.trim() ? '无匹配会话' : '暂无会话，点击上方新建' }}
            </div>
            <template v-for="g in sessionGroups" :key="g.label || 'search'">
                <div v-if="g.label" class="session-group-label">{{ g.label }}</div>
                <div v-for="s in g.items" :key="s"
                     class="session-item" :class="{ active: s === currentSessionId }"
                     @click="onSwitch(s)">
                    <input v-if="editingId === s" class="session-rename-input" v-model="editingName"
                           @keydown.enter="commitEdit(s)" @keydown.esc="editingId = ''"
                           @blur="commitEdit(s)" @click.stop />
                    <span v-else class="session-name" :title="s" @dblclick.stop="startEdit(s)">{{ titleOf(s) }}</span>
                    <button class="btn-icon pin" :class="{ active: isPinned(s) }"
                            @click.stop="togglePin(s)" :title="isPinned(s) ? '取消置顶' : '置顶'">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 17v5"/>
                            <path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z"/>
                        </svg>
                    </button>
                    <button class="btn-icon" @click.stop="startEdit(s)" title="重命名">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                    </button>
                    <button class="btn-icon danger" @click.stop="onDelete(s)" title="删除">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                            <line x1="10" y1="11" x2="10" y2="17"/>
                            <line x1="14" y1="11" x2="14" y2="17"/>
                        </svg>
                    </button>
                </div>
            </template>
        </div>

        <div class="upload-area">
            <div class="sidebar-section-label">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                上传文档
            </div>
            <label class="btn-upload" title="界面迁移中：上传功能后续接入">选择文件上传</label>
            <div class="upload-status"></div>
        </div>
    </aside>
</template>
