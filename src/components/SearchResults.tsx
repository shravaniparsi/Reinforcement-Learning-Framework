'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { Product } from '@/types'
import { searchProducts } from '@/api/dummyData'

interface SearchResultsProps {
  renderStrategy?: string
  onRenderComplete?: (metrics: { renderTime: number; strategy: string }) => void
}

export default function SearchResults({ renderStrategy = 'CSR', onRenderComplete }: SearchResultsProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Product[]>([])
  const [loading, setLoading] = useState(false)
  const [searchHistory, setSearchHistory] = useState<string[]>([])
  const [sortBy, setSortBy] = useState<'relevance' | 'price' | 'rating'>('relevance')

  const performSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([])
      return
    }

    const startTime = performance.now()
    setLoading(true)

    try {
      const data = await searchProducts(searchQuery, 20)
      setResults(data)
      
      // Add to search history
      setSearchHistory(prev => {
        const newHistory = [searchQuery, ...prev.filter(q => q !== searchQuery)].slice(0, 5)
        return newHistory
      })

      const renderTime = performance.now() - startTime
      onRenderComplete?.({ renderTime, strategy: renderStrategy })
    } catch (err) {
      console.error('Search failed:', err)
    } finally {
      setLoading(false)
    }
  }, [renderStrategy, onRenderComplete])

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      performSearch(query)
    }, 300)

    return () => clearTimeout(debounceTimer)
  }, [query, performSearch])

  const sortedResults = useMemo(() => {
    const sorted = [...results]
    switch (sortBy) {
      case 'price':
        return sorted.sort((a, b) => a.price - b.price)
      case 'rating':
        return sorted.sort((a, b) => b.rating.rate - a.rating.rate)
      default:
        return sorted
    }
  }, [results, sortBy])

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold mb-6">Search Products</h2>

      {/* Search Input */}
      <div className="relative mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for products..."
          className="w-full px-4 py-3 pl-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        />
        <span className="absolute left-4 top-3.5 text-gray-400">🔍</span>
        
        {query && (
          <button
            onClick={() => setQuery('')}
            className="absolute right-4 top-3.5 text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        )}
      </div>

      {/* Search History */}
      {searchHistory.length > 0 && !query && (
        <div className="mb-6">
          <p className="text-sm text-gray-500 mb-2">Recent searches:</p>
          <div className="flex flex-wrap gap-2">
            {searchHistory.map((term, idx) => (
              <button
                key={idx}
                onClick={() => setQuery(term)}
                className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm hover:bg-gray-200 transition"
              >
                {term}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Sort Options */}
      {results.length > 0 && (
        <div className="flex items-center gap-4 mb-6">
          <span className="text-sm text-gray-600">Sort by:</span>
          {(['relevance', 'price', 'rating'] as const).map(option => (
            <button
              key={option}
              onClick={() => setSortBy(option)}
              className={`px-3 py-1 rounded text-sm capitalize ${
                sortBy === option
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {option}
            </button>
          ))}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      )}

      {/* Results */}
      {!loading && sortedResults.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-gray-500">{sortedResults.length} results found</p>
          
          {sortedResults.map(product => (
            <div
              key={product.id}
              className="flex gap-4 p-4 border border-gray-200 rounded-lg hover:shadow-md transition"
            >
              <img
                src={product.image}
                alt={product.title}
                className="w-20 h-20 object-contain"
              />
              <div className="flex-1">
                <h3 className="font-semibold text-gray-800 mb-1">{product.title}</h3>
                <p className="text-sm text-gray-600 line-clamp-2 mb-2">{product.description}</p>
                <div className="flex items-center gap-4">
                  <span className="text-lg font-bold text-green-600">
                    ${product.price.toFixed(2)}
                  </span>
                  <span className="text-sm text-gray-500">
                    ★ {product.rating.rate.toFixed(1)} ({product.rating.count} reviews)
                  </span>
                </div>
              </div>
              <button className="self-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition">
                View
              </button>
            </div>
          ))}
        </div>
      )}

      {/* No Results */}
      {!loading && query && results.length === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-500">No results found for &quot;{query}&quot;</p>
        </div>
      )}
    </div>
  )
}
