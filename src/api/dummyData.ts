import { Product, User, CartItem, Comment, Todo, Post, Notification } from '@/types'

// Free APIs (No Auth Required)
const FAKESTORE_BASE = 'https://fakestoreapi.com'
const DUMMYJSON_BASE = 'https://dummyjson.com'
const DOG_API = 'https://dog.ceo/api'
const CAT_API = 'https://api.thecatapi.com/v1'
const MEAL_API = 'https://www.themealdb.com/api/json/v1/1'
const CURRENCY_API = 'https://api.frankfurter.app'
const JOKE_API = 'https://v2.jokeapi.dev'
const QUOTE_API = 'https://zenquotes.io/api'
const POKE_API = 'https://pokeapi.co/api/v2'
const BREWERY_API = 'https://api.openbrewerydb.org/v1'

// Simulate network delay
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

// Products
export async function fetchProducts(limit: number = 20): Promise<Product[]> {
  const start = Date.now()
  try {
    const res = await fetch(`${FAKESTORE_BASE}/products?limit=${limit}`)
    const data = await res.json()
    const elapsed = Date.now() - start
    console.log(`[API] fetchProducts: ${elapsed}ms`)
    return data
  } catch {
    return generateMockProducts(limit)
  }
}

export async function fetchProductById(id: number): Promise<Product | null> {
  try {
    const res = await fetch(`${FAKESTORE_BASE}/products/${id}`)
    if (!res.ok) return null
    return await res.json()
  } catch {
    return generateMockProduct(id)
  }
}

export async function fetchProductsByCategory(category: string): Promise<Product[]> {
  try {
    const res = await fetch(`${FAKESTORE_BASE}/products/category/${category}`)
    return await res.json()
  } catch {
    return generateMockProducts(10)
  }
}

export async function fetchCategories(): Promise<string[]> {
  try {
    const res = await fetch(`${FAKESTORE_BASE}/products/categories`)
    return await res.json()
  } catch {
    return ['electronics', 'jewelery', "men's clothing", "women's clothing"]
  }
}

// Users
export async function fetchUsers(limit: number = 10): Promise<User[]> {
  try {
    const res = await fetch(`${DUMMYJSON_BASE}/users?limit=${limit}`)
    const data = await res.json()
    return data.users
  } catch {
    return generateMockUsers(limit)
  }
}

export async function fetchUserById(id: number): Promise<User | null> {
  try {
    const res = await fetch(`${DUMMYJSON_BASE}/users/${id}`)
    if (!res.ok) return null
    return await res.json()
  } catch {
    return generateMockUser(id)
  }
}

// Cart
export async function fetchCart(userId: number): Promise<CartItem[]> {
  try {
    const res = await fetch(`${DUMMYJSON_BASE}/carts/user/${userId}`)
    const data = await res.json()
    return data.carts
  } catch {
    return generateMockCart(userId)
  }
}

// Comments (simulated)
export async function fetchComments(postId: number, limit: number = 20): Promise<Comment[]> {
  try {
    const res = await fetch(`${DUMMYJSON_BASE}/comments/post/${postId}?limit=${limit}`)
    const data = await res.json()
    return data.comments
  } catch {
    return generateMockComments(postId, limit)
  }
}

// Todos
export async function fetchTodos(limit: number = 30): Promise<Todo[]> {
  try {
    const res = await fetch(`${DUMMYJSON_BASE}/todos?limit=${limit}`)
    const data = await res.json()
    return data.todos
  } catch {
    return generateMockTodos(limit)
  }
}

// Posts
export async function fetchPosts(limit: number = 20): Promise<Post[]> {
  try {
    const res = await fetch(`${DUMMYJSON_BASE}/posts?limit=${limit}`)
    const data = await res.json()
    return data.posts
  } catch {
    return generateMockPosts(limit)
  }
}

export async function fetchPostById(id: number): Promise<Post | null> {
  try {
    const res = await fetch(`${DUMMYJSON_BASE}/posts/${id}`)
    if (!res.ok) return null
    return await res.json()
  } catch {
    return generateMockPost(id)
  }
}

// Notifications (simulated)
export async function fetchNotifications(limit: number = 10): Promise<Notification[]> {
  await delay(100) // Simulate SSE connection time
  return generateMockNotifications(limit)
}

// Analytics (simulated - compute-heavy)
export async function fetchAnalytics(): Promise<{
  totalViews: number
  uniqueVisitors: number
  avgSessionDuration: number
  bounceRate: number
  topPages: { page: string; views: number }[]
  dailyStats: { date: string; views: number; conversions: number }[]
}> {
  // Simulate compute-heavy operation
  await delay(200)
  const dailyStats = Array.from({ length: 30 }, (_, i) => ({
    date: new Date(Date.now() - (29 - i) * 86400000).toISOString().split('T')[0],
    views: Math.floor(Math.random() * 10000) + 5000,
    conversions: Math.floor(Math.random() * 500) + 100,
  }))

  return {
    totalViews: 2847593,
    uniqueVisitors: 892341,
    avgSessionDuration: 245,
    bounceRate: 0.342,
    topPages: [
      { page: '/products', views: 456789 },
      { page: '/checkout', views: 234567 },
      { page: '/account', views: 189432 },
      { page: '/home', views: 567890 },
    ],
    dailyStats,
  }
}

