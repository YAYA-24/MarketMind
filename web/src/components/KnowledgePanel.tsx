import { useState, useEffect, useCallback, useRef } from 'react'

interface SourceItem {
  source: string
  file_type: string
  chunks: number
}

export default function KnowledgePanel() {
  const [sources, setSources] = useState<SourceItem[]>([])
  const [totalChunks, setTotalChunks] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchSources = useCallback(async () => {
    try {
      const res = await fetch('/api/knowledge')
      if (res.ok) {
        const data = await res.json()
        setSources(data.sources || [])
        setTotalChunks(data.total_chunks || 0)
      }
    } catch {}
  }, [])

  useEffect(() => { fetchSources() }, [fetchSources])

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setUploading(true)

    for (const file of Array.from(files)) {
      const formData = new FormData()
      formData.append('file', file)
      try {
        const res = await fetch('/api/knowledge/upload', { method: 'POST', body: formData })
        const data = await res.json()
        if (data.error) {
          alert(`上传失败: ${data.error}`)
        }
      } catch {
        alert(`上传 ${file.name} 时出错`)
      }
    }

    setUploading(false)
    fetchSources()
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleDelete = async (source: string) => {
    if (!confirm(`确定删除「${source}」的所有知识片段？`)) return
    await fetch(`/api/knowledge/${encodeURIComponent(source)}`, { method: 'DELETE' })
    fetchSources()
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleUpload(e.dataTransfer.files)
  }

  const FILE_TYPE_ICONS: Record<string, string> = {
    '.pdf': '📄',
    '.txt': '📝',
    '.md': '📋',
  }

  return (
    <div className="p-4 space-y-3">
      {/* 统计 */}
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>{sources.length} 个文件</span>
        <span>{totalChunks} 个知识片段</span>
      </div>

      {/* 上传区域 */}
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`flex flex-col items-center justify-center gap-1.5 p-4 rounded-xl border-2 border-dashed cursor-pointer transition-all duration-200 ${
          dragOver
            ? 'border-emerald-400 bg-emerald-500/10'
            : 'border-slate-700/50 bg-slate-800/30 hover:border-slate-600 hover:bg-slate-800/50'
        }`}
      >
        <span className="text-lg">{uploading ? '⏳' : '📁'}</span>
        <span className="text-xs text-slate-400">
          {uploading ? '正在上传并解析...' : '拖拽文件或点击上传'}
        </span>
        <span className="text-[10px] text-slate-500">支持 PDF、TXT、MD</span>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md"
          multiple
          className="hidden"
          onChange={e => handleUpload(e.target.files)}
        />
      </div>

      {/* 文件列表 */}
      {sources.length === 0 && (
        <p className="text-xs text-slate-500 text-center py-4">
          知识库为空，上传投资相关文档开始使用
        </p>
      )}

      {sources.map(item => (
        <div
          key={item.source}
          className="group p-3 rounded-xl border border-slate-800/60 bg-slate-900/40 backdrop-blur-sm hover:bg-slate-800/60 transition-all duration-200"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-200 truncate flex items-center gap-1.5">
                <span>{FILE_TYPE_ICONS[item.file_type] || '📄'}</span>
                <span className="truncate">{item.source}</span>
              </p>
              <p className="text-[10px] text-slate-500 mt-1">
                {item.chunks} 个片段
              </p>
            </div>
            <button
              onClick={() => handleDelete(item.source)}
              className="opacity-0 group-hover:opacity-100 text-xs text-red-400 hover:text-red-300 shrink-0 transition-opacity duration-200"
            >
              删除
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
