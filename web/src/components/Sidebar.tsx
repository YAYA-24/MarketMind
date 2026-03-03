import { useState } from 'react'
import MonitorPanel from './MonitorPanel'
import KnowledgePanel from './KnowledgePanel'

type Tab = 'monitor' | 'knowledge'

export default function Sidebar() {
  const [tab, setTab] = useState<Tab>('monitor')

  return (
    <aside className="w-80 border-l border-slate-800/50 bg-slate-900/60 backdrop-blur-md flex flex-col overflow-hidden">
      <div className="h-14 flex items-center border-b border-slate-800/50">
        <button
          onClick={() => setTab('monitor')}
          className={`flex-1 h-full text-xs font-semibold tracking-tight transition-colors duration-200 ${
            tab === 'monitor'
              ? 'text-emerald-400 border-b-2 border-emerald-400'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          监控面板
        </button>
        <button
          onClick={() => setTab('knowledge')}
          className={`flex-1 h-full text-xs font-semibold tracking-tight transition-colors duration-200 ${
            tab === 'knowledge'
              ? 'text-emerald-400 border-b-2 border-emerald-400'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          知识库
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {tab === 'monitor' ? <MonitorPanel /> : <KnowledgePanel />}
      </div>
    </aside>
  )
}
