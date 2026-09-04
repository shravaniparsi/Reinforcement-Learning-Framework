'use client'

import { useState, useEffect, useCallback } from 'react'
import { Comment } from '@/types'
import { fetchComments } from '@/api/dummyData'

interface CommentsProps {
  postId?: number
  renderStrategy?: string
  onRenderComplete?: (metrics: { renderTime: number; strategy: string }) => void
}

export default function Comments({ 
  postId = 1, 
  renderStrategy = 'CSR', 
  onRenderComplete 
}: CommentsProps) {
  const [comments, setComments] = useState<Comment[]>([])
  const [loading, setLoading] = useState(true)
  const [newComment, setNewComment] = useState('')
  const [replyingTo, setReplyingTo] = useState<number | null>(null)
  const [replyText, setReplyText] = useState('')
  const [sortBy, setSortBy] = useState<'newest' | 'oldest'>('newest')

  const loadComments = useCallback(async () => {
    const startTime = performance.now()
    setLoading(true)

    try {
      const data = await fetchComments(postId, 30)
      setComments(data)

      const renderTime = performance.now() - startTime
      onRenderComplete?.({ renderTime, strategy: renderStrategy })
    } catch (err) {
      console.error('Failed to load comments:', err)
    } finally {
      setLoading(false)
    }
  }, [postId, renderStrategy, onRenderComplete])

  useEffect(() => {
    loadComments()
  }, [loadComments])

  const handleSubmitComment = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newComment.trim()) return

    const comment: Comment = {
      id: Date.now(),
      postId,
      user: 'current-user',
      body: newComment,
    }

    setComments(prev => [comment, ...prev])
    setNewComment('')
  }

  const handleSubmitReply = (commentId: number) => {
    if (!replyText.trim()) return

    const reply: Comment = {
      id: Date.now(),
      postId,
      user: 'current-user',
      body: replyText,
    }

    setComments(prev => {
      const idx = prev.findIndex(c => c.id === commentId)
      if (idx === -1) return prev
      const newComments = [...prev]
      newComments.splice(idx + 1, 0, reply)
      return newComments
    })

    setReplyText('')
    setReplyingTo(null)
  }

  const sortedComments = [...comments].sort((a, b) => {
    return sortBy === 'newest' ? b.id - a.id : a.id - b.id
  })

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">
          Comments ({comments.length})
        </h2>
        <div className="flex gap-2">
          <button
            onClick={() => setSortBy('newest')}
            className={`px-3 py-1 rounded text-sm ${
              sortBy === 'newest'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600'
            }`}
          >
            Newest
          </button>
          <button
            onClick={() => setSortBy('oldest')}
            className={`px-3 py-1 rounded text-sm ${
              sortBy === 'oldest'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600'
            }`}
          >
            Oldest
          </button>
        </div>
      </div>

      {/* Comment Form */}
      <form onSubmit={handleSubmitComment} className="mb-8">
        <textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Write a comment..."
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
          rows={3}
        />
        <div className="flex justify-end mt-2">
          <button
            type="submit"
            disabled={!newComment.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Post Comment
          </button>
        </div>
      </form>

      {/* Loading State */}
      {loading && (
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="animate-pulse flex gap-4">
              <div className="w-10 h-10 bg-gray-200 rounded-full"></div>
              <div className="flex-1">
                <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Comments List */}
      {!loading && (
        <div className="space-y-6">
          {sortedComments.map(comment => (
            <div key={comment.id} className="border-b border-gray-100 pb-6 last:border-0">
              <div className="flex gap-4">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white font-semibold">
                  {comment.user.charAt(0).toUpperCase()}
                </div>
                
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-semibold text-gray-800">{comment.user}</span>
                    <span className="text-xs text-gray-400">
                      #{comment.id}
                    </span>
                  </div>
                  
                  <p className="text-gray-700 mb-3">{comment.body}</p>
                  
                  <div className="flex gap-4 text-sm">
                    <button className="text-gray-500 hover:text-blue-600">
                      ♡ Like
                    </button>
                    <button
                      onClick={() => setReplyingTo(replyingTo === comment.id ? null : comment.id)}
                      className="text-gray-500 hover:text-blue-600"
                    >
                      ↩ Reply
                    </button>
                  </div>

                  {/* Reply Form */}
                  {replyingTo === comment.id && (
                    <div className="mt-4 pl-4 border-l-2 border-blue-200">
                      <textarea
                        value={replyText}
                        onChange={(e) => setReplyText(e.target.value)}
                        placeholder={`Reply to ${comment.user}...`}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm resize-none"
                        rows={2}
                      />
                      <div className="flex justify-end gap-2 mt-2">
                        <button
                          onClick={() => setReplyingTo(null)}
                          className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleSubmitReply(comment.id)}
                          disabled={!replyText.trim()}
                          className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                        >
                          Reply
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {comments.length === 0 && (
            <p className="text-center text-gray-500 py-8">
              No comments yet. Be the first to comment!
            </p>
          )}
        </div>
      )}
    </div>
  )
}
