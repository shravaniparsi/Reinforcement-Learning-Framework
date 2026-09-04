export interface Product {
  id: number
  title: string
  price: number
  description: string
  category: string
  image: string
  rating: {
    rate: number
    count: number
  }
}

export interface User {
  id: number
  email: string
  username: string
  name: {
    firstname: string
    lastname: string
  }
  address: {
    city: string
    street: string
    number: number
    zipcode: string
    geolocation: {
      lat: string
      long: string
    }
  }
  phone: string
}

export interface CartItem {
  id: number
  userId: number
  date: string
  products: {
    productId: number
    quantity: number
  }[]
}

export interface Comment {
  id: number
  postId: number
  user: string
  body: string
}

export interface Todo {
  id: number
  todo: string
  completed: boolean
  userId: number
}

export interface Post {
  id: number
  title: string
  body: string
  userId: number
  tags: string[]
  reactions: number
}

export interface Notification {
  id: string
  type: 'info' | 'warning' | 'success' | 'error'
  title: string
  message: string
  timestamp: Date
}

export type RenderingStrategy = 
  | 'CSR'      // Client-Side Rendering
  | 'SSR'      // Server-Side Rendering
  | 'SSG'      // Static Site Generation
  | 'ISR'      // Incremental Static Regeneration
  | 'STREAM'   // Streaming SSR
  | 'PARTIAL'  // Partial Hydration

export interface ComponentConfig {
  id: string
  name: string
  strategy: RenderingStrategy
  complexity: number      // 1-10
  updateFrequency: number // updates per minute
  dataDependency: number  // 0-1
  interactivity: number   // 0-1
}

export interface SystemState {
  networkLatencyMs: number
  networkBandwidthMbps: number
  serverCpuPercent: number
  serverMemoryPercent: number
  requestRatePerMin: number
  componentComplexity: number
  componentUpdateFreq: number
  componentDataDependency: number
  componentInteractivity: number
  clientCpuCores: number
  clientMemoryGb: number
  cacheHitRatio: number
  lastRenderLatencyMs: number
  lastRenderSuccess: boolean
  timeOfDayHour: number
}

export interface RenderMetrics {
  ttfbMs: number
  ttiMs: number
  fcpMs: number
  lcpMs: number
  totalRenderTimeMs: number
  serverCpuSeconds: number
  serverMemoryMb: number
  bandwidthBytes: number
  cacheHitRate: number
  errorRate: number
}

export interface ExperimentResult {
  runId: string
  strategy: string
  condition: string
  metrics: RenderMetrics
  timestamp: Date
  duration: number
}
