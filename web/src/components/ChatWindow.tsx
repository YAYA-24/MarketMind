import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ToolStep {
  id: string
  name: string
  icon: string
  displayName: string
  inputSummary: string
  status: 'running' | 'done'
}

interface Reference {
  url: string
  title: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  images?: string[]
  steps?: ToolStep[]
  references?: Reference[]
}

/* ------------------------------------------------------------------ */
/*  Quick Actions                                                      */
/* ------------------------------------------------------------------ */

const DEFAULT_QUICK_ACTIONS = [
  '查一下茅台现在的股价',
  '分析比亚迪的技术指标',
  '对比茅台、五粮液和平安银行',
  '查一下宁德时代的财务数据',
  '帮我画一下比亚迪的K线图',
  '最近A股有什么重要消息',
]

const STORAGE_KEY = 'astock-quick-actions'

function loadQuickActions(): string[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) return JSON.parse(saved)
  } catch {}
  return DEFAULT_QUICK_ACTIONS
}

function saveQuickActions(actions: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(actions))
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function stripImagePaths(text: string): string {
  return text
    .replace(/[`*]*[/\\][\w/\\._-]*\.png[`*]*/g, '')
    .replace(/\*{0,2}K线图文件已保存\*{0,2}[：:]\s*/g, '')
    .replace(/文件路径[：:]\s*/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function ImageLightbox({ src, onClose }: { src: string; onClose: () => void }) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={onClose}>
      <div className="relative max-w-[90vw] max-h-[90vh]" onClick={e => e.stopPropagation()}>
        <img src={src} alt="K线图" className="max-w-full max-h-[85vh] rounded-lg shadow-2xl" />
        <div className="absolute top-3 right-3 flex gap-2">
          <a href={src} download className="px-3 py-1.5 rounded-lg bg-slate-800/80 text-xs text-slate-200 hover:bg-slate-700 backdrop-blur-sm border border-slate-600/50 transition-colors">
            保存图片
          </a>
          <button onClick={onClose} className="px-3 py-1.5 rounded-lg bg-slate-800/80 text-xs text-slate-200 hover:bg-slate-700 backdrop-blur-sm border border-slate-600/50 transition-colors">
            关闭
          </button>
        </div>
      </div>
    </div>
  )
}

function QuickActionEditor({ actions, onSave, onClose }: { actions: string[]; onSave: (a: string[]) => void; onClose: () => void }) {
  const [draft, setDraft] = useState(actions.join('\n'))
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-md bg-slate-900 border border-slate-700/60 rounded-2xl p-5 shadow-2xl" onClick={e => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-slate-100 mb-3">自定义快捷提问</h3>
        <p className="text-xs text-slate-400 mb-3">每行一个，最多 8 条</p>
        <textarea value={draft} onChange={e => setDraft(e.target.value)} rows={8}
          className="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/50 resize-none" />
        <div className="flex justify-end gap-2 mt-3">
          <button onClick={() => setDraft(DEFAULT_QUICK_ACTIONS.join('\n'))}
            className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 border border-slate-700/50 hover:border-slate-600 transition-colors">恢复默认</button>
          <button onClick={onClose}
            className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 border border-slate-700/50 hover:border-slate-600 transition-colors">取消</button>
          <button onClick={() => { const lines = draft.split('\n').map(l => l.trim()).filter(Boolean).slice(0, 8); if (lines.length > 0) { onSave(lines); onClose() } }}
            className="px-4 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition-colors">保存</button>
        </div>
      </div>
    </div>
  )
}

