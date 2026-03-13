'use client'

import { useState } from 'react'
import { SessionSidebar } from '@/components/chat/SessionSidebar'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { ChatInput } from '@/components/chat/ChatInput'
import type { Session, Message } from '@/lib/chat-types'

const STUB_SESSIONS: Session[] = [
  {
    id: '1',
    title: 'Inventory API design',
    preview: 'How should I structure the endpoints?',
    updatedAt: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    messageCount: 6,
  },
  {
    id: '2',
    title: 'Python agent debugging',
    preview: 'The static check keeps failing on…',
    updatedAt: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    messageCount: 14,
  },
  {
    id: '3',
    title: 'LangGraph state design',
    preview: 'What is the difference between…',
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    messageCount: 9,
  },
]

const STUB_MESSAGES: Message[] = [
  {
    id: '1',
    role: 'assistant',
    content: `Hello! I'm your Agentic SDLC assistant. I can help you with:\n\n- Designing agent workflows and task structures\n- Reviewing generated code and suggesting improvements\n- Answering questions about the system architecture\n- Analysing uploaded files or documents\n\nYou can also upload files and images for me to analyse. How can I help you today?`,
    createdAt: new Date(Date.now() - 1000 * 60 * 10).toISOString(),
    attachments: [],
  },
]

export default function ChatPage() {
  const [sessions, setSessions]           = useState<Session[]>(STUB_SESSIONS)
  const [activeSessionId, setActiveSession] = useState<string>('1')
  const [messages, setMessages]           = useState<Message[]>(STUB_MESSAGES)
  const [loading, setLoading]             = useState(false)

  const activeSession = sessions.find(s => s.id === activeSessionId)

  const handleNewSession = () => {
    const id = String(Date.now())
    const session: Session = {
      id,
      title: 'New conversation',
      preview: '',
      updatedAt: new Date().toISOString(),
      messageCount: 0,
    }
    setSessions(prev => [session, ...prev])
    setActiveSession(id)
    setMessages([])
  }

  const handleDeleteSession = (id: string) => {
    setSessions(prev => prev.filter(s => s.id !== id))
    if (activeSessionId === id) {
      const remaining = sessions.filter(s => s.id !== id)
      if (remaining.length > 0) {
        setActiveSession(remaining[0].id)
      } else {
        handleNewSession()
      }
    }
  }

  const handleSend = async (content: string, attachments: File[]) => {
    if (!content.trim() && attachments.length === 0) return

    const userMsg: Message = {
      id:          String(Date.now()),
      role:        'user',
      content,
      createdAt:   new Date().toISOString(),
      attachments: attachments.map(f => ({ name: f.name, size: f.size, type: f.type })),
    }

    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    // Update session preview
    setSessions(prev => prev.map(s =>
      s.id === activeSessionId
        ? { ...s, preview: content.slice(0, 60), updatedAt: new Date().toISOString(), messageCount: s.messageCount + 1 }
        : s
    ))

    // Stub assistant reply — replace with real API call when backend is ready
    await new Promise(r => setTimeout(r, 1200))
    const assistantMsg: Message = {
      id:          String(Date.now() + 1),
      role:        'assistant',
      content:     `This is a placeholder response. The chat backend (LangGraph long-term memory + RAG) hasn't been wired yet.\n\nYou sent: "${content.slice(0, 80)}${content.length > 80 ? '…' : ''}"`,
      createdAt:   new Date().toISOString(),
      attachments: [],
    }
    setMessages(prev => [...prev, assistantMsg])
    setLoading(false)
  }

  return (
    <div className="flex h-[calc(100vh-56px-48px)] -m-6 overflow-hidden">
      <SessionSidebar
        sessions={sessions}
        activeId={activeSessionId}
        onSelect={setActiveSession}
        onNew={handleNewSession}
        onDelete={handleDeleteSession}
      />

      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Session title bar */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-surface flex-shrink-0">
          <div>
            <p className="text-sm font-sans font-semibold text-foreground">
              {activeSession?.title ?? 'New conversation'}
            </p>
            <p className="text-[11px] font-mono text-muted-fg">
              {messages.length} message{messages.length !== 1 ? 's' : ''}
              {' · '}
              <span className="text-accent/70">RAG · Long-term memory</span>
              <span className="ml-1.5 text-[10px] border border-border rounded px-1 py-0.5">coming soon</span>
            </p>
          </div>
        </div>

        {/* Messages */}
        <ChatWindow messages={messages} loading={loading} />

        {/* Input */}
        <ChatInput onSend={handleSend} loading={loading} />
      </div>
    </div>
  )
}
