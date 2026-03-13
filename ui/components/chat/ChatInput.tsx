'use client'

import { useRef, useState, KeyboardEvent } from 'react'
import { Send, Paperclip, Image, X, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  onSend: (content: string, attachments: File[]) => void
  loading: boolean
}

export function ChatInput({ onSend, loading }: Props) {
  const [text, setText]               = useState('')
  const [attachments, setAttachments] = useState<File[]>([])
  const fileRef     = useRef<HTMLInputElement>(null)
  const imageRef    = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const canSend = (text.trim().length > 0 || attachments.length > 0) && !loading

  const handleSend = () => {
    if (!canSend) return
    onSend(text, attachments)
    setText('')
    setAttachments([])
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`
  }

  const addFiles = (files: FileList | null) => {
    if (!files) return
    setAttachments(prev => [...prev, ...Array.from(files)])
  }

  return (
    <div className="flex-shrink-0 border-t border-border bg-surface px-4 py-3">

      {/* Attachment chips */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {attachments.map((file, i) => (
            <div key={i} className="flex items-center gap-1.5 bg-muted border border-border rounded px-2 py-1 text-[11px] font-mono text-muted-fg">
              {file.type.startsWith('image/')
                ? <Image className="w-3 h-3 text-accent" />
                : <Paperclip className="w-3 h-3 text-accent" />
              }
              <span className="max-w-[100px] truncate">{file.name}</span>
              <button onClick={() => setAttachments(prev => prev.filter((_, j) => j !== i))} className="hover:text-danger transition-colors">
                <X className="w-2.5 h-2.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2">
        {/* Hidden file inputs */}
        <input ref={fileRef} type="file" multiple accept=".txt,.md,.pdf,.py,.ts,.js,.go" className="hidden" onChange={e => addFiles(e.target.files)} />
        <input ref={imageRef} type="file" multiple accept="image/*" className="hidden" onChange={e => addFiles(e.target.files)} />

        {/* Upload buttons */}
        <div className="flex gap-1 pb-1.5">
          <button onClick={() => fileRef.current?.click()} className="w-7 h-7 rounded flex items-center justify-center text-muted-fg hover:text-accent hover:bg-accent-dim transition-all" title="Attach file">
            <Paperclip className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => imageRef.current?.click()} className="w-7 h-7 rounded flex items-center justify-center text-muted-fg hover:text-accent hover:bg-accent-dim transition-all" title="Attach image">
            <Image className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleTextChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything… (Shift+Enter for new line)"
          rows={1}
          disabled={loading}
          className={cn(
            'flex-1 bg-muted border border-border rounded-lg px-3 py-2 text-sm font-mono',
            'text-foreground placeholder:text-muted-fg resize-none leading-relaxed',
            'focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all',
            'disabled:opacity-50 disabled:cursor-not-allowed min-h-[38px] max-h-[160px]'
          )}
        />

        {/* Send */}
        <button
          onClick={handleSend}
          disabled={!canSend}
          className={cn(
            'w-8 h-8 rounded-lg flex items-center justify-center transition-all flex-shrink-0 mb-0.5',
            canSend ? 'bg-accent text-background hover:opacity-90 active:scale-95' : 'bg-muted text-muted-fg cursor-not-allowed'
          )}
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
        </button>
      </div>

      <p className="text-[10px] font-mono text-muted-fg/50 mt-2 text-center">
        Chat backend not yet wired · responses are stubs · RAG + session memory coming soon
      </p>
    </div>
  )
}
