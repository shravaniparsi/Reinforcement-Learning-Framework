"""
RL Environment for Adaptive Component Rendering Optimization

This module implements an OpenAI Gym-compatible environment for training
reinforcement learning agents to select optimal rendering strategies.
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, Tuple, Optional, List
import json
import time

# Rendering strategies
RENDERING_STRATEGIES = ['CSR', 'SSR', 'SSG', 'ISR', 'STREAM', 'PARTIAL']
NUM_STRATEGIES = len(RENDERING_STRATEGIES)

# Device profiles
DEVICE_PROFILES = {
    'high_end': {'cpu_cores': 8, 'memory_gb': 16, 'device_type': 0},
    'mid_range': {'cpu_cores': 4, 'memory_gb': 8, 'device_type': 0},
    'low_end': {'cpu_cores': 2, 'memory_gb': 3, 'device_type': 1},
    'iot': {'cpu_cores': 2, 'memory_gb': 2, 'device_type': 2},
}

# Network presets
NETWORK_PRESETS = {
    'excellent': {'latency_ms': 5, 'bandwidth_mbps': 100},
    'good': {'latency_ms': 20, 'bandwidth_mbps': 50},
    'moderate': {'latency_ms': 50, 'bandwidth_mbps': 20},
    'poor': {'latency_ms': 150, 'bandwidth_mbps': 5},
    'terrible': {'latency_ms': 300, 'bandwidth_mbps': 1},
}

# Server presets
SERVER_PRESETS = {
    'idle': {'cpu_percent': 10, 'memory_percent': 30, 'request_rate': 50},
    'normal': {'cpu_percent': 40, 'memory_percent': 50, 'request_rate': 200},
    'high': {'cpu_percent': 75, 'memory_percent': 70, 'request_rate': 500},
    'overload': {'cpu_percent': 95, 'memory_percent': 90, 'request_rate': 1000},
}

# Component configurations
COMPONENT_CONFIGS = [
    {'id': 'header', 'complexity': 2, 'update_freq': 0.1, 'data_dep': 0.1, 'interactivity': 0.3},
    {'id': 'product_grid', 'complexity': 6, 'update_freq': 2, 'data_dep': 0.8, 'interactivity': 0.5},
    {'id': 'dashboard', 'complexity': 8, 'update_freq': 5, 'data_dep': 0.9, 'interactivity': 0.9},
    {'id': 'search', 'complexity': 5, 'update_freq': 8, 'data_dep': 0.7, 'interactivity': 0.7},
    {'id': 'recommendations', 'complexity': 7, 'update_freq': 1, 'data_dep': 0.6, 'interactivity': 0.4},
    {'id': 'comments', 'complexity': 4, 'update_freq': 10, 'data_dep': 0.5, 'interactivity': 0.8},
    {'id': 'notifications', 'complexity': 3, 'update_freq': 15, 'data_dep': 0.4, 'interactivity': 0.6},
    {'id': 'cart', 'complexity': 5, 'update_freq': 3, 'data_dep': 0.7, 'interactivity': 0.9},
    {'id': 'analytics', 'complexity': 9, 'update_freq': 0.5, 'data_dep': 0.9, 'interactivity': 0.5},
    {'id': 'footer', 'complexity': 1, 'update_freq': 0, 'data_dep': 0, 'interactivity': 0.1},
]


class RenderingEnvironment(gym.Env):
    """
    Custom Gym environment for adaptive component rendering optimization.
    
    The agent observes system state (network, server, device, component characteristics)
    and selects a rendering strategy for each component.
    """
    
    metadata = {'render_modes': ['human', 'rgb_array']}
    
    def __init__(
        self,
        max_steps: int = 1000,
        num_components: int = 10,
        randomize_conditions: bool = True,
        render_mode: Optional[str] = None
    ):
        super().__init__()
        
        self.max_steps = max_steps
        self.num_components = num_components
        self.randomize_conditions = randomize_conditions
        self.render_mode = render_mode
        
        # State space: 15-dimensional continuous
        # [network_latency, network_bw, server_cpu, server_mem, request_rate,
        #  component_complexity, component_update_freq, component_data_dep,
        #  component_interactivity, client_cpu_cores, client_memory_gb,
        #  cache_hit_ratio, last_render_latency, last_render_success, time_of_day]
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
            high=np.array([500, 200, 100, 100, 2000, 10, 20, 1, 1, 16, 32, 1, 5000, 1, 24]),
            dtype=np.float32
        )
        
        # Action space: select rendering strategy (6 options)
        self.action_space = spaces.Discrete(NUM_STRATEGIES)
        
        # Internal state
        self.current_step = 0
        self.current_component_idx = 0
        self.state = None
        self.render_history = []
        self.metrics_history = []
        
        # Condition trackers
        self.network_conditions = {'latency_ms': 20, 'bandwidth_mbps': 50}
        self.server_conditions = {'cpu_percent': 40, 'memory_percent': 50, 'request_rate': 200}
        self.client_conditions = {'cpu_cores': 4, 'memory_gb': 8, 'device_type': 0}
        self.cache_state = {}
        
    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None
    ) -> Tuple[np.ndarray, Dict]:
        """Reset the environment to initial state."""
        super().reset(seed=seed)
        
        self.current_step = 0
        self.current_component_idx = 0
        self.render_history = []
        self.metrics_history = []
        self.cache_state = {}
        
        # Randomize initial conditions if enabled
        if self.randomize_conditions:
            self._randomize_conditions()
        
        # Get initial observation
        self.state = self._get_observation()
        
        info = {
            'conditions': {
                'network': self.network_conditions.copy(),
                'server': self.server_conditions.copy(),
                'client': self.client_conditions.copy(),
            }
        }
        
        return self.state, info
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Execute one step in the environment.
        
        Args:
            action: Rendering strategy index (0-5)
            
        Returns:
            observation, reward, terminated, truncated, info
        """
        self.current_step += 1
        
        # Get current component
        component = COMPONENT_CONFIGS[self.current_component_idx % len(COMPONENT_CONFIGS)]
        
        # Calculate reward based on action and state
        reward = self._calculate_reward(action, component)
        
        # Record metrics
        metrics = self._simulate_render(action, component)
        self.metrics_history.append(metrics)
        self.render_history.append({
            'strategy': RENDERING_STRATEGIES[action],
            'component': component['id'],
            'metrics': metrics,
            'step': self.current_step,
        })
        
        # Update conditions (simulate time passing)
        if self.current_step % 10 == 0:
            self._update_conditions()
        
        # Move to next component
        self.current_component_idx += 1
        
        # Check if episode is done
        terminated = self.current_step >= self.max_steps
        truncated = False
        
        # Get new observation
        self.state = self._get_observation()
        
        info = {
            'step': self.current_step,
            'strategy': RENDERING_STRATEGIES[action],
            'component': component['id'],
            'metrics': metrics,
            'conditions': {
                'network': self.network_conditions.copy(),
                'server': self.server_conditions.copy(),
                'client': self.client_conditions.copy(),
            }
        }
        
        return self.state, reward, terminated, truncated, info
    
    def _get_observation(self) -> np.ndarray:
        """Generate current observation vector."""
        component = COMPONENT_CONFIGS[self.current_component_idx % len(COMPONENT_CONFIGS)]
        
        # Normalize values to [0, 1] range
        obs = np.array([
            self.network_conditions['latency_ms'] / 500,           # network_latency
            self.network_conditions['bandwidth_mbps'] / 200,       # network_bandwidth
            self.server_conditions['cpu_percent'] / 100,            # server_cpu
            self.server_conditions['memory_percent'] / 100,         # server_memory
            self.server_conditions['request_rate'] / 2000,          # request_rate
            component['complexity'] / 10,                           # component_complexity
            min(component['update_freq'] / 20, 1),                 # component_update_freq
            component['data_dep'],                                  # component_data_dependency
            component['interactivity'],                             # component_interactivity
            self.client_conditions['cpu_cores'] / 16,              # client_cpu
            self.client_conditions['memory_gb'] / 32,              # client_memory
            self._get_cache_hit_ratio(),                            # cache_hit_ratio
            self._get_last_render_latency() / 5000,                # last_render_latency
            1.0 if self._get_last_render_success() else 0.0,       # last_render_success
            (self.current_step % 24) / 24,                         # time_of_day
        ], dtype=np.float32)
        
        return obs
    
    def _calculate_reward(self, action: int, component: Dict) -> float:
        """
        Calculate reward based on rendering strategy and component characteristics.
        
        Multi-objective reward function:
        R = -(α*latency + β*cpu_cost + γ*bandwidth) + δ*ux_score
        """
        strategy = RENDERING_STRATEGIES[action]
        
        # Strategy characteristics
        strategy_chars = {
            'CSR': {'cpu_weight': 0.1, 'latency_weight': 0.3, 'bandwidth_weight': 0.4, 'cacheability': 0.1},
            'SSR': {'cpu_weight': 0.9, 'latency_weight': 0.8, 'bandwidth_weight': 0.7, 'cacheability': 0.2},
            'SSG': {'cpu_weight': 0.05, 'latency_weight': 0.1, 'bandwidth_weight': 0.5, 'cacheability': 1.0},
            'ISR': {'cpu_weight': 0.3, 'latency_weight': 0.2, 'bandwidth_weight': 0.5, 'cacheability': 0.9},
            'STREAM': {'cpu_weight': 0.6, 'latency_weight': 0.4, 'bandwidth_weight': 0.4, 'cacheability': 0.3},
            'PARTIAL': {'cpu_weight': 0.4, 'latency_weight': 0.5, 'bandwidth_weight': 0.3, 'cacheability': 0.4},
        }
        
        chars = strategy_chars[strategy]
        
        # Calculate costs
        latency_cost = (
            chars['latency_weight'] * component['complexity'] / 10 *
            (self.network_conditions['latency_ms'] / 100)
        )
        
        cpu_cost = (
            chars['cpu_weight'] * component['complexity'] / 10 *
            (self.server_conditions['cpu_percent'] / 50)
        )
        
        bandwidth_cost = (
            chars['bandwidth_weight'] * component['complexity'] / 10 *
            (1 - self.network_conditions['bandwidth_mbps'] / 200)
        )
        
        # Calculate UX score (higher is better)
        cache_bonus = chars['cacheability'] * 0.3
        interactivity_match = (
            component['interactivity'] * (0.8 if strategy in ['CSR', 'PARTIAL'] else 0.4)
        )
        update_freq_match = (
            (1 - component['update_freq'] / 20) if strategy in ['SSG', 'ISR'] else 0.5
        )
        
        ux_score = 0.4 + cache_bonus + interactivity_match * 0.3 + update_freq_match * 0.3
        
        # Weights
        alpha = 0.35  # latency
        beta = 0.25   # cpu
        gamma = 0.20  # bandwidth
        delta = 0.20  # ux
        
        # Calculate reward (negative costs, positive UX)
        reward = -(alpha * latency_cost + beta * cpu_cost + gamma * bandwidth_cost) + delta * ux_score
        
        # Normalize to [-1, 1]
        reward = np.clip(reward, -1, 1)
        
        return float(reward)
    
    def _simulate_render(self, action: int, component: Dict) -> Dict:
        """Simulate rendering and return metrics."""
        strategy = RENDERING_STRATEGIES[action]
        
        # Base render time based on complexity
        base_time = component['complexity'] * 10
        
        # Strategy multipliers
        strategy_multipliers = {
            'CSR': 0.3,
            'SSR': 1.0,
            'SSG': 0.1,
            'ISR': 0.15,
            'STREAM': 0.4,
            'PARTIAL': 0.5,
        }
        
        multiplier = strategy_multipliers[strategy]
        
        # Calculate metrics
        render_time = base_time * multiplier + self.network_conditions['latency_ms'] * 0.1
        ttfb = render_time * 0.3 if strategy in ['SSG', 'ISR'] else render_time * 0.5
        fcp = ttfb + render_time * 0.2
        lcp = fcp + render_time * 0.3
        tti = lcp + (render_time * 0.5 if strategy == 'CSR' else render_time * 0.1)
        
        # Resource usage
        server_cpu = component['complexity'] * 0.05 * multiplier * 100
        bandwidth = component['complexity'] * 1024 * multiplier
        
        # Cache hit
        cache_hit = 1.0 if strategy in ['SSG', 'ISR'] else 0.1
        
        return {
            'ttfb_ms': ttfb,
            'fcp_ms': fcp,
            'lcp_ms': lcp,
            'tti_ms': tti,
            'total_render_time_ms': render_time,
            'server_cpu_seconds': server_cpu / 1000,
            'server_memory_mb': component['complexity'] * 10 * multiplier,
            'bandwidth_bytes': bandwidth,
            'cache_hit_rate': cache_hit,
            'error_rate': 0.01 if np.random.random() < 0.01 else 0,
        }
    
    def _get_cache_hit_ratio(self) -> float:
        """Calculate current cache hit ratio."""
        if not self.render_history:
            return 0.1
        
        cache_hits = sum(
            1 for r in self.render_history[-100:]
            if r['strategy'] in ['SSG', 'ISR']
        )
        
        return cache_hits / min(len(self.render_history), 100)
    
    def _get_last_render_latency(self) -> float:
        """Get last render latency."""
        if not self.metrics_history:
            return 100.0
        
        return self.metrics_history[-1]['total_render_time_ms']
    
    def _get_last_render_success(self) -> bool:
        """Check if last render was successful."""
        if not self.metrics_history:
            return True
        
        return self.metrics_history[-1]['error_rate'] == 0
    
    def _randomize_conditions(self):
        """Randomize network, server, and client conditions."""
        import random
        
        # Random network
        network_keys = list(NETWORK_PRESETS.keys())
        net_preset = NETWORK_PRESETS[random.choice(network_keys)]
        self.network_conditions = {
            'latency_ms': net_preset['latency_ms'] * (0.8 + random.random() * 0.4),
            'bandwidth_mbps': net_preset['bandwidth_mbps'] * (0.8 + random.random() * 0.4),
        }
        
        # Random server
        server_keys = list(SERVER_PRESETS.keys())
        srv_preset = SERVER_PRESETS[random.choice(server_keys)]
        self.server_conditions = {
            'cpu_percent': min(100, srv_preset['cpu_percent'] * (0.8 + random.random() * 0.4)),
            'memory_percent': min(100, srv_preset['memory_percent'] * (0.9 + random.random() * 0.2)),
            'request_rate': srv_preset['request_rate'] * (0.8 + random.random() * 0.4),
        }
        
        # Random client
        device_keys = list(DEVICE_PROFILES.keys())
        device = DEVICE_PROFILES[random.choice(device_keys)]
        self.client_conditions = {
            'cpu_cores': device['cpu_cores'],
            'memory_gb': device['memory_gb'],
            'device_type': device['device_type'],
        }
    
    def _update_conditions(self):
        """Simulate conditions changing over time."""
        import random
        
        # Small random variations
        self.network_conditions['latency_ms'] *= (0.9 + random.random() * 0.2)
        self.network_conditions['bandwidth_mbps'] *= (0.9 + random.random() * 0.2)
        
        self.server_conditions['cpu_percent'] = min(100, 
            self.server_conditions['cpu_percent'] * (0.9 + random.random() * 0.2)
        )
        self.server_conditions['memory_percent'] = min(100,
            self.server_conditions['memory_percent'] * (0.95 + random.random() * 0.1)
        )
    
    def render(self):
        """Render the environment (optional)."""
        if self.render_mode == 'human':
            print(f"Step: {self.current_step}, Component: {COMPONENT_CONFIGS[self.current_component_idx % len(COMPONENT_CONFIGS)]['id']}")
            print(f"  Network: {self.network_conditions}")
            print(f"  Server: {self.server_conditions}")
            if self.render_history:
                last = self.render_history[-1]
                print(f"  Last: {last['strategy']} on {last['component']}")
    
    def get_metrics_summary(self) -> Dict:
        """Get summary of all metrics collected."""
        if not self.metrics_history:
            return {}
        
        metrics_array = {
            'ttfb_ms': [m['ttfb_ms'] for m in self.metrics_history],
            'fcp_ms': [m['fcp_ms'] for m in self.metrics_history],
            'lcp_ms': [m['lcp_ms'] for m in self.metrics_history],
            'tti_ms': [m['tti_ms'] for m in self.metrics_history],
            'total_render_time_ms': [m['total_render_time_ms'] for m in self.metrics_history],
            'server_cpu_seconds': [m['server_cpu_seconds'] for m in self.metrics_history],
            'bandwidth_bytes': [m['bandwidth_bytes'] for m in self.metrics_history],
        }
        
        summary = {}
        for key, values in metrics_array.items():
            values = np.array(values)
            summary[key] = {
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'p50': float(np.percentile(values, 50)),
                'p95': float(np.percentile(values, 95)),
                'p99': float(np.percentile(values, 99)),
            }
        
        # Strategy distribution
        strategy_counts = {}
        for r in self.render_history:
            strategy = r['strategy']
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        summary['strategy_distribution'] = {
            k: v / len(self.render_history) for k, v in strategy_counts.items()
        }
        
        return summary


