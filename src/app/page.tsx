'use client'

import { useState, useCallback, useEffect } from 'react'
import Header from '@/components/Header'
import ProductGrid from '@/components/ProductGrid'
import Dashboard from '@/components/Dashboard'
import SearchResults from '@/components/SearchResults'
import Comments from '@/components/Comments'
import Recommendations from '@/components/Recommendations'
import Notifications from '@/components/Notifications'
import ShoppingCart from '@/components/ShoppingCart'
import AnalyticsWidget from '@/components/AnalyticsWidget'
import Footer from '@/components/Footer'

type RenderingStrategy = 'CSR' | 'SSR' | 'SSG' | 'ISR' | 'STREAM' | 'PARTIAL'

interface ComponentMetrics {
  componentName: string
  strategy: RenderingStrategy
  renderTime: number
  timestamp: number
}

export default function Home() {
  const [activeStrategy, setActiveStrategy] = useState<RenderingStrategy>('CSR')
  const [metrics, setMetrics] = useState<ComponentMetrics[]>([])
  const [showMetrics, setShowMetrics] = useState(false)

  const handleRenderComplete = useCallback((componentName: string, data: { renderTime: number; strategy: string }) => {
    setMetrics(prev => [
      ...prev.slice(-99), // Keep last 100 metrics
      {
        componentName,
        strategy: data.strategy as RenderingStrategy,
        renderTime: data.renderTime,
        timestamp: Date.now(),
      },
    ])
  }, [])

  const strategies: RenderingStrategy[] = ['CSR', 'SSR', 'SSG', 'ISR', 'STREAM', 'PARTIAL']

  const avgMetrics = metrics.length > 0
    ? {
        avgRenderTime: metrics.reduce((sum, m) => sum + m.renderTime, 0) / metrics.length,
        totalComponents: metrics.length,
        strategyDistribution: strategies.reduce((acc, s) => {
          acc[s] = metrics.filter(m => m.strategy === s).length
          return acc
        }, {} as Record<string, number>),
      }
    : null

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header 
        renderStrategy={activeStrategy}
        onRenderComplete={(data) => handleRenderComplete('Header', data)}
      />

      <main className="flex-1 max-w-7xl mx-auto px-4 py-8 w-full">
        {/* Strategy Selector */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Rendering Strategy Control</h2>
          <p className="text-gray-600 mb-4">
            Select a rendering strategy to see how it affects component performance.
          </p>
          
          <div className="flex flex-wrap gap-3">
            {strategies.map(strategy => (
              <button
                key={strategy}
                onClick={() => setActiveStrategy(strategy)}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  activeStrategy === strategy
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {strategy}
              </button>
            ))}
          </div>

          {/* Metrics Toggle */}
          <button
            onClick={() => setShowMetrics(!showMetrics)}
            className="mt-4 text-sm text-blue-600 hover:text-blue-800"
          >
            {showMetrics ? 'Hide' : 'Show'} Performance Metrics
          </button>

          {/* Metrics Display */}
          {showMetrics && avgMetrics && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div>
                  <p className="text-sm text-gray-500">Avg Render Time</p>
                  <p className="text-lg font-bold">{avgMetrics.avgRenderTime.toFixed(2)}ms</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Components Rendered</p>
                  <p className="text-lg font-bold">{avgMetrics.totalComponents}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Current Strategy</p>
                  <p className="text-lg font-bold">{activeStrategy}</p>
                </div>
              </div>
              
              <div className="flex gap-2 flex-wrap">
                {strategies.map(s => (
                  <span
                    key={s}
                    className={`px-2 py-1 rounded text-xs ${
                      s === activeStrategy ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {s}: {avgMetrics.strategyDistribution[s] || 0}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Components Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column */}
          <div className="space-y-8">
            <ProductGrid 
              renderStrategy={activeStrategy}
              limit={8}
              onRenderComplete={(data) => handleRenderComplete('ProductGrid', data)}
            />
            
            <SearchResults 
              renderStrategy={activeStrategy}
              onRenderComplete={(data) => handleRenderComplete('SearchResults', data)}
            />
            
            <Comments 
              postId={1}
              renderStrategy={activeStrategy}
              onRenderComplete={(data) => handleRenderComplete('Comments', data)}
            />
          </div>

          {/* Right Column */}
          <div className="space-y-8">
            <Dashboard 
              renderStrategy={activeStrategy}
              onRenderComplete={(data) => handleRenderComplete('Dashboard', data)}
            />
            
            <Recommendations 
              userId={1}
              renderStrategy={activeStrategy}
              onRenderComplete={(data) => handleRenderComplete('Recommendations', data)}
            />
            
            <Notifications 
              renderStrategy={activeStrategy}
              onRenderComplete={(data) => handleRenderComplete('Notifications', data)}
            />
            
            <ShoppingCart 
              userId={1}
              renderStrategy={activeStrategy}
              onRenderComplete={(data) => handleRenderComplete('ShoppingCart', data)}
            />
            
            <AnalyticsWidget 
              renderStrategy={activeStrategy}
              onRenderComplete={(data) => handleRenderComplete('AnalyticsWidget', data)}
            />
          </div>
        </div>
      </main>

      <Footer 
        renderStrategy={activeStrategy}
        onRenderComplete={(data) => handleRenderComplete('Footer', data)}
      />
    </div>
  )
}
