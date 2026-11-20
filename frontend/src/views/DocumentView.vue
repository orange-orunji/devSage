<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const emit = defineEmits(['back'])
const { apiFetch, isAdmin } = useAuth()

const loading = ref(true)
const error = ref('')
const items = ref([])
const metrics = ref(null)
const keyword = ref('')
const busyName = ref('')
const toast = ref('')

const filtered = computed(() => {
    const k = keyword.value.trim().toLowerCase()
    if (!k) return items.value
    return items.value.filter((it) => (it.name || '').toLowerCase().includes(k))
})

const maxActivity = computed(() => {
    if (!metrics.value?.activity?.length) return 1
    return Math.max(1, ...metrics.value.activity.map((a) => a.sessions))
})

async function load() {
    loading.value = true
    error.value = ''
    try {
        const [m, d] = await Promise.all([
            apiFetch('/api/kb/metrics'),
            apiFetch('/api/kb/documents'),
        ])
        const mj = await m.json()
        const dj = await d.json()
        if (!m.ok || mj.code !== 200) throw new Error(mj.message || '指标加载失败')
        if (!d.ok || dj.code !== 200) throw new Error(dj.message || '文档列表加载失败')
        metrics.value = mj.data
        items.value = dj.data.items || []
    } catch (err) {
        error.value = err.message || '加载失败'
    } finally {
        loading.value = false
    }
}

async function removeDoc(name) {
    if (!confirm(`确定删除「${name}」吗？该文档的所有切片会一并删除，且不可恢复。`)) return
    busyName.value = name
    try {
        const resp = await apiFetch('/api/kb/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name }),
        })
        const j = await resp.json()
        if (!resp.ok || j.code !== 200) throw new Error(j.message || '删除失败')
        toast.value = j.message || '已删除'
        setTimeout(() => { toast.value = '' }, 2500)
        await load()
    } catch (err) {
        toast.value = '删除失败：' + (err.message || '未知错误')
    } finally {
        busyName.value = ''
    }
}

function fmtTime(t) {
    if (!t) return '—'
    return String(t).replace('T', ' ').slice(0, 19)
}

onMounted(load)
</script>

<template>
    <main class="kb-view">
        <header class="kb-header">
            <button class="btn-back" @click="emit('back')" title="返回对话">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
                     stroke-linecap="round" stroke-linejoin="round">
                    <path d="M19 12H5"/><polyline points="12 19 5 12 12 5"/>
                </svg>
            </button>
            <h1>文档管理</h1>
            <button class="btn-refresh" @click="load" :disabled="loading">刷新</button>
        </header>

        <div class="kb-body">
            <p v-if="error" class="kb-error">{{ error }}</p>

            <section class="metric-grid" v-if="metrics">
                <div class="metric-card">
                    <span class="metric-value">{{ metrics.doc_count }}</span>
                    <span class="metric-label">知识库文档</span>
                </div>
                <div class="metric-card">
                    <span class="metric-value">{{ metrics.chunk_count }}</span>
                    <span class="metric-label">知识切片</span>
                </div>
                <div class="metric-card">
                    <span class="metric-value">{{ metrics.session_count }}</span>
                    <span class="metric-label">历史会话</span>
                </div>
                <div class="metric-card">
                    <span class="metric-value">{{ metrics.assistant_count }}</span>
                    <span class="metric-label">智能回答</span>
                </div>
                <div class="metric-card">
                    <span class="metric-value">{{ metrics.vector_size_mb }}<small>MB</small></span>
                    <span class="metric-label">向量库占用</span>
                </div>
            </section>

            <section class="panel" v-if="metrics">
                <div class="panel-head">
                    <h2>近 7 天活跃会话</h2>
                    <span class="panel-hint">按会话文件的最后修改时间统计</span>
                </div>
                <div class="activity">
                    <div class="activity-col" v-for="a in metrics.activity" :key="a.date">
                        <div class="activity-bar-wrap">
                            <div class="activity-bar"
                                 :style="{ height: Math.max(4, (a.sessions / maxActivity) * 100) + '%' }"
                                 :title="a.date + '：' + a.sessions + ' 个会话'"></div>
                        </div>
                        <span class="activity-count">{{ a.sessions }}</span>
                        <span class="activity-date">{{ a.date.slice(5) }}</span>
                    </div>
                </div>
            </section>

            <section class="panel">
                <div class="panel-head">
                    <h2>文档清单</h2>
                    <input v-model="keyword" class="kb-search" type="search" placeholder="按文件名筛选…" />
                </div>

                <p v-if="loading" class="kb-empty">正在加载…</p>
                <p v-else-if="!filtered.length" class="kb-empty">暂无文档，可在对话页左下角上传。</p>

                <table v-else class="kb-table">
                    <thead>
                    <tr>
                        <th>#</th>
                        <th>文件名</th>
                        <th class="num">切片数</th>
                        <th>入库时间</th>
                        <th class="op">操作</th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr v-for="(it, i) in filtered" :key="it.name">
                        <td class="num">{{ i + 1 }}</td>
                        <td class="name">{{ it.name }}</td>
                        <td class="num">{{ it.chunks }}</td>
                        <td class="time">{{ fmtTime(it.create_time) }}</td>
                        <td class="op">
                            <button v-if="isAdmin" class="btn-del" :disabled="busyName === it.name"
                                    @click="removeDoc(it.name)">
                                {{ busyName === it.name ? '删除中…' : '删除' }}
                            </button>
                            <span v-else class="op-readonly">只读</span>
                        </td>
                    </tr>
                    </tbody>
                </table>
            </section>

            <p class="kb-tip">
                删除会同时移除该文件的全部切片并重建 BM25 索引，操作不可恢复；
                <strong>仅管理员可删除</strong>，普通用户为只读。
            </p>
        </div>

        <transition name="fade">
            <div v-if="toast" class="kb-toast">{{ toast }}</div>
        </transition>
    </main>