class BaselineEnvironment(RenderingEnvironment):
    """
    Baseline environment with fixed strategies for comparison.
    """
    
    def __init__(
        self,
        fixed_strategy: str = 'SSR',
        **kwargs
    ):
        super().__init__(**kwargs)
        self.fixed_strategy = fixed_strategy
        self.fixed_action = RENDERING_STRATEGIES.index(fixed_strategy)
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Override to always use fixed strategy."""
        return super().step(self.fixed_action)


class RandomBaselineEnvironment(RenderingEnvironment):
    """Random baseline that selects strategies randomly."""
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Override to use random strategy."""
        random_action = self.action_space.sample()
        return super().step(random_action)


class RoundRobinBaselineEnvironment(RenderingEnvironment):
    """Round-robin baseline that cycles through strategies."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cycle_idx = 0
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Override to cycle through strategies."""
        round_robin_action = self._cycle_idx % NUM_STRATEGIES
        self._cycle_idx += 1
        return super().step(round_robin_action)


class GreedyBaselineEnvironment(RenderingEnvironment):
    """
    Greedy heuristic baseline.
    
    Rules:
    - If server CPU > 70%: prefer CSR or PARTIAL
    - If network latency > 100ms: prefer SSG or ISR
    - If component is highly interactive: prefer CSR
    - Default: SSR
    """
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Override to use greedy heuristic."""
        component = COMPONENT_CONFIGS[self.current_component_idx % len(COMPONENT_CONFIGS)]
        
        # Apply heuristic rules
        if self.server_conditions['cpu_percent'] > 70:
            if component['interactivity'] > 0.7:
                greedy_action = RENDERING_STRATEGIES.index('CSR')
            else:
                greedy_action = RENDERING_STRATEGIES.index('PARTIAL')
        elif self.network_conditions['latency_ms'] > 100:
            greedy_action = RENDERING_STRATEGIES.index('SSG')
        elif component['interactivity'] > 0.7:
            greedy_action = RENDERING_STRATEGIES.index('CSR')
        elif component['update_freq'] < 1:
            greedy_action = RENDERING_STRATEGIES.index('SSG')
        else:
            greedy_action = RENDERING_STRATEGIES.index('SSR')
        
        return super().step(greedy_action)


def make_env(
    env_id: str = "RenderingEnv-v0",
    fixed_strategy: str = "SSR",
    **kwargs
) -> gym.Env:
    """Factory function to create environments."""
    envs = {
        "RenderingEnv-v0": lambda: RenderingEnvironment(**kwargs),
        "CSR-Only-v0": lambda: BaselineEnvironment(fixed_strategy="CSR", **kwargs),
        "SSR-Only-v0": lambda: BaselineEnvironment(fixed_strategy="SSR", **kwargs),
        "SSG-Only-v0": lambda: BaselineEnvironment(fixed_strategy="SSG", **kwargs),
        "ISR-Only-v0": lambda: BaselineEnvironment(fixed_strategy="ISR", **kwargs),
        "STREAM-Only-v0": lambda: BaselineEnvironment(fixed_strategy="STREAM", **kwargs),
        "PARTIAL-Only-v0": lambda: BaselineEnvironment(fixed_strategy="PARTIAL", **kwargs),
        "Random-v0": lambda: RandomBaselineEnvironment(**kwargs),
        "RoundRobin-v0": lambda: RoundRobinBaselineEnvironment(**kwargs),
        "Greedy-v0": lambda: GreedyBaselineEnvironment(**kwargs),
    }
    
    if env_id not in envs:
        raise ValueError(f"Unknown environment: {env_id}. Available: {list(envs.keys())}")
    
    return envs[env_id]()


if __name__ == "__main__":
    # Test the environment
    env = RenderingEnvironment(max_steps=100)
    obs, info = env.reset()
    
    print(f"Initial observation shape: {obs.shape}")
    print(f"Initial observation: {obs}")
    
    total_reward = 0
    for step in range(100):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        
        if terminated or truncated:
            break
    
    print(f"\nTotal reward: {total_reward:.4f}")
    print(f"\nMetrics summary:")
    summary = env.get_metrics_summary()
    for key, value in summary.items():
        if key != 'strategy_distribution':
            print(f"  {key}: mean={value['mean']:.2f}, p95={value['p95']:.2f}")
        else:
            print(f"  {key}: {value}")
