'use client'

import { useState, useEffect, useCallback } from 'react'
import { Notification } from '@/types'
import { fetchNotifications } from '@/api/dummyData'

interface NotificationsProps {
  renderStrategy?: string
  onRenderComplete?: (metrics: { renderTime: number; strategy: string }) => void
}

export default function Notifications({ renderStrategy = 'CSR', onRenderComplete }: NotificationsProps) {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'unread' | 'read'>('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const loadNotifications = useCallback(async () => {
    const startTime = performance.now()
    setLoading(true)

    try {
      const data = await fetchNotifications(15)
      setNotifications(data)

      const renderTime = performance.now() - startTime
      onRenderComplete?.({ renderTime, strategy: renderStrategy })
    } catch (err) {
      console.error('Failed to load notifications:', err)
    } finally {
      setLoading(false)
    }
  }, [renderStrategy, onRenderComplete])

  useEffect(() => {
    loadNotifications()
  }, [loadNotifications])

  const filteredNotifications = notifications.filter(n => {
    if (filter === 'unread') return !n.title.includes('Read')
    if (filter === 'read') return n.title.includes('Read')
    return true
  })

  const markAsRead = (id: string) => {
    setNotifications(prev =>
      prev.map(n => (n.id === id ? { ...n, title: `Read: ${n.title}` } : n))
    )
  }

  const markAllAsRead = () => {
    setNotifications(prev =>
      prev.map(n => ({ ...n, title: n.title.startsWith('Read:') ? n.title : `Read: ${n.title}` }))
    )
  }

  const clearAll = () => {
    setNotifications([])
  }

  const getIcon = (type: Notification['type']) => {
    switch (type) {
      case 'info': return 'ℹ️'
      case 'warning': return '⚠️'
      case 'success': return '✅'
      case 'error': return '❌'
    }
  }

  const getColor = (type: Notification['type']) => {
    switch (type) {
      case 'info': return 'bg-blue-50 border-blue-200'
      case 'warning': return 'bg-yellow-50 border-yellow-200'
      case 'success': return 'bg-green-50 border-green-200'
      case 'error': return 'bg-red-50 border-red-200'
    }
  }

  const unreadCount = notifications.filter(n => !n.title.startsWith('Read:')).length

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold">Notifications</h2>
          {unreadCount > 0 && (
            <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
              {unreadCount}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={markAllAsRead}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Mark all read
          </button>
          <button
            onClick={clearAll}
            className="text-sm text-red-600 hover:text-red-800"
          >
            Clear all
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-4">
        {(['all', 'unread', 'read'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm capitalize transition ${
              filter === f
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="animate-pulse flex gap-4 p-4 bg-gray-50 rounded-lg">
              <div className="w-10 h-10 bg-gray-200 rounded-full"></div>
              <div className="flex-1">
                <div className="h-4 bg-gray-200 rounded w-1/3 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-2/3"></div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Notifications List */}
      {!loading && (
        <div className="space-y-3">
          {filteredNotifications.map(notification => (
            <div
              key={notification.id}
              className={`p-4 rounded-lg border transition-all cursor-pointer ${getColor(notification.type)} ${
                expandedId === notification.id ? 'shadow-md' : ''
              }`}
              onClick={() => {
                setExpandedId(expandedId === notification.id ? null : notification.id)
                markAsRead(notification.id)
              }}
            >
              <div className="flex items-start gap-4">
                <span className="text-xl">{getIcon(notification.type)}</span>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-gray-800">{notification.title}</h3>
                    <span className="text-xs text-gray-500">
                      {notification.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm mt-1">{notification.message}</p>
                  
                  {expandedId === notification.id && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-sm text-gray-500">
                        Notification ID: {notification.id}
                      </p>
                      <div className="flex gap-2 mt-2">
                        <button className="text-sm text-blue-600 hover:underline">
                          View Details
                        </button>
                        <button className="text-sm text-gray-500 hover:underline">
                          Dismiss
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {filteredNotifications.length === 0 && (
            <div className="text-center py-8">
              <p className="text-gray-500">
                {filter === 'all' 
                  ? 'No notifications'
                  : filter === 'unread'
                  ? 'No unread notifications'
                  : 'No read notifications'}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
