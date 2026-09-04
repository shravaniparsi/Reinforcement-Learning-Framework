'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { Product, CartItem } from '@/types'
import { fetchProducts, fetchCart } from '@/api/dummyData'

interface ShoppingCartProps {
  userId?: number
  renderStrategy?: string
  onRenderComplete?: (metrics: { renderTime: number; strategy: string }) => void
}

interface CartProduct extends Product {
  quantity: number
}

export default function ShoppingCart({ 
  userId = 1, 
  renderStrategy = 'CSR', 
  onRenderComplete 
}: ShoppingCartProps) {
  const [cartProducts, setCartProducts] = useState<CartProduct[]>([])
  const [loading, setLoading] = useState(true)
  const [promoCode, setPromoCode] = useState('')
  const [promoApplied, setPromoApplied] = useState(false)
  const [isCheckingOut, setIsCheckingOut] = useState(false)

  const loadCart = useCallback(async () => {
    const startTime = performance.now()
    setLoading(true)

    try {
      const [cart, products] = await Promise.all([
        fetchCart(userId),
        fetchProducts(20),
      ])

      // Merge cart items with product data
      const cartItems = cart[0]?.products || []
      const merged: CartProduct[] = cartItems
        .map(item => {
          const product = products.find(p => p.id === item.productId)
          return product ? { ...product, quantity: item.quantity } : null
        })
        .filter(Boolean) as CartProduct[]

      // Add some demo items if cart is empty
      if (merged.length === 0) {
        merged.push(
          { ...products[0], quantity: 2 },
          { ...products[1], quantity: 1 },
          { ...products[2], quantity: 3 }
        )
      }

      setCartProducts(merged)

      const renderTime = performance.now() - startTime
      onRenderComplete?.({ renderTime, strategy: renderStrategy })
    } catch (err) {
      console.error('Failed to load cart:', err)
    } finally {
      setLoading(false)
    }
  }, [userId, renderStrategy, onRenderComplete])

  useEffect(() => {
    loadCart()
  }, [loadCart])

  const updateQuantity = (productId: number, delta: number) => {
    setCartProducts(prev =>
      prev.map(item => {
        if (item.id === productId) {
          const newQty = Math.max(1, item.quantity + delta)
          return { ...item, quantity: newQty }
        }
        return item
      })
    )
  }

  const removeItem = (productId: number) => {
    setCartProducts(prev => prev.filter(item => item.id !== productId))
  }

  const subtotal = useMemo(
    () => cartProducts.reduce((sum, item) => sum + item.price * item.quantity, 0),
    [cartProducts]
  )

  const discount = promoApplied ? subtotal * 0.1 : 0
  const shipping = subtotal > 100 ? 0 : 9.99
  const tax = (subtotal - discount) * 0.08
  const total = subtotal - discount + shipping + tax

  const handleCheckout = async () => {
    setIsCheckingOut(true)
    // Simulate checkout process
    await new Promise(resolve => setTimeout(resolve, 2000))
    setIsCheckingOut(false)
    alert('Order placed successfully!')
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="flex gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="w-20 h-20 bg-gray-200 rounded"></div>
                <div className="flex-1">
                  <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/4"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold mb-6">Shopping Cart ({cartProducts.length})</h2>

      {cartProducts.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-500 mb-4">Your cart is empty</p>
          <button className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition">
            Continue Shopping
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Cart Items */}
          <div className="lg:col-span-2 space-y-4">
            {cartProducts.map(item => (
              <div
                key={item.id}
                className="flex gap-4 p-4 border border-gray-200 rounded-lg"
              >
                <img
                  src={item.image}
                  alt={item.title}
                  className="w-24 h-24 object-contain"
                />
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-800 mb-1">{item.title}</h3>
                  <p className="text-sm text-gray-500 mb-2">{item.category}</p>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center border border-gray-300 rounded">
                      <button
                        onClick={() => updateQuantity(item.id, -1)}
                        className="px-3 py-1 hover:bg-gray-100 transition"
                      >
                        -
                      </button>
                      <span className="px-4 py-1 border-x border-gray-300">
                        {item.quantity}
                      </span>
                      <button
                        onClick={() => updateQuantity(item.id, 1)}
                        className="px-3 py-1 hover:bg-gray-100 transition"
                      >
                        +
                      </button>
                    </div>
                    <button
                      onClick={() => removeItem(item.id)}
                      className="text-red-500 hover:text-red-700 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-green-600">
                    ${(item.price * item.quantity).toFixed(2)}
                  </p>
                  <p className="text-sm text-gray-500">
                    ${item.price.toFixed(2)} each
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Order Summary */}
          <div className="bg-gray-50 rounded-lg p-6 h-fit">
            <h3 className="text-lg font-semibold mb-4">Order Summary</h3>
            
            <div className="space-y-3 mb-6">
              <div className="flex justify-between">
                <span className="text-gray-600">Subtotal</span>
                <span className="font-semibold">${subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Shipping</span>
                <span className="font-semibold">
                  {shipping === 0 ? 'FREE' : `$${shipping.toFixed(2)}`}
                </span>
              </div>
              {promoApplied && (
                <div className="flex justify-between text-green-600">
                  <span>Discount (10%)</span>
                  <span>-${discount.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-600">Tax (8%)</span>
                <span className="font-semibold">${tax.toFixed(2)}</span>
              </div>
              <div className="border-t border-gray-300 pt-3 flex justify-between">
                <span className="text-lg font-bold">Total</span>
                <span className="text-lg font-bold">${total.toFixed(2)}</span>
              </div>
            </div>

            {/* Promo Code */}
            <div className="mb-6">
              <label className="block text-sm text-gray-600 mb-2">Promo Code</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={promoCode}
                  onChange={(e) => setPromoCode(e.target.value)}
                  placeholder="Enter code"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                  disabled={promoApplied}
                />
                <button
                  onClick={() => {
                    if (promoCode.toUpperCase() === 'SAVE10') {
                      setPromoApplied(true)
                    }
                  }}
                  disabled={promoApplied || !promoCode}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition disabled:opacity-50"
                >
                  Apply
                </button>
              </div>
            </div>

            {/* Checkout Button */}
            <button
              onClick={handleCheckout}
              disabled={isCheckingOut}
              className="w-full bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isCheckingOut ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Processing...
                </>
              ) : (
                'Proceed to Checkout'
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