</template>

<style scoped>
.kb-view {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    background: #f7f8fa;
    height: 100%;
    overflow: hidden;
}

.kb-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 24px;
    background: #fff;
    border-bottom: 1px solid #e5e7eb;
}

.kb-header h1 {
    font-size: 17px;
    font-weight: 600;
    margin: 0;
    color: #1f2937;
}

.btn-back, .btn-refresh {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #e5e7eb;
    background: #fff;
    border-radius: 8px;
    height: 32px;
    padding: 0 10px;
    cursor: pointer;
    color: #4b5563;
}

.btn-back svg { width: 16px; height: 16px; }
.btn-refresh { margin-left: auto; font-size: 13px; }
.btn-refresh:disabled { opacity: .5; cursor: default; }

.kb-body {
    flex: 1;
    overflow-y: auto;
    padding: 20px 24px 40px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 12px;
}

.metric-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.metric-value {
    font-size: 24px;
    font-weight: 600;
    color: #2b6cb0;
    line-height: 1.1;
}

.metric-value small { font-size: 12px; margin-left: 2px; color: #6b7280; }
.metric-label { font-size: 12px; color: #6b7280; }

.panel {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px;
}

.panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
}

.panel-head h2 { font-size: 14px; font-weight: 600; margin: 0; color: #1f2937; }
.panel-hint { font-size: 12px; color: #9ca3af; }

.kb-search {
    height: 30px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 0 10px;
    font-size: 13px;
    width: 200px;
    outline: none;
}

.activity { display: flex; gap: 10px; align-items: flex-end; height: 120px; }
.activity-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.activity-bar-wrap { height: 80px; width: 100%; display: flex; align-items: flex-end; }
.activity-bar {
    width: 100%;
    background: linear-gradient(180deg, #63a4e8, #2b6cb0);
    border-radius: 4px 4px 0 0;
    min-height: 4px;
}
.activity-count { font-size: 12px; color: #374151; }
.activity-date { font-size: 11px; color: #9ca3af; }

.kb-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.kb-table th, .kb-table td {
    padding: 9px 8px;
    border-bottom: 1px solid #f0f1f3;
    text-align: left;
    color: #374151;
}
.kb-table th { color: #6b7280; font-weight: 500; background: #fafbfc; }
.kb-table .num { text-align: right; width: 80px; }
.kb-table .op { width: 90px; text-align: right; }
.kb-table .name { word-break: break-all; }
.kb-table .time { color: #6b7280; white-space: nowrap; }

.btn-del {
    border: 1px solid #fecaca;
    color: #c53030;
    background: #fff5f5;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    cursor: pointer;
}
.btn-del:disabled { opacity: .6; cursor: default; }

.kb-empty { color: #9ca3af; font-size: 13px; padding: 16px 0; text-align: center; }
.kb-error { color: #c53030; font-size: 13px; }
.kb-tip { font-size: 12px; color: #9ca3af; }

.kb-toast {
    position: fixed;
    left: 50%;
    bottom: 40px;
    transform: translateX(-50%);
    background: #1f2937;
    color: #fff;
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px;
    z-index: 50;
}

.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
