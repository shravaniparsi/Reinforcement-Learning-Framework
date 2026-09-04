import { RenderingStrategy, RenderMetrics, ComponentConfig } from '@/types'

export interface RenderingContext {
  component: ComponentConfig
  networkLatencyMs: number
  networkBandwidthMbps: number
  serverCpuPercent: number
  serverMemoryPercent: number
  clientCpuCores: number
  clientMemoryGb: number
  cacheHitRatio: number
}

export interface RenderingResult {
  strategy: RenderingStrategy
  metrics: RenderMetrics
  html: string
  hydrated: boolean
  cached: boolean
}

// Simulate rendering delay based on strategy and conditions
function simulateRenderDelay(
  strategy: RenderingStrategy,
  complexity: number,
  conditions: Partial<RenderingContext>
): number {
  const baseDelay = complexity * 10 // Base delay per complexity unit

  switch (strategy) {
    case 'CSR':
      // CSR: Minimal server delay, but client must process
      return baseDelay * 0.3 + (conditions.networkLatencyMs || 0) * 0.1

    case 'SSR':
      // SSR: Full server render, network dependent
      return baseDelay * 1.0 + (conditions.networkLatencyMs || 0) * 0.5

    case 'SSG':
      // SSG: Pre-rendered, very fast delivery
      return baseDelay * 0.1 + (conditions.networkLatencyMs || 0) * 0.2

    case 'ISR':
      // ISR: Cached but occasional revalidation
      const isRevalidating = Math.random() < 0.1 // 10% chance of revalidation
      return isRevalidating
        ? baseDelay * 0.8 + (conditions.networkLatencyMs || 0) * 0.3
        : baseDelay * 0.15 + (conditions.networkLatencyMs || 0) * 0.2

    case 'STREAM':
      // Streaming: Start fast, complete in background
      return baseDelay * 0.4 + (conditions.networkLatencyMs || 0) * 0.3

    case 'PARTIAL':
      // Partial hydration: Only hydrate interactive parts
      return baseDelay * 0.5 + (conditions.networkLatencyMs || 0) * 0.2

    default:
      return baseDelay
  }
}

// Generate mock HTML based on strategy
function generateHtml(
  strategy: RenderingStrategy,
  component: ComponentConfig
): string {
  const strategyLabel = strategy
  const componentName = component.name

  switch (strategy) {
    case 'CSR':
      return `<div id="${component.id}" class="csr-component">
        <div class="loading-skeleton">Loading ${componentName}...</div>
        <script>/* React hydration code */</script>
      </div>`

    case 'SSR':
      return `<div id="${component.id}" class="ssr-component">
        <h2>${componentName}</h2>
        <div class="server-rendered-content">
          <!-- Fully rendered HTML from server -->
        </div>
        <script>/* Minimal hydration */</script>
      </div>`

    case 'SSG':
      return `<div id="${component.id}" class="ssg-component">
        <h2>${componentName}</h2>
        <div class="static-content">
          <!-- Pre-rendered static HTML -->
        </div>
      </div>`

    case 'ISR':
      return `<div id="${component.id}" class="isr-component">
        <h2>${componentName}</h2>
        <div class="cached-content">
          <!-- Cached HTML with revalidation -->
        </div>
        <meta data-revalidate="60">
      </div>`

    case 'STREAM':
      return `<div id="${component.id}" class="stream-component">
        <div class="stream-placeholder">
          <!-- Streaming chunks -->
          <template shadowrootmode="open">
            <h2>${componentName}</h2>
            <div class="streaming-content"></div>
          </template>
        </div>
      </div>`

    case 'PARTIAL':
      return `<div id="${component.id}" class="partial-component">
        <h2>${componentName}</h2>
        <div class="static-part">
          <!-- No hydration needed -->
        </div>
        <div class="interactive-part" data-hydrate="true">
          <!-- Only this part is hydrated -->
        </div>
      </div>`

    default:
      return `<div id="${component.id}">${componentName}</div>`
  }
}