// Recommendations (simulated - ML-heavy)
export async function fetchRecommendations(
  userId: number,
  limit: number = 6
): Promise<Product[]> {
  // Simulate ML inference time
  await delay(150 + Math.random() * 100)
  const products = await fetchProducts(limit)
  return products.slice(0, limit)
}

// Search
export async function searchProducts(
  query: string,
  limit: number = 10
): Promise<Product[]> {
  try {
    const res = await fetch(`${DUMMYJSON_BASE}/products/search?q=${query}&limit=${limit}`)
    const data = await res.json()
    return data.products
  } catch {
    return generateMockProducts(limit)
  }
}

// Mock data generators (fallback when APIs are down)
function generateMockProducts(n: number): Product[] {
  const categories = ['electronics', 'jewelery', "men's clothing", "women's clothing"]
  return Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    title: `Product ${i + 1}`,
    price: Math.floor(Math.random() * 200) + 10,
    description: `This is a detailed description of product ${i + 1}. It includes all the features and specifications.`,
    category: categories[Math.floor(Math.random() * categories.length)],
    image: `https://fakestoreapi.com/img/81fPKd-2AYL._AC_SL1500_.jpg`,
    rating: {
      rate: Math.random() * 2 + 3,
      count: Math.floor(Math.random() * 500),
    },
  }))
}

function generateMockProduct(id: number): Product {
  return {
    id,
    title: `Product ${id}`,
    price: 29.99,
    description: `Detailed description for product ${id}`,
    category: 'electronics',
    image: 'https://fakestoreapi.com/img/81fPKd-2AYL._AC_SL1500_.jpg',
    rating: { rate: 4.5, count: 120 },
  }
}

function generateMockUsers(n: number): User[] {
  return Array.from({ length: n }, (_, i) => generateMockUser(i + 1))
}

function generateMockUser(id: number): User {
  return {
    id,
    email: `user${id}@example.com`,
    username: `user${id}`,
    name: { firstname: 'John', lastname: `Doe${id}` },
    address: {
      city: 'New York',
      street: 'Main St',
      number: 123,
      zipcode: '10001',
      geolocation: { lat: '40.7128', long: '-74.0060' },
    },
    phone: '1-570-236-5467',
  }
}

function generateMockCart(userId: number): CartItem[] {
  return [
    {
      id: 1,
      userId,
      date: new Date().toISOString(),
      products: [
        { productId: 1, quantity: 2 },
        { productId: 3, quantity: 1 },
      ],
    },
  ]
}

function generateMockComments(postId: number, n: number): Comment[] {
  return Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    postId,
    user: `user${i + 1}`,
    body: `This is comment ${i + 1} on post ${postId}. It contains some thoughts about the content.`,
  }))
}

function generateMockTodos(n: number): Todo[] {
  return Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    todo: `Task ${i + 1}: Complete this task`,
    completed: Math.random() > 0.5,
    userId: 1,
  }))
}

function generateMockPosts(n: number): Post[] {
  return Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    title: `Post ${i + 1}`,
    body: `This is the body content of post ${i + 1}. It contains detailed information.`,
    userId: Math.floor(Math.random() * 10) + 1,
    tags: ['technology', 'web', 'react'],
    reactions: Math.floor(Math.random() * 100),
  }))
}

function generateMockPost(id: number): Post {
  return {
    id,
    title: `Post ${id}`,
    body: `Body of post ${id}`,
    userId: 1,
    tags: ['tech'],
    reactions: 42,
  }
}

function generateMockNotifications(n: number): Notification[] {
  const types: Array<'info' | 'warning' | 'success' | 'error'> = [
    'info', 'warning', 'success', 'error',
  ]
  return Array.from({ length: n }, (_, i) => ({
    id: `notif-${i + 1}`,
    type: types[Math.floor(Math.random() * types.length)],
    title: `Notification ${i + 1}`,
    message: `This is notification message ${i + 1}`,
    timestamp: new Date(Date.now() - i * 60000),
  }))
}

// ============================================================
// FREE PUBLIC APIs (No Auth Required)
// ============================================================

// Dog API - Random dog images
export interface DogImage {
  message: string
  status: string
}

export async function fetchRandomDog(): Promise<DogImage> {
  try {
    const res = await fetch(`${DOG_API}/breeds/image/random`)
    return await res.json()
  } catch {
    return { message: 'https://images.dog.ceo/breeds/hound-afghan/n02088074_1003.jpg', status: 'success' }
  }
}

export async function fetchDogBreeds(): Promise<string[]> {
  try {
    const res = await fetch(`${DOG_API}/breeds/list/all`)
    const data = await res.json()
    return Object.keys(data.message).slice(0, 20)
  } catch {
    return ['akita', 'beagle', 'bulldog', 'chihuahua', 'dalmatian']
  }
}

