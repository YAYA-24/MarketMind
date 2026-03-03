import { useState, useEffect, useCallback } from 'react'

interface MonitorRule {
  id: number
  symbol: string
  condition: string
  threshold: number
  description: string
  enabled: boolean
  created_at: string
  last_triggered: string | null
}

const CONDITION_LABELS: Record<string, string> = {
  price_above: '价格高于',
  price_below: '价格低于',
  change_pct_above: '涨幅超过',
  change_pct_below: '跌幅超过',
  volume_ratio_above: '量比超过',
}

const CONDITION_OPTIONS = [
  { value: 'price_above', label: '价格高于' },
  { value: 'price_below', label: '价格低于' },
  { value: 'change_pct_above', label: '涨幅超过 (%)' },
  { value: 'change_pct_below', label: '跌幅超过 (%)' },
]

export default function MonitorPanel() {
  const [rules, setRules] = useState<MonitorRule[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ symbol: '', condition: 'price_below', threshold: '', description: '' })
  const [submitting, setSubmitting] = useState(false)

  const fetchRules = useCallback(async () => {
    try {
      const res = await fetch('/api/monitors')
      if (res.ok) setRules(await res.json())
    } catch {}
  }, [])

  useEffect(() => { fetchRules() }, [fetchRules])

  const handleAdd = async () => {
    if (!form.symbol || !form.threshold) return
    setSubmitting(true)
    try {
      await fetch('/api/monitors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: form.symbol,
          condition: form.condition,
          threshold: parseFloat(form.threshold),
          description: form.description || `${form.symbol} ${CONDITION_LABELS[form.condition]} ${form.threshold}`,
        }),
      })
      setForm({ symbol: '', condition: 'price_below', threshold: '', description: '' })
      setShowAdd(false)
      fetchRules()
    } catch {}
    setSubmitting(false)
  }

  const handleDelete = async (id: number) => {
    await fetch(`/api/monitors/${id}`, { method: 'DELETE' })
    fetchRules()
  }

  return (
    <div className="p-4 space-y-3">
      <button
        onClick={() => setShowAdd(!showAdd)}
        className="w-full text-xs font-medium text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 rounded-lg px-3 py-2 hover:bg-emerald-500/20 transition-all duration-200"
      >
        {showAdd ? '取消' : '+ 添加监控规则'}
      </button>

      {showAdd && (
        <div className="space-y-2 p-3 rounded-xl border border-slate-700/50 bg-slate-800/40">
          <input
            value={form.symbol}
            onChange={e => setForm({ ...form, symbol: e.target.value })}
            placeholder="股票代码 (如 600519)"
            className="w-full bg-slate-900/60 border border-slate-700/50 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/50"
          />
          <select
            value={form.condition}
            onChange={e => setForm({ ...form, condition: e.target.value })}
            className="w-full bg-slate-900/60 border border-slate-700/50 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-emerald-500/50"
          >
            {CONDITION_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <input
            value={form.threshold}
            onChange={e => setForm({ ...form, threshold: e.target.value })}
            placeholder="阈值 (如 1400)"
            type="number"
            className="w-full bg-slate-900/60 border border-slate-700/50 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/50"
          />
          <input
            value={form.description}
            onChange={e => setForm({ ...form, description: e.target.value })}
            placeholder="备注 (可选)"
            className="w-full bg-slate-900/60 border border-slate-700/50 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/50"
          />
          <button
            onClick={handleAdd}
            disabled={!form.symbol || !form.threshold || submitting}
            className="w-full text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-3 py-2 disabled:opacity-30 transition-all duration-200"
          >
            确认添加
          </button>
        </div>
      )}

      {rules.length === 0 && !showAdd && (
        <p className="text-xs text-slate-500 text-center py-6">
          暂无监控规则
        </p>
      )}

      {rules.map(rule => (
        <div
          key={rule.id}
          className="group p-3 rounded-xl border border-slate-800/60 bg-slate-900/40 backdrop-blur-sm hover:bg-slate-800/60 transition-all duration-200"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-200 truncate">
                {rule.description}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {rule.symbol} · {CONDITION_LABELS[rule.condition] || rule.condition} {rule.threshold}
              </p>
            </div>
            <button
              onClick={() => handleDelete(rule.id)}
              className="opacity-0 group-hover:opacity-100 text-xs text-red-400 hover:text-red-300 ml-2 transition-opacity duration-200"
            >
              删除
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
