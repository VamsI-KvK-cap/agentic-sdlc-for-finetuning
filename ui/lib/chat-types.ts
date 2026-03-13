export interface Attachment {
  name: string
  size: number
  type: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
  attachments: Attachment[]
}

export interface Session {
  id: string
  title: string
  preview: string
  updatedAt: string
  messageCount: number
}
