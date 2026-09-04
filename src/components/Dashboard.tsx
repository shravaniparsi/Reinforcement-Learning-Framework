'use client'

import { useState, useEffect, useMemo } from 'react'
import { fetchAnalytics } from '@/api/dummyData'

interface DashboardProps {
  renderStrategy?: string
  onRenderComplete?: (metrics: { renderTime: number; strategy: string }) => void
}

interface AnalyticsData {
  totalViews: number
  uniqueVisitors: number
  avgSessionDuration: number
  bounceRate: number
  topPages: { page: string; views: number }[]
  dailyStats: { date: string; views: number; conversions: number }[]
}

export default function Dashboard({ renderStrategy = 'CSR', onRenderComplete }: DashboardProps) {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedPeriod, setSelectedPeriod] = useState<'7d' | '30d' | '90d'>('30d')
  const [hoveredBar, setHoveredBar] = useState<number | null>(null)

  useEffect(() => {
    const loadAnalytics = async () => {
      const startTime = performance.now()
      setLoading(true)
      
      try {
        const data = await fetchAnalytics()
        setAnalytics(data)
        
        const renderTime = performance.now() - startTime
        onRenderComplete?.({ renderTime, strategy: renderStrategy })
      } catch (err) {
        console.error('Failed to load analytics:', err)
      } finally {
        setLoading(false)
      }
    }
    
    loadAnalytics()
  }, [renderStrategy, onRenderComplete])

  const chartData = useMemo(() => {
    if (!analytics) return []
    
    const days = selectedPeriod === '7d' ? 7 : selectedPeriod === '30d' ? 30 : 90
    return analytics.dailyStats.slice(-days)
  }, [analytics, selectedPeriod])

  const maxValue = useMemo(() => {
    return Math.max(...chartData.map(d => d.views))
  }, [chartData])

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-6"></div>
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (!analytics) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">Failed to load analytics data</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Analytics Dashboard</h2>
        <div className="flex gap-2">
          {(['7d', '30d', '90d'] as const).map(period => (
            <button
              key={period}
              onClick={() => setSelectedPeriod(period)}
              className={`px-3 py-1 rounded text-sm ${
                selectedPeriod === period
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {period}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg p-4 text-white">
          <p className="text-sm opacity-80">Total Views</p>
          <p className="text-2xl font-bold">{analytics.totalViews.toLocaleString()}</p>
        </div>
        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-lg p-4 text-white">
          <p className="text-sm opacity-80">Unique Visitors</p>
          <p className="text-2xl font-bold">{analytics.uniqueVisitors.toLocaleString()}</p>
        </div>
        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg p-4 text-white">
          <p className="text-sm opacity-80">Avg Session</p>
          <p className="text-2xl font-bold">{Math.floor(analytics.avgSessionDuration / 60)}m {analytics.avgSessionDuration % 60}s</p>
        </div>
        <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg p-4 text-white">
          <p className="text-sm opacity-80">Bounce Rate</p>
          <p className="text-2xl font-bold">{(analytics.bounceRate * 100).toFixed(1)}%</p>
        </div>
      </div>

      {/* Chart */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold mb-4">Views Over Time</h3>
        <div className="h-64 flex items-end gap-1">
          {chartData.map((stat, idx) => (
            <div
              key={idx}
              className="flex-1 flex flex-col items-center"
              onMouseEnter={() => setHoveredBar(idx)}
              onMouseLeave={() => setHoveredBar(null)}
            >
              <div
                className="w-full bg-gradient-to-t from-blue-500 to-blue-400 rounded-t transition-all duration-200 hover:from-blue-600 hover:to-blue-500"
                style={{
                  height: `${(stat.views / maxValue) * 200}px`,
                  opacity: hoveredBar === idx ? 1 : 0.8,
                }}
              />
              {hoveredBar === idx && (
                <div className="absolute -mt-8 bg-gray-900 text-white text-xs px-2 py-1 rounded">
                  {stat.views.toLocaleString()} views
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-2">
          <span>{chartData[0]?.date}</span>
          <span>{chartData[chartData.length - 1]?.date}</span>
        </div>
      </div>

      {/* Top Pages */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Top Pages</h3>
        <div className="space-y-3">
          {analytics.topPages.map((page, idx) => (
            <div key={idx} className="flex items-center gap-4">
              <span className="text-sm font-mono text-gray-600 w-32">{page.page}</span>
              <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-green-400 to-green-500 rounded-full"
                  style={{
                    width: `${(page.views / analytics.topPages[0].views) * 100}%`,
                  }}
                />
              </div>
              <span className="text-sm text-gray-600 w-20 text-right">
                {page.views.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
