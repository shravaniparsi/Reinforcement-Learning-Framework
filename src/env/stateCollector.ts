import { SystemState, ComponentConfig, RenderingStrategy } from '@/types'

export interface NetworkConditions {
  latencyMs: number
  bandwidthMbps: number
  packetLoss: number
}

export interface ServerConditions {
  cpuPercent: number
  memoryPercent: number
  requestRate: number
  activeConnections: number
}

export interface ClientConditions {
  cpuCores: number
  memoryGb: number
  deviceType: 'desktop' | 'mobile' | 'tablet'
  browserEngine: string
}

export interface DeviceProfile {
  name: string
  cpuCores: number
  memoryGb: number
  deviceType: 'desktop' | 'mobile' | 'tablet'
  browserEngine: string
}

// Predefined device profiles
export const DEVICE_PROFILES: Record<string, DeviceProfile> = {
  highEnd: {
    name: 'High-end Desktop',
    cpuCores: 8,
    memoryGb: 16,
    deviceType: 'desktop',
    browserEngine: 'V8',
  },
  midRange: {
    name: 'Mid-range Laptop',
    cpuCores: 4,
    memoryGb: 8,
    deviceType: 'desktop',
    browserEngine: 'V8',
  },
  lowEnd: {
    name: 'Budget Mobile',
    cpuCores: 2,
    memoryGb: 3,
    deviceType: 'mobile',
    browserEngine: 'JavaScriptCore',
  },
  iot: {
    name: 'Smart TV',
    cpuCores: 2,
    memoryGb: 2,
    deviceType: 'tablet',
    browserEngine: 'V8',
  },
}

// Network condition presets
export const NETWORK_PRESETS: Record<string, NetworkConditions> = {
  excellent: { latencyMs: 5, bandwidthMbps: 100, packetLoss: 0 },
  good: { latencyMs: 20, bandwidthMbps: 50, packetLoss: 0.01 },
  moderate: { latencyMs: 50, bandwidthMbps: 20, packetLoss: 0.02 },
  poor: { latencyMs: 150, bandwidthMbps: 5, packetLoss: 0.05 },
  terrible: { latencyMs: 300, bandwidthMbps: 1, packetLoss: 0.1 },
}

// Server load presets
export const SERVER_PRESETS: Record<string, ServerConditions> = {
  idle: { cpuPercent: 10, memoryPercent: 30, requestRate: 50, activeConnections: 10 },
  normal: { cpuPercent: 40, memoryPercent: 50, requestRate: 200, activeConnections: 50 },
  high: { cpuPercent: 75, memoryPercent: 70, requestRate: 500, activeConnections: 150 },
  overload: { cpuPercent: 95, memoryPercent: 90, requestRate: 1000, activeConnections: 500 },
}

// Component configurations with varying characteristics
export const COMPONENT_CONFIGS: ComponentConfig[] = [
  {
    id: 'header',
    name: 'Header',
    strategy: 'SSG',
    complexity: 2,
    updateFrequency: 0.1,
    dataDependency: 0.1,
    interactivity: 0.3,
  },
  {
    id: 'product-grid',
    name: 'Product Grid',
    strategy: 'SSR',
    complexity: 6,
    updateFrequency: 2,
    dataDependency: 0.8,
    interactivity: 0.5,
  },
  {
    id: 'dashboard',
    name: 'User Dashboard',
    strategy: 'CSR',
    complexity: 8,
    updateFrequency: 5,
    dataDependency: 0.9,
    interactivity: 0.9,
  },
  {
    id: 'search',
    name: 'Search Results',
    strategy: 'SSR',
    complexity: 5,
    updateFrequency: 8,
    dataDependency: 0.7,
    interactivity: 0.7,
  },
  {
    id: 'recommendations',
    name: 'Recommendations',
    strategy: 'CSR',
    complexity: 7,
    updateFrequency: 1,
    dataDependency: 0.6,
    interactivity: 0.4,
  },
  {
    id: 'comments',
    name: 'Comments',
    strategy: 'CSR',
    complexity: 4,
    updateFrequency: 10,
    dataDependency: 0.5,
    interactivity: 0.8,
  },
  {
    id: 'notifications',
    name: 'Notifications',
    strategy: 'STREAM',
    complexity: 3,
    updateFrequency: 15,
    dataDependency: 0.4,
    interactivity: 0.6,
  },
  {
    id: 'cart',
    name: 'Shopping Cart',
    strategy: 'CSR',
    complexity: 5,
    updateFrequency: 3,
    dataDependency: 0.7,
    interactivity: 0.9,
  },
  {
    id: 'analytics',
    name: 'Analytics Widget',
    strategy: 'CSR',
    complexity: 9,
    updateFrequency: 0.5,
    dataDependency: 0.9,
    interactivity: 0.5,
  },
  {
    id: 'footer',
    name: 'Footer',
    strategy: 'SSG',
    complexity: 1,
    updateFrequency: 0,
    dataDependency: 0,
    interactivity: 0.1,
  },
]

