import { useState } from 'react'
import ChatWindow from './components/ChatWindow'
import Sidebar from './components/Sidebar'

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className="flex h-screen overflow-hidden">
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 flex items-center justify-between px-6 border-b border-slate-800/50 bg-slate-900/60 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
              <span className="text-emerald-400 text-sm font-bold">A</span>
            </div>
            <h1 className="text-sm font-semibold text-slate-50 tracking-tight">
              A 股智能分析助手
            </h1>
          </div>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="text-xs text-slate-400 hover:text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700/50 hover:border-slate-600 transition-all duration-200"
          >
            {sidebarOpen ? '收起面板' : '工具面板'}
          </button>
        </header>
        <ChatWindow />
      </div>
      {sidebarOpen && <Sidebar />}
    </div>
  )
}