// Cat API - Random cat images
export interface CatImage {
  id: string
  url: string
  width: number
  height: number
}

export async function fetchRandomCat(): Promise<CatImage> {
  try {
    const res = await fetch(`${CAT_API}/images/search`)
    const data = await res.json()
    return data[0]
  } catch {
    return { id: 'demo', url: 'https://cdn2.thecatapi.com/images/MTk4MjA0MA.jpg', width: 1024, height: 768 }
  }
}

// TheMealDB - Random meals
export interface Meal {
  idMeal: string
  strMeal: string
  strCategory: string
  strArea: string
  strInstructions: string
  strMealThumb: string
  strIngredient1: string
  strIngredient2: string
  strIngredient3: string
}

export async function fetchRandomMeal(): Promise<Meal | null> {
  try {
    const res = await fetch(`${MEAL_API}/random.php`)
    const data = await res.json()
    return data.meals?.[0] || null
  } catch {
    return null
  }
}

export async function fetchMealsByCategory(category: string): Promise<Meal[]> {
  try {
    const res = await fetch(`${MEAL_API}/filter.php?c=${category}`)
    const data = await res.json()
    return data.meals || []
  } catch {
    return []
  }
}

export async function fetchMealCategories(): Promise<string[]> {
  try {
    const res = await fetch(`${MEAL_API}/categories.php`)
    const data = await res.json()
    return data.categories?.map((c: { strCategory: string }) => c.strCategory) || []
  } catch {
    return ['Beef', 'Chicken', 'Dessert', 'Pasta', 'Seafood']
  }
}

// Frankfurter - Currency Exchange Rates
export interface CurrencyRates {
  base: string
  date: string
  rates: Record<string, number>
}

export async function fetchCurrencyRates(base: string = 'USD'): Promise<CurrencyRates> {
  try {
    const res = await fetch(`${CURRENCY_API}/latest?from=${base}`)
    return await res.json()
  } catch {
    return { base: 'USD', date: new Date().toISOString().split('T')[0], rates: { EUR: 0.85, GBP: 0.73, JPY: 110.25 } }
  }
}

export async function convertCurrency(from: string, to: string, amount: number): Promise<number> {
  try {
    const res = await fetch(`${CURRENCY_API}/latest?from=${from}&to=${to}&amount=${amount}`)
    const data = await res.json()
    return data.rates[to] || amount
  } catch {
    return amount
  }
}

// Joke API - Random jokes
export interface Joke {
  id: number
  type: string
  setup: string
  delivery: string
  category: string
}

export async function fetchRandomJoke(): Promise<Joke | null> {
  try {
    const res = await fetch(`${JOKE_API}/any?type=single,twopart`)
    const data = await res.json()
    return data
  } catch {
    return { id: 1, type: 'twopart', setup: 'Why do programmers prefer dark mode?', delivery: 'Because light attracts bugs!', category: 'Programming' }
  }
}

// PokeAPI - Pokemon data
export interface Pokemon {
  id: number
  name: string
  height: number
  weight: number
  sprites: { front_default: string }
  types: { type: { name: string } }[]
}

export async function fetchRandomPokemon(): Promise<Pokemon | null> {
  try {
    const id = Math.floor(Math.random() * 151) + 1
    const res = await fetch(`${POKE_API}/pokemon/${id}`)
    return await res.json()
  } catch {
    return null
  }
}

export async function fetchPokemonList(limit: number = 20): Promise<{ name: string; url: string }[]> {
  try {
    const res = await fetch(`${POKE_API}/pokemon?limit=${limit}`)
    const data = await res.json()
    return data.results
  } catch {
    return []
  }
}

// Open Brewery DB - Breweries
export interface Brewery {
  id: string
  name: string
  brewery_type: string
  city: string
  state: string
  country: string
  website_url: string
}

export async function fetchBreweries(city: string = 'san_diego'): Promise<Brewery[]> {
  try {
    const res = await fetch(`${BREWERY_API}/breweries?by_city=${city}&per_page=10`)
    return await res.json()
  } catch {
    return []
  }
}

// Combined data fetcher for heavy components
export async function fetchCombinedDashboardData(): Promise<{
  products: Product[]
  meals: Meal[]
  currencies: CurrencyRates
  pokemon: Pokemon[]
  timestamp: number
}> {
  const startTime = Date.now()
  
  const [products, meal, currencies, pokemon1, pokemon2, pokemon3] = await Promise.all([
    fetchProducts(5),
    fetchRandomMeal(),
    fetchCurrencyRates('USD'),
    fetchRandomPokemon(),
    fetchRandomPokemon(),
    fetchRandomPokemon(),
  ])
  
  console.log(`[API] fetchCombinedDashboardData: ${Date.now() - startTime}ms`)
  
  return {
    products,
    meals: meal ? [meal] : [],
    currencies,
    pokemon: [pokemon1, pokemon2, pokemon3].filter(Boolean) as Pokemon[],
    timestamp: Date.now(),
  }
}
