'use client'

import { useState, useEffect, useCallback } from 'react'
import { Product } from '@/types'
import { fetchProducts } from '@/api/dummyData'

interface ProductGridProps {
  renderStrategy?: string
  limit?: number
  onRenderComplete?: (metrics: { renderTime: number; strategy: string; dataSize: number }) => void
}

export default function ProductGrid({ 
  renderStrategy = 'CSR', 
  limit = 12,
  onRenderComplete 
}: ProductGridProps) {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hoveredProduct, setHoveredProduct] = useState<number | null>(null)

  const loadProducts = useCallback(async () => {
    const startTime = performance.now()
    setLoading(true)
    setError(null)
    
    try {
      const data = await fetchProducts(limit)
      setProducts(data)
      
      const renderTime = performance.now() - startTime
      onRenderComplete?.({ 
        renderTime, 
        strategy: renderStrategy, 
        dataSize: JSON.stringify(data).length 
      })
    } catch (err) {
      setError('Failed to load products')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [limit, renderStrategy, onRenderComplete])

  useEffect(() => {
    loadProducts()
  }, [loadProducts])

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 p-4">
        {Array.from({ length: limit }).map((_, i) => (
          <div key={i} className="bg-white rounded-lg shadow-md p-4 animate-pulse">
            <div className="h-48 bg-gray-200 rounded mb-4"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 m-4">
        <p className="text-red-600">{error}</p>
        <button 
          onClick={loadProducts}
          className="mt-2 text-sm text-blue-600 hover:underline"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Products</h2>
        <span className="text-sm text-gray-500">
          {products.length} items • {renderStrategy}
        </span>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {products.map((product) => (
          <div
            key={product.id}
            className={`bg-white rounded-lg shadow-md overflow-hidden transition-all duration-200 ${
              hoveredProduct === product.id ? 'shadow-lg scale-105' : ''
            }`}
            onMouseEnter={() => setHoveredProduct(product.id)}
            onMouseLeave={() => setHoveredProduct(null)}
          >
            <div className="h-48 bg-gray-100 flex items-center justify-center p-4">
              <img
                src={product.image}
                alt={product.title}
                className="max-h-full max-w-full object-contain"
                loading="lazy"
              />
            </div>
            
            <div className="p-4">
              <h3 className="font-semibold text-gray-800 line-clamp-2 mb-2">
                {product.title}
              </h3>
              
              <p className="text-sm text-gray-600 line-clamp-2 mb-3">
                {product.description}
              </p>
              
              <div className="flex items-center justify-between">
                <span className="text-lg font-bold text-green-600">
                  ${product.price.toFixed(2)}
                </span>
                
                <div className="flex items-center">
                  <span className="text-yellow-500 mr-1">★</span>
                  <span className="text-sm text-gray-600">
                    {product.rating.rate.toFixed(1)} ({product.rating.count})
                  </span>
                </div>
              </div>
              
              <div className="mt-3 flex gap-2">
                <button className="flex-1 bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition">
                  Add to Cart
                </button>
                <button className="p-2 border border-gray-300 rounded hover:bg-gray-50 transition">
                  ♡
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
