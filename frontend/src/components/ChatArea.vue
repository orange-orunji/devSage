<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useSessions } from '../composables/useSessions'
import { useMessages } from '../composables/useMessages'
import { useAuth } from '../composables/useAuth'
import { useTheme } from '../composables/useTheme'
import { useToast } from '../composables/useToast'
import { formatContent } from '../utils/format'
import ApprovalCard from './ApprovalCard.vue'

const emit = defineEmits(['toggle-sidebar'])

const { currentSessionId, loadSessions, createSession, titleOf } = useSessions()
const { messages, isStreaming, awaitingApproval, loadHistory, sendMessage, sendResume, checkPendingInterrupt } = useMessages()
const { shownName, apiFetch, fetchProfile } = useAuth()
const { theme, toggleTheme } = useTheme()
const { show: toast } = useToast()

const headerTitle = computed(() => titleOf(currentSessionId.value) || '新会话')
const inputLocked = computed(() => isStreaming.value || awaitingApproval.value)
const initial = computed(() => (shownName.value.charAt(0) || '?').toUpperCase())

const inputText = ref('')
const inputEl = ref(null)
const messagesEl = ref(null)
const kbStats = ref(null)          // 知识库概览（空状态卡片数据）

// ── 引用回复 ──
const quote = ref('')
const quotePreview = computed(() => (quote.value.length > 80 ? quote.value.slice(0, 80) + '…' : quote.value))

// ── 自动滚动 / 回到最新 ──
const autoScroll = ref(true)
const showScrollBtn = ref(false)

function scrollToBottom(smooth = false) {
    nextTick(() => {
        const el = messagesEl.value
        if (!el) return
        el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
    })
}

function onMessagesScroll() {
    const el = messagesEl.value
    if (!el) return
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120
    autoScroll.value = nearBottom
    showScrollBtn.value = !nearBottom
}

// 消息增长：仅当用户在底部附近时自动滚底（上翻阅读时不再被拉回）
watch(messages, () => { if (autoScroll.value) scrollToBottom() }, { deep: true })

function backToLatest() {
    autoScroll.value = true
    showScrollBtn.value = false
    scrollToBottom(true)
}

// ── 消息操作（复制 / 引用 / 反馈 / 重新生成） ──
async function copyMessage(m) {
    try {
        await navigator.clipboard.writeText(m.content)
        toast('已复制回答')
    } catch {
        toast('复制失败', 'error')
    }
}

function quoteMessage(m) {
    quote.value = m.content.slice(0, 300)
    inputEl.value?.focus()
}

function feedbackKey(i) {
    return `fb_${currentSessionId.value}_${i}`
}

function feedback(m, type, i) {
    m.feedback = m.feedback === type ? '' : type
    localStorage.setItem(feedbackKey(i), m.feedback)
    if (m.feedback) toast(m.feedback === 'up' ? '感谢反馈' : '收到，会继续改进')
}

function restoreFeedback() {
    messages.value.forEach((m, i) => {
        const fb = localStorage.getItem(feedbackKey(i))
        if (fb) m.feedback = fb
    })
}

function isLastAssistant(i) {
    const m = messages.value[i]
    return i === messages.value.length - 1 && m?.role === 'assistant' && !!m.content && !m.streaming
}

async function onRegenerate() {
    if (inputLocked.value) return
    let li = -1
    for (let i = messages.value.length - 1; i >= 0; i--) {
        if (messages.value[i].role === 'user') { li = i; break }
    }
    if (li < 0) return
    const q = messages.value[li].content
    messages.value.splice(li)          // 移除旧问答对（仅 UI；后端历史会追加新记录）
    await sendMessage(q, currentSessionId.value)
    await loadSessions()
}

