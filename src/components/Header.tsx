'use client'

import { useState, useEffect } from 'react'

interface HeaderProps {
  renderStrategy?: string
  onRenderComplete?: (metrics: { renderTime: number; strategy: string }) => void
}

export default function Header({ renderStrategy = 'CSR', onRenderComplete }: HeaderProps) {
  const [currentTime, setCurrentTime] = useState(new Date())
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    const startTime = performance.now()
    
    // Simulate minimal render work
    requestAnimationFrame(() => {
      const renderTime = performance.now() - startTime
      onRenderComplete?.({ renderTime, strategy: renderStrategy })
    })

    return () => clearInterval(timer)
  }, [renderStrategy, onRenderComplete])

  return (
    <header className="bg-gray-900 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-bold">RL-Store</h1>
            <span className="text-xs bg-blue-600 px-2 py-1 rounded">
              {renderStrategy}
            </span>
          </div>
          
          <nav className="hidden md:flex space-x-6">
            <a href="#" className="hover:text-blue-400 transition">Home</a>
            <a href="#" className="hover:text-blue-400 transition">Products</a>
            <a href="#" className="hover:text-blue-400 transition">Categories</a>
            <a href="#" className="hover:text-blue-400 transition">Deals</a>
          </nav>

          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-400">
              {currentTime.toLocaleTimeString()}
            </span>
            <button 
              className="md:hidden"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              ☰
            </button>
          </div>
        </div>

        {isMenuOpen && (
          <nav className="md:hidden mt-4 pb-4 border-t border-gray-700 pt-4">
            <div className="flex flex-col space-y-2">
              <a href="#" className="hover:text-blue-400">Home</a>
              <a href="#" className="hover:text-blue-400">Products</a>
              <a href="#" className="hover:text-blue-400">Categories</a>
            </div>
          </nav>
        )}
      </div>
    </header>
  )
}