function ToolSteps({ steps }: { steps: ToolStep[] }) {
  const [collapsed, setCollapsed] = useState(false)
  if (steps.length === 0) return null

  const allDone = steps.every(s => s.status === 'done')

  return (
    <div className="mb-2.5">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-1.5 text-[11px] text-slate-400 hover:text-slate-300 transition-colors mb-1.5"
      >
        <span className={`transition-transform duration-200 ${collapsed ? '' : 'rotate-90'}`}>▶</span>
        <span>
          {allDone
            ? `已调用 ${steps.length} 个工具`
            : `正在调用工具 (${steps.filter(s => s.status === 'done').length}/${steps.length})...`
          }
        </span>
      </button>
      {!collapsed && (
        <div className="tool-steps-timeline ml-1 space-y-1">
          {steps.map((step, i) => (
            <div key={`${step.name}-${i}`} className="flex items-center gap-2 py-0.5">
              <div className="relative flex items-center justify-center w-4 h-4 shrink-0">
                {step.status === 'running' ? (
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                ) : (
                  <span className="text-[10px] text-emerald-400">✓</span>
                )}
              </div>
              <span className="text-[11px]">{step.icon}</span>
              <span className="text-[11px] text-slate-300 font-medium">{step.displayName}</span>
              {step.inputSummary && (
                <span className="text-[10px] text-slate-500 truncate max-w-[180px]">{step.inputSummary}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function References({ refs }: { refs: Reference[] }) {
  if (refs.length === 0) return null
  return (
    <div className="mt-3 pt-2.5 border-t border-slate-700/30">
      <p className="text-[10px] text-slate-500 mb-1.5">引用来源</p>
      <div className="flex flex-wrap gap-1.5">
        {refs.map((ref, i) => (
          ref.url ? (
            <a
              key={i}
              href={ref.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[10px] text-emerald-400/80 hover:text-emerald-300 bg-emerald-500/5 border border-emerald-500/15 rounded-md px-2 py-0.5 transition-colors"
            >
              <span>🔗</span>
              <span className="max-w-[160px] truncate">{ref.title}</span>
            </a>
          ) : (
            <span key={i} className="inline-flex items-center gap-1 text-[10px] text-slate-400 bg-slate-700/20 border border-slate-700/30 rounded-md px-2 py-0.5">
              {ref.title}
            </span>
          )
        ))}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null)
  const [quickActions, setQuickActions] = useState(loadQuickActions)
  const [editingActions, setEditingActions] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const updateLast = (updater: (msg: Message) => Partial<Message>) => {
    setMessages(prev => {
      const updated = [...prev]
      const last = updated[updated.length - 1]
      updated[updated.length - 1] = { ...last, ...updater(last) }
      return updated
    })
  }

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return

    const userMsg: Message = { role: 'user', content: text.trim() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    const assistantMsg: Message = { role: 'assistant', content: '', images: [], steps: [], references: [] }
    setMessages(prev => [...prev, assistantMsg])

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text.trim(), session_id: 'web' }),
      })

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))

            if (data.type === 'tool_start') {
              updateLast(msg => ({
                steps: [...(msg.steps || []), {
                  id: data.id || data.name,
                  name: data.name,
                  icon: data.icon,
                  displayName: data.displayName,
                  inputSummary: data.inputSummary,
                  status: 'running' as const,
                }],
              }))
            } else if (data.type === 'tool_end') {
              const endId = data.id || data.name
              updateLast(msg => ({
                steps: (msg.steps || []).map(s =>
                  (s.id === endId || s.name === data.name) && s.status === 'running'
                    ? { ...s, status: 'done' as const }
                    : s
                ),
              }))
            } else if (data.type === 'token') {
              updateLast(msg => ({ content: msg.content + data.content }))
            } else if (data.type === 'done') {
              updateLast(msg => ({
                steps: (msg.steps || []).map(s => ({ ...s, status: 'done' as const })),
                ...(data.images?.length ? { images: data.images } : {}),
                ...(data.references?.length ? { references: data.references } : {}),
              }))
            }
          } catch {}
        }
      }
    } catch (err) {
      updateLast(() => ({ content: '网络错误，请检查后端服务是否启动。' }))
    }

    setLoading(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const handleSaveActions = (actions: string[]) => {
    setQuickActions(actions)
    saveQuickActions(actions)
  }

  const isEmpty = messages.length === 0

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {isEmpty ? (
          <div className="h-full flex flex-col items-center justify-center">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/15 flex items-center justify-center mb-6">
              <span className="text-3xl text-emerald-400 font-bold">A</span>
            </div>
            <h2 className="text-xl font-semibold text-slate-50 tracking-tight mb-2">
              A 股智能分析助手
            </h2>
            <p className="text-sm text-slate-400 mb-8">
              查行情 · 看指标 · 读财报 · 搜新闻 · 画K线
            </p>
            <div className="grid grid-cols-2 gap-3 max-w-lg w-full">
              {quickActions.map(action => (
                <button key={action} onClick={() => sendMessage(action)}
                  className="text-left text-sm text-slate-300 p-4 rounded-xl border border-slate-800/60 bg-slate-900/40 backdrop-blur-sm hover:bg-slate-800/60 hover:border-slate-700 transition-all duration-200">
                  {action}
                </button>
              ))}
            </div>
            <button onClick={() => setEditingActions(true)}
              className="mt-4 text-[11px] text-slate-500 hover:text-slate-300 transition-colors">
              自定义快捷提问
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-emerald-600/20 text-slate-100 border border-emerald-500/20'
                      : 'bg-slate-800/50 text-slate-200 border border-slate-700/40 backdrop-blur-sm'
                  }`}
                >
                  {/* 工具调用步骤 */}
                  {msg.role === 'assistant' && msg.steps && msg.steps.length > 0 && (
                    <ToolSteps steps={msg.steps} />
                  )}

                  {/* 正文 */}
                  {msg.role === 'assistant' ? (
                    msg.content ? (
                      <div className="markdown-body">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {stripImagePaths(msg.content)}
                        </ReactMarkdown>
                      </div>
                    ) : loading && i === messages.length - 1 && (!msg.steps || msg.steps.length === 0) ? (
                      <div className="flex gap-1.5 py-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    ) : null
                  ) : (
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  )}

                  {/* 图片 */}
                  {msg.images?.map((src, j) => (
                    <img key={j} src={src} alt="K线图"
                      className="mt-3 rounded-lg max-w-full border border-slate-700/50 cursor-pointer hover:opacity-90 transition-opacity"
                      onClick={() => setLightboxSrc(src)} />
                  ))}

                  {/* 引用来源 */}
                  {msg.role === 'assistant' && msg.references && msg.references.length > 0 && (
                    <References refs={msg.references} />
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="p-4 border-t border-slate-800/50">
        <div className="relative max-w-3xl mx-auto">
          <textarea ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown}
            placeholder="输入你的问题..." rows={1}
            className="w-full resize-none bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl px-4 py-3 pr-20 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/50 transition-all duration-200" />
          <button onClick={() => sendMessage(input)} disabled={!input.trim() || loading}
            className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200">
            发送
          </button>
        </div>
      </div>

      {lightboxSrc && <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />}
      {editingActions && <QuickActionEditor actions={quickActions} onSave={handleSaveActions} onClose={() => setEditingActions(false)} />}
    </div>
  )
}