// ── 导出会话（Markdown 下载） ──
function exportSession() {
    if (!messages.value.length) {
        toast('当前会话没有内容可导出', 'error')
        return
    }
    const title = titleOf(currentSessionId.value)
    const lines = [`# ${title}`, '', `> 导出时间：${new Date().toLocaleString()}`, '']
    for (const m of messages.value) {
        lines.push(m.role === 'user' ? '**我**：' : '**助手**：', '', m.content, '')
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${title}.md`
    a.click()
    URL.revokeObjectURL(url)
    toast('已导出为 Markdown')
}

// ── 快捷提示词 ──
const quickPrompts = [
    { label: '知识库有哪些文档', text: '知识库里有哪些文档？' },
    { label: '生成一份报告', text: '帮我生成一份关于' },
    { label: '发一封邮件', text: '帮我发一封邮件给' },
    { label: '知识库检索', text: '在知识库中查找' },
]

function fillPrompt(c) {
    inputText.value = c.text
    nextTick(() => { inputEl.value?.focus(); autoGrow() })
}

// ── 斜杠命令 ──
const commands = [
    { name: 'report', desc: '生成报告', tpl: '帮我生成一份关于「主题」的报告' },
    { name: 'email', desc: '发送邮件（人工审批）', tpl: '帮我发一封邮件给「邮箱」，内容是「内容」' },
    { name: 'search', desc: '知识库检索', tpl: '在知识库中查找「关键词」' },
    { name: 'stats', desc: '知识库统计', tpl: '知识库里有哪些文档？' },
    { name: 'convert', desc: '报告格式转换', tpl: '把报告「文件名」转成 Word' },
]

const showCommands = computed(() => {
    const t = inputText.value
    return t.startsWith('/') && !t.includes(' ') && t.length <= 10
})
const filteredCommands = computed(() => {
    const q = inputText.value.slice(1).toLowerCase()
    if (!q) return commands
    return commands.filter((c) => c.name.includes(q) || c.desc.includes(q))
})
const cmdIndex = ref(0)
watch(filteredCommands, () => { cmdIndex.value = 0 })

function applyCommand(c) {
    inputText.value = c.tpl
    nextTick(() => { inputEl.value?.focus(); autoGrow() })
}

// ── 语音输入（浏览器原生 SpeechRecognition） ──
const SR = window.SpeechRecognition || window.webkitSpeechRecognition
const voiceSupported = !!SR
const listening = ref(false)
let recognition = null

function toggleVoice() {
    if (!voiceSupported) return
    if (listening.value) {
        recognition?.stop()
        return
    }
    recognition = new SR()
    recognition.lang = 'zh-CN'
    recognition.interimResults = true
    recognition.continuous = false
    recognition.onresult = (e) => {
        let text = ''
        for (const r of e.results) text += r[0].transcript
        inputText.value = text
        autoGrow()
    }
    recognition.onend = () => { listening.value = false }
    recognition.onerror = () => { listening.value = false; toast('语音识别失败，请重试', 'error') }
    recognition.start()
    listening.value = true
}

// ── 拖拽上传（复用后端异步上传链路 + 任务轮询） ──
const dragging = ref(false)

function onDragOver(e) {
    e.preventDefault()
    dragging.value = true
}

function onDragLeave(e) {
    if (!e.currentTarget.contains(e.relatedTarget)) dragging.value = false
}

async function onDrop(e) {
    e.preventDefault()
    dragging.value = false
    const files = [...(e.dataTransfer?.files || [])]
    if (!files.length) return
    for (const f of files) uploadFile(f)
}

async function uploadFile(file) {
    if (file.size > 20 * 1024 * 1024) {
        toast(`${file.name} 超过 20MB 限制`, 'error')
        return
    }
    toast(`正在上传 ${file.name}…`)
    try {
        const form = new FormData()
        form.append('file', file)
        const resp = await apiFetch('/api/document/upload', { method: 'POST', body: form })
        const data = await resp.json().catch(() => ({}))
        if (!resp.ok) throw new Error(data.detail || data.message || '上传失败')
        const taskId = data.data?.task_id
        if (!taskId) throw new Error('未获取到任务 ID')
        pollUpload(taskId, file.name)
    } catch (err) {
        toast(`${file.name} 上传失败：${err.message}`, 'error', 5000)
    }
}

async function pollUpload(taskId, filename) {
    for (let i = 0; i < 150; i++) {   // 最长轮询 5 分钟
        await new Promise((r) => setTimeout(r, 2000))
        try {
            const resp = await apiFetch(`/api/document/upload/status/${taskId}`)
            const data = await resp.json()
            const st = data.data
            if (!st) continue
            if (st.status === 'completed') {
                toast(`✅ ${filename} 已入库`)
                loadKbStats()
                return
            }
            if (st.status === 'failed') {
                toast(`${filename} 处理失败：${st.error || st.message || '未知错误'}`, 'error', 6000)
                return
            }
        } catch { /* 网络抖动忽略，继续轮询 */ }
    }
    toast(`${filename} 处理超时，请稍后在知识库中确认`, 'error', 5000)
}

// ── 知识库概览（空状态卡片） ──
async function loadKbStats() {
    try {
        const resp = await apiFetch('/api/document/stats')
        if (!resp.ok) return
        const data = await resp.json()
        kbStats.value = data.data || null
    } catch (err) {
        console.warn('知识库统计加载失败:', err)
    }
}

// ── 未读提示（回答完成时若页面不可见 → 标题加 ●） ──
const BASE_TITLE = document.title

function markUnread() {
    if (document.hidden) document.title = '● ' + BASE_TITLE
}

function onVisibility() {
    if (!document.hidden) document.title = BASE_TITLE
}

// ── 发送 / 审批 / 输入 ──
async function onSend() {
    const q = inputText.value.trim()
    if (!q || inputLocked.value || !currentSessionId.value) return
    const finalQ = quote.value ? `【引用以下内容】\n${quote.value}\n【引用结束】\n\n${q}` : q
    inputText.value = ''
    quote.value = ''
    if (inputEl.value) inputEl.value.style.height = 'auto'
    autoScroll.value = true
    await sendMessage(finalQ, currentSessionId.value)
    await loadSessions()
    markUnread()
}

function onKeydown(e) {
    // 斜杠命令菜单键盘导航优先
    if (showCommands.value && filteredCommands.value.length) {
        if (e.key === 'ArrowDown') {
            e.preventDefault()
            cmdIndex.value = (cmdIndex.value + 1) % filteredCommands.value.length
            return
        }
        if (e.key === 'ArrowUp') {
            e.preventDefault()
            cmdIndex.value = (cmdIndex.value - 1 + filteredCommands.value.length) % filteredCommands.value.length
            return
        }
        if (e.key === 'Enter' || e.key === 'Tab') {
            e.preventDefault()
            applyCommand(filteredCommands.value[cmdIndex.value])
            return
        }
        if (e.key === 'Escape') {
            e.preventDefault()
            inputText.value = ''
            return
        }
    }
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        onSend()
    }
}

function autoGrow() {
    const el = inputEl.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 130) + 'px'
}

async function onDecide(msg, decision) {
    await sendResume(msg, decision, currentSessionId.value)
    await loadSessions()
    markUnread()
}

/** 等待首字时的打字指示器 */
function isTyping(m) {
    return m.streaming && !m.content
}

/** 代码块"复制"按钮（v-html 内容 → 事件委托） */
async function onMessagesClick(e) {
    const btn = e.target.closest('.code-copy-btn')
    if (!btn || !messagesEl.value?.contains(btn)) return
    const code = btn.closest('.code-block')?.querySelector('code')
    if (!code) return
    try {
        await navigator.clipboard.writeText(code.innerText)
        btn.textContent = '已复制 ✓'
    } catch {
        btn.textContent = '复制失败'
    }
    setTimeout(() => { btn.textContent = '复制' }, 1500)
}

onMounted(async () => {
    // 首次进入：无当前会话则新建；加载列表与历史；恢复待审批卡片
    if (!currentSessionId.value) createSession()
    await loadSessions()
    await loadHistory(currentSessionId.value)
    restoreFeedback()
    await checkPendingInterrupt(currentSessionId.value)
    loadKbStats()
    fetchProfile()   // 拉取最新资料（昵称/头像/签名）
    scrollToBottom()
    document.addEventListener('visibilitychange', onVisibility)
})

onBeforeUnmount(() => {
    document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<template>
    <main class="chat-area"
          @dragover="onDragOver" @dragleave="onDragLeave" @drop="onDrop">
        <!-- 拖拽上传遮罩 -->
        <div v-if="dragging" class="drop-mask">
            <div class="drop-mask-inner">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <p>松开鼠标上传文档</p>
                <span>支持 txt / docx / pdf / md（不超过 20MB）</span>
            </div>
        </div>

        <header class="chat-header">
            <div class="chat-header-title">
                <button class="btn-menu" @click="emit('toggle-sidebar')" title="会话列表">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="3" y1="6" x2="21" y2="6"/>
                        <line x1="3" y1="12" x2="21" y2="12"/>
                        <line x1="3" y1="18" x2="21" y2="18"/>
                    </svg>
                </button>
                <span class="session-title">{{ headerTitle }}</span>
            </div>
            <div class="chat-header-actions">
                <span class="chat-header-badge">RAG 增强检索</span>
                <button class="btn-theme" @click="exportSession" title="导出当前会话为 Markdown">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                </button>
                <button class="btn-theme" @click="toggleTheme"
                        :title="theme === 'dark' ? '切换到亮色主题' : '切换到暗色主题'">
                    <svg v-if="theme === 'dark'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="4"/>
                        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
                    </svg>
                    <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                    </svg>
                </button>
            </div>
        </header>

        <div class="chat-messages" ref="messagesEl" @click="onMessagesClick" @scroll.passive="onMessagesScroll">
            <div v-if="messages.length === 0" class="empty-state">
                <div class="overview-hero">
                    <div class="hero-logo">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                        </svg>
                    </div>
                    <h2>你好，{{ shownName || '朋友' }}！我是智维台，你的知识库与交付助手</h2>
                    <p>知识检索 · 报告生成 · 邮件审批 · 格式转换 · 拖拽文件即可入库</p>
                </div>
                <div v-if="kbStats" class="overview-cards">
                    <div class="overview-card">
                        <div class="overview-num">{{ kbStats.doc_count }}</div>
                        <div class="overview-label">知识库文档</div>
                    </div>
                    <div class="overview-card">
                        <div class="overview-num">{{ kbStats.chunk_count }}</div>
                        <div class="overview-label">知识切片</div>
                    </div>
                    <div v-if="kbStats.recent_files && kbStats.recent_files.length" class="overview-card">
                        <div class="overview-recent-name" :title="kbStats.recent_files[0]">{{ kbStats.recent_files[0] }}</div>
                        <div class="overview-label">最近入库</div>
                    </div>
                </div>
            </div>

            <div v-for="(m, i) in messages" :key="i"
                 class="message" :class="m.role === 'user' ? 'user' : 'assistant'">
                <div class="msg-avatar">
                    <template v-if="m.role === 'user'">{{ initial }}</template>
                    <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/>
                        <circle cx="9" cy="14" r="1"/>
                        <circle cx="15" cy="14" r="1"/>
                    </svg>
                </div>
                <div class="msg-body">
                    <div class="msg-role">{{ m.role === 'user' ? '你' : '助手' }}</div>
                    <div v-for="(t, j) in (m.tips || [])" :key="'tip' + j" class="tool-call-tip">{{ t }}</div>
                    <div v-if="isTyping(m)" class="msg-bubble">
                        <div class="typing-indicator"><span></span><span></span><span></span></div>
                    </div>
                    <div v-else-if="m.content" class="msg-bubble"
                         :class="{ 'cursor-blink': m.streaming }"
                         v-html="formatContent(m.content)"></div>

                    <!-- 消息操作条（助手消息，hover 显示） -->
                    <div v-if="m.role === 'assistant' && m.content && !m.streaming" class="bubble-actions">
                        <span v-if="m.duration" class="msg-duration">用时 {{ m.duration.toFixed(1) }}s</span>
                        <button title="复制回答" @click="copyMessage(m)">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                                <rect x="9" y="9" width="13" height="13" rx="2"/>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                            </svg>
                        </button>
                        <button title="引用此回答" @click="quoteMessage(m)">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/>
                                <path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z"/>
                            </svg>
                        </button>
                        <button :class="{ active: m.feedback === 'up' }" title="有帮助" @click="feedback(m, 'up', i)">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
                            </svg>
                        </button>
                        <button :class="{ active: m.feedback === 'down' }" title="没帮助" @click="feedback(m, 'down', i)">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zM17 2h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"/>
                            </svg>
                        </button>
                        <button v-if="isLastAssistant(i) && !inputLocked" title="重新生成" @click="onRegenerate">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="23 4 23 10 17 10"/>
                                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                            </svg>
                        </button>
                    </div>

                    <ApprovalCard v-if="m.approval" :approval="m.approval" @decide="onDecide(m, $event)" />
                </div>
            </div>

            <!-- 回到最新 -->
            <button v-if="showScrollBtn" class="btn-scroll-bottom" @click="backToLatest" title="回到最新">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="6 9 12 15 18 9"/>
                </svg>
            </button>
        </div>

        <div class="chat-input-area">
            <!-- 引用条 -->
            <div v-if="quote" class="quote-bar">
                <span class="quote-label">引用</span>
                <span class="quote-text">{{ quotePreview }}</span>
                <button class="quote-close" @click="quote = ''" title="取消引用">×</button>
            </div>

            <!-- 快捷提示词（输入框为空且会话进行中时显示） -->
            <div v-if="!inputText && !quote && messages.length" class="quick-chips">
                <button v-for="c in quickPrompts" :key="c.label" @click="fillPrompt(c)">{{ c.label }}</button>
            </div>

            <div class="chat-input-row">
                <button v-if="voiceSupported" class="btn-mic" :class="{ active: listening }"
                        @click="toggleVoice" :title="listening ? '停止录音' : '语音输入'">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                        <line x1="12" y1="19" x2="12" y2="23"/>
                        <line x1="8" y1="23" x2="16" y2="23"/>
                    </svg>
                </button>
                <textarea ref="inputEl" v-model="inputText" rows="1" :disabled="inputLocked"
                          placeholder="输入问题，Enter 发送，Shift+Enter 换行；输入 / 打开命令菜单"
                          @keydown="onKeydown" @input="autoGrow"></textarea>
                <button class="btn-send" :disabled="inputLocked || !inputText.trim()" @click="onSend" title="发送">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"/>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                    </svg>
                </button>
            </div>

            <!-- 斜杠命令菜单 -->
            <div v-if="showCommands && filteredCommands.length" class="cmd-menu">
                <div v-for="(c, ci) in filteredCommands" :key="c.name"
                     class="cmd-item" :class="{ active: ci === cmdIndex }"
                     @mouseenter="cmdIndex = ci" @mousedown.prevent="applyCommand(c)">
                    <span class="cmd-name">/{{ c.name }}</span>
                    <span class="cmd-desc">{{ c.desc }}</span>
                </div>
            </div>
        </div>
    </main>
</template>
