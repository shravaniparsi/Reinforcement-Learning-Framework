'use client'

import { useState, useEffect } from 'react'
import { Product } from '@/types'
import { fetchRecommendations } from '@/api/dummyData'

interface RecommendationsProps {
  userId?: number
  renderStrategy?: string
  onRenderComplete?: (metrics: { renderTime: number; strategy: string }) => void
}

export default function Recommendations({ 
  userId = 1, 
  renderStrategy = 'CSR', 
  onRenderComplete 
}: RecommendationsProps) {
  const [recommendations, setRecommendations] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    const loadRecommendations = async () => {
      const startTime = performance.now()
      setLoading(true)

      try {
        const data = await fetchRecommendations(userId, 6)
        setRecommendations(data)

        const renderTime = performance.now() - startTime
        onRenderComplete?.({ renderTime, strategy: renderStrategy })
      } catch (err) {
        console.error('Failed to load recommendations:', err)
      } finally {
        setLoading(false)
      }
    }

    loadRecommendations()
  }, [userId, renderStrategy, onRenderComplete])

  const handleNext = () => {
    setCurrentIndex(prev => (prev + 1) % recommendations.length)
  }

  const handlePrev = () => {
    setCurrentIndex(prev => (prev - 1 + recommendations.length) % recommendations.length)
  }

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg shadow-md p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-white/20 rounded w-1/3 mb-4"></div>
          <div className="h-48 bg-white/20 rounded mb-4"></div>
          <div className="h-4 bg-white/20 rounded w-2/3"></div>
        </div>
      </div>
    )
  }

  if (recommendations.length === 0) {
    return null
  }

  const currentProduct = recommendations[currentIndex]

  return (
    <div className="bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg shadow-md p-6 text-white">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Recommended for You</h2>
        <div className="flex gap-2">
          <button
            onClick={handlePrev}
            className="w-8 h-8 bg-white/20 rounded-full hover:bg-white/30 transition flex items-center justify-center"
          >
            ←
          </button>
          <button
            onClick={handleNext}
            className="w-8 h-8 bg-white/20 rounded-full hover:bg-white/30 transition flex items-center justify-center"
          >
            →
          </button>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Main Product */}
        <div className="flex-1">
          <div className="bg-white rounded-lg p-4 mb-4">
            <img
              src={currentProduct.image}
              alt={currentProduct.title}
              className="w-full h-48 object-contain"
            />
          </div>
          <h3 className="font-semibold text-lg mb-2">{currentProduct.title}</h3>
          <p className="text-white/80 text-sm mb-3 line-clamp-2">
            {currentProduct.description}
          </p>
          <div className="flex items-center gap-4">
            <span className="text-2xl font-bold">${currentProduct.price.toFixed(2)}</span>
            <span className="text-white/80">
              ★ {currentProduct.rating.rate.toFixed(1)} ({currentProduct.rating.count})
            </span>
          </div>
          <button className="mt-4 w-full bg-white text-purple-600 font-semibold py-2 rounded-lg hover:bg-gray-100 transition">
            Add to Cart
          </button>
        </div>

        {/* Thumbnail Navigation */}
        <div className="hidden md:flex flex-col gap-2">
          {recommendations.map((product, idx) => (
            <button
              key={product.id}
              onClick={() => setCurrentIndex(idx)}
              className={`w-16 h-16 bg-white rounded-lg p-1 transition ${
                idx === currentIndex
                  ? 'ring-2 ring-white'
                  : 'opacity-60 hover:opacity-100'
              }`}
            >
              <img
                src={product.image}
                alt={product.title}
                className="w-full h-full object-contain"
              />
            </button>
          ))}
        </div>
      </div>

      {/* Progress Dots */}
      <div className="flex justify-center gap-2 mt-6">
        {recommendations.map((_, idx) => (
          <button
            key={idx}
            onClick={() => setCurrentIndex(idx)}
            className={`w-2 h-2 rounded-full transition ${
              idx === currentIndex ? 'bg-white' : 'bg-white/40 hover:bg-white/60'
            }`}
          />
        ))}
      </div>
    </div>
  )
}