// Calculate resource usage based on strategy
function calculateResourceUsage(
  strategy: RenderingStrategy,
  complexity: number,
  context: RenderingContext
): { cpuSeconds: number; memoryMb: number; bandwidthBytes: number } {
  const baseResource = complexity * 1024 // Base bandwidth per complexity unit

  switch (strategy) {
    case 'CSR':
      return {
        cpuSeconds: 0.01, // Minimal server CPU
        memoryMb: 5,
        bandwidthBytes: baseResource * 0.3, // Smaller initial payload
      }

    case 'SSR':
      return {
        cpuSeconds: complexity * 0.05, // High server CPU
        memoryMb: complexity * 10,
        bandwidthBytes: baseResource * 1.0,
      }

    case 'SSG':
      return {
        cpuSeconds: 0.005, // Almost no server CPU at serve time
        memoryMb: 2,
        bandwidthBytes: baseResource * 0.8, // Optimized static assets
      }

    case 'ISR':
      return {
        cpuSeconds: Math.random() < 0.1 ? complexity * 0.04 : 0.005,
        memoryMb: Math.random() < 0.1 ? complexity * 8 : 3,
        bandwidthBytes: baseResource * 0.85,
      }

    case 'STREAM':
      return {
        cpuSeconds: complexity * 0.03, // Moderate server CPU
        memoryMb: complexity * 7,
        bandwidthBytes: baseResource * 0.6, // Chunked delivery
      }

    case 'PARTIAL':
      return {
        cpuSeconds: complexity * 0.02, // Lower server CPU
        memoryMb: complexity * 5,
        bandwidthBytes: baseResource * 0.5, // Only interactive parts
      }

    default:
      return { cpuSeconds: 0.01, memoryMb: 5, bandwidthBytes: baseResource }
  }
}

// Main rendering function
export async function renderComponent(
  strategy: RenderingStrategy,
  component: ComponentConfig,
  context: RenderingContext
): Promise<RenderingResult> {
  const startTime = performance.now()

  // Simulate render delay
  const delay = simulateRenderDelay(strategy, component.complexity, context)
  await new Promise(resolve => setTimeout(resolve, delay))

  // Generate HTML
  const html = generateHtml(strategy, component)

  // Calculate metrics
  const resources = calculateResourceUsage(strategy, component.complexity, context)
  const renderTime = performance.now() - startTime

  // Calculate performance metrics
  const ttfb = strategy === 'SSG' || strategy === 'ISR'
    ? renderTime * 0.3
    : renderTime * 0.5

  const fcp = ttfb + renderTime * 0.2
  const lcp = fcp + renderTime * 0.3
  const tti = strategy === 'CSR'
    ? lcp + renderTime * 0.5 // Client must execute JS
    : lcp + renderTime * 0.1

  const metrics: RenderMetrics = {
    ttfbMs: ttfb,
    fcpMs: fcp,
    lcpMs: lcp,
    ttiMs: tti,
    totalRenderTimeMs: renderTime,
    serverCpuSeconds: resources.cpuSeconds,
    serverMemoryMb: resources.memoryMb,
    bandwidthBytes: resources.bandwidthBytes,
    cacheHitRate: strategy === 'SSG' ? 1.0 :
                  strategy === 'ISR' ? (context.cacheHitRatio || 0.9) :
                  strategy === 'SSR' ? 0.1 : 0,
    errorRate: Math.random() < 0.01 ? 1 : 0, // 1% error rate
  }

  return {
    strategy,
    metrics,
    html,
    hydrated: strategy !== 'SSG',
    cached: strategy === 'SSG' || strategy === 'ISR',
  }
}

// Batch render multiple components
export async function renderComponents(
  strategy: RenderingStrategy,
  components: ComponentConfig[],
  context: Omit<RenderingContext, 'component'>
): Promise<RenderingResult[]> {
  const results: RenderingResult[] = []

  for (const component of components) {
    const result = await renderComponent(strategy, component, { ...context, component })
    results.push(result)
  }

  return results
}

// Get strategy characteristics for RL state
export function getStrategyCharacteristics(strategy: RenderingStrategy) {
  const characteristics: Record<RenderingStrategy, {
    serverCpuWeight: number
    clientCpuWeight: number
    latencyWeight: number
    bandwidthWeight: number
    cacheability: number
  }> = {
    CSR: {
      serverCpuWeight: 0.1,
      clientCpuWeight: 0.9,
      latencyWeight: 0.3,
      bandwidthWeight: 0.4,
      cacheability: 0.1,
    },
    SSR: {
      serverCpuWeight: 0.9,
      clientCpuWeight: 0.2,
      latencyWeight: 0.8,
      bandwidthWeight: 0.7,
      cacheability: 0.2,
    },
    SSG: {
      serverCpuWeight: 0.05,
      clientCpuWeight: 0.1,
      latencyWeight: 0.1,
      bandwidthWeight: 0.5,
      cacheability: 1.0,
    },
    ISR: {
      serverCpuWeight: 0.3,
      clientCpuWeight: 0.1,
      latencyWeight: 0.2,
      bandwidthWeight: 0.5,
      cacheability: 0.9,
    },
    STREAM: {
      serverCpuWeight: 0.6,
      clientCpuWeight: 0.3,
      latencyWeight: 0.4,
      bandwidthWeight: 0.4,
      cacheability: 0.3,
    },
    PARTIAL: {
      serverCpuWeight: 0.4,
      clientCpuWeight: 0.5,
      latencyWeight: 0.5,
      bandwidthWeight: 0.3,
      cacheability: 0.4,
    },
  }

  return characteristics[strategy]
}