// State collector class
export class StateCollector {
  private networkConditions: NetworkConditions
  private serverConditions: ServerConditions
  private clientConditions: ClientConditions
  private cacheState: Map<string, { data: unknown; timestamp: number }> = new Map()
  private renderHistory: { strategy: RenderingStrategy; latencyMs: number; success: boolean }[] = []
  private currentHour: number

  constructor(
    networkPreset: keyof typeof NETWORK_PRESETS = 'good',
    serverPreset: keyof typeof SERVER_PRESETS = 'normal',
    deviceProfile: keyof typeof DEVICE_PROFILES = 'midRange'
  ) {
    this.networkConditions = { ...NETWORK_PRESETS[networkPreset] }
    this.serverConditions = { ...SERVER_PRESETS[serverPreset] }
    this.clientConditions = { ...DEVICE_PROFILES[deviceProfile] }
    this.currentHour = new Date().getHours()
  }

  // Update conditions (simulates real-time changes)
  updateConditions(
    networkPreset?: keyof typeof NETWORK_PRESETS,
    serverPreset?: keyof typeof SERVER_PRESETS,
    deviceProfile?: keyof typeof DEVICE_PROFILES
  ): void {
    if (networkPreset) {
      this.networkConditions = {
        ...NETWORK_PRESETS[networkPreset],
        // Add some randomness
        latencyMs: NETWORK_PRESETS[networkPreset].latencyMs * (0.9 + Math.random() * 0.2),
        bandwidthMbps: NETWORK_PRESETS[networkPreset].bandwidthMbps * (0.8 + Math.random() * 0.4),
      }
    }

    if (serverPreset) {
      this.serverConditions = {
        ...SERVER_PRESETS[serverPreset],
        // Add some randomness
        cpuPercent: Math.min(100, SERVER_PRESETS[serverPreset].cpuPercent * (0.8 + Math.random() * 0.4)),
        memoryPercent: Math.min(100, SERVER_PRESETS[serverPreset].memoryPercent * (0.9 + Math.random() * 0.2)),
      }
    }

    if (deviceProfile) {
      this.clientConditions = { ...DEVICE_PROFILES[deviceProfile] }
    }

    this.currentHour = new Date().getHours()
  }

  // Collect current system state
  collectState(component: ComponentConfig): SystemState {
    const cacheKey = `${component.id}_${this.currentHour}`
    const cached = this.cacheState.get(cacheKey)
    const cacheHitRatio = cached ? 0.9 : 0.1

    // Get last render metrics
    const lastRender = this.renderHistory[this.renderHistory.length - 1]
    const lastRenderLatencyMs = lastRender ? lastRender.latencyMs : 100
    const lastRenderSuccess = lastRender ? lastRender.success : true

    return {
      networkLatencyMs: this.networkConditions.latencyMs,
      networkBandwidthMbps: this.networkConditions.bandwidthMbps,
      serverCpuPercent: this.serverConditions.cpuPercent,
      serverMemoryPercent: this.serverConditions.memoryPercent,
      requestRatePerMin: this.serverConditions.requestRate,
      componentComplexity: component.complexity,
      componentUpdateFreq: component.updateFrequency,
      componentDataDependency: component.dataDependency,
      componentInteractivity: component.interactivity,
      clientCpuCores: this.clientConditions.cpuCores,
      clientMemoryGb: this.clientConditions.memoryGb,
      cacheHitRatio,
      lastRenderLatencyMs,
      lastRenderSuccess,
      timeOfDayHour: this.currentHour,
    }
  }

  // Record render result
  recordRender(strategy: RenderingStrategy, latencyMs: number, success: boolean): void {
    this.renderHistory.push({ strategy, latencyMs, success })
    // Keep only last 100 records
    if (this.renderHistory.length > 100) {
      this.renderHistory.shift()
    }
  }

  // Update cache state
  updateCache(componentId: string, data: unknown): void {
    const cacheKey = `${componentId}_${this.currentHour}`
    this.cacheState.set(cacheKey, { data, timestamp: Date.now() })
  }

  // Get current conditions for logging
  getCurrentConditions() {
    return {
      network: { ...this.networkConditions },
      server: { ...this.serverConditions },
      client: { ...this.clientConditions },
      hour: this.currentHour,
    }
  }

  // Calculate cache hit ratio
  getCacheHitRatio(): number {
    const totalRenders = this.renderHistory.length
    if (totalRenders === 0) return 0

    const cacheHits = this.renderHistory.filter(
      (r) => r.strategy === 'SSG' || r.strategy === 'ISR'
    ).length

    return cacheHits / totalRenders
  }
}

// Factory function to create state collector with random conditions
export function createRandomStateCollector(): StateCollector {
  const networkPresets = Object.keys(NETWORK_PRESETS) as (keyof typeof NETWORK_PRESETS)[]
  const serverPresets = Object.keys(SERVER_PRESETS) as (keyof typeof SERVER_PRESETS)[]
  const deviceProfiles = Object.keys(DEVICE_PROFILES) as (keyof typeof DEVICE_PROFILES)[]

  return new StateCollector(
    networkPresets[Math.floor(Math.random() * networkPresets.length)],
    serverPresets[Math.floor(Math.random() * serverPresets.length)],
    deviceProfiles[Math.floor(Math.random() * deviceProfiles.length)]
  )
}
