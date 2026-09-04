'use client'

import { useState, useEffect, useMemo } from 'react'
import { fetchAnalytics } from '@/api/dummyData'

interface AnalyticsWidgetProps {
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

export default function AnalyticsWidget({ renderStrategy = 'CSR', onRenderComplete }: AnalyticsWidgetProps) {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [chartType, setChartType] = useState<'views' | 'conversions'>('views')
  const [showTooltip, setShowTooltip] = useState<number | null>(null)

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
    return analytics.dailyStats.slice(-14) // Last 14 days
  }, [analytics])

  const maxValue = useMemo(() => {
    if (!analytics) return 1
    return Math.max(
      ...chartData.map(d => chartType === 'views' ? d.views : d.conversions)
    )
  }, [chartData, chartType, analytics])

  const conversionRate = useMemo(() => {
    if (!analytics) return 0
    const totalConversions = analytics.dailyStats.reduce((sum, d) => sum + d.conversions, 0)
    return (totalConversions / analytics.totalViews) * 100
  }, [analytics])

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-3 gap-4 mb-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="h-40 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (!analytics) {
    return null
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold">Analytics Widget</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setChartType('views')}
            className={`px-3 py-1 rounded text-sm ${
              chartType === 'views'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600'
            }`}
          >
            Views
          </button>
          <button
            onClick={() => setChartType('conversions')}
            className={`px-3 py-1 rounded text-sm ${
              chartType === 'conversions'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600'
            }`}
          >
            Conversions
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4">
          <p className="text-sm text-blue-600 mb-1">Total Views</p>
          <p className="text-2xl font-bold text-blue-800">
            {analytics.totalViews.toLocaleString()}
          </p>
        </div>
        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4">
          <p className="text-sm text-green-600 mb-1">Unique Visitors</p>
          <p className="text-2xl font-bold text-green-800">
            {analytics.uniqueVisitors.toLocaleString()}
          </p>
        </div>
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4">
          <p className="text-sm text-purple-600 mb-1">Conversion Rate</p>
          <p className="text-2xl font-bold text-purple-800">
            {conversionRate.toFixed(2)}%
          </p>
        </div>
      </div>

      {/* Mini Chart */}
      <div className="mb-6">
        <div className="h-32 flex items-end gap-1">
          {chartData.map((stat, idx) => {
            const value = chartType === 'views' ? stat.views : stat.conversions
            const height = (value / maxValue) * 120

            return (
              <div
                key={idx}
                className="relative flex-1"
                onMouseEnter={() => setShowTooltip(idx)}
                onMouseLeave={() => setShowTooltip(null)}
              >
                <div
                  className={`w-full rounded-t transition-all duration-200 ${
                    chartType === 'views'
                      ? 'bg-gradient-to-t from-blue-500 to-blue-400'
                      : 'bg-gradient-to-t from-green-500 to-green-400'
                  }`}
                  style={{
                    height: `${height}px`,
                    opacity: showTooltip === idx ? 1 : 0.8,
                  }}
                />
                {showTooltip === idx && (
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                    {value.toLocaleString()} {chartType === 'views' ? 'views' : 'conversions'}
                    <br />
                    {stat.date}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Top Pages */}
      <div>
        <h3 className="text-sm font-semibold text-gray-600 mb-3">Top Pages</h3>
        <div className="space-y-2">
          {analytics.topPages.slice(0, 3).map((page, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <span className="text-sm font-mono text-gray-500 w-24 truncate">{page.page}</span>
              <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-400 to-blue-500 rounded-full"
                  style={{
                    width: `${(page.views / analytics.topPages[0].views) * 100}%`,
                  }}
                />
              </div>
              <span className="text-xs text-gray-500 w-16 text-right">
                {page.views.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
