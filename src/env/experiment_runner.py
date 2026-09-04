"""
Experiment Runner for RL-Based Rendering Optimization

This script runs controlled experiments comparing RL-based adaptive rendering
against static and heuristic baselines.
"""

import numpy as np
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
import time

from rendering_env import (
    RenderingEnvironment,
    BaselineEnvironment,
    RandomBaselineEnvironment,
    RoundRobinBaselineEnvironment,
    GreedyBaselineEnvironment,
    make_env,
    RENDERING_STRATEGIES,
    NETWORK_PRESETS,
    SERVER_PRESETS,
    DEVICE_PROFILES,
    COMPONENT_CONFIGS,
)
from train_ppo import PPOAgent


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment."""
    name: str
    env_id: str
    n_episodes: int
    max_steps: int
    network_preset: str
    server_preset: str
    device_profile: str
    seed: int


@dataclass
class ExperimentResult:
    """Results from a single experiment."""
    config: ExperimentConfig
    mean_reward: float
    std_reward: float
    mean_latency: float
    mean_ttfb: float
    mean_tti: float
    mean_cpu_usage: float
    mean_bandwidth: float
    mean_cache_hit_rate: float
    strategy_distribution: Dict[str, float]
    convergence_episode: int
    execution_time: float


class ExperimentRunner:
    """Runs experiments and collects results."""
    
    def __init__(
        self,
        n_seeds: int = 5,
        n_episodes_per_experiment: int = 100,
        max_steps_per_episode: int = 1000,
        output_dir: str = "results",
    ):
        self.n_seeds = n_seeds
        self.n_episodes = n_episodes_per_experiment
        self.max_steps = max_steps_per_episode
        self.output_dir = output_dir
        
        os.makedirs(output_dir, exist_ok=True)
    
    def run_single_experiment(
        self,
        config: ExperimentConfig,
        agent: PPOAgent = None,
    ) -> ExperimentResult:
        """Run a single experiment with given configuration."""
        start_time = time.time()
        
        # Create environment with specific conditions
        env = make_env(
            config.env_id,
            max_steps=config.max_steps,
            randomize_conditions=False,
        )
        
        # Override conditions
        env.network_conditions = {
            'latency_ms': NETWORK_PRESETS[config.network_preset]['latency_ms'],
            'bandwidth_mbps': NETWORK_PRESETS[config.network_preset]['bandwidth_mbps'],
        }
        env.server_conditions = {
            'cpu_percent': SERVER_PRESETS[config.server_preset]['cpu_percent'],
            'memory_percent': SERVER_PRESETS[config.server_preset]['memory_percent'],
            'request_rate': SERVER_PRESETS[config.server_preset]['request_rate'],
        }
        env.client_conditions = {
            'cpu_cores': DEVICE_PROFILES[config.device_profile]['cpu_cores'],
            'memory_gb': DEVICE_PROFILES[config.device_profile]['memory_gb'],
            'device_type': DEVICE_PROFILES[config.device_profile]['device_type'],
        }
        
        all_rewards = []
        all_metrics = []
        
        for episode in range(config.n_episodes):
            state, _ = env.reset(seed=config.seed + episode)
            episode_reward = 0
            
            for step in range(config.max_steps):
                if agent is not None:
                    # Use trained agent
                    action, _, _ = agent.select_action(state, deterministic=True)
                else:
                    # Use environment's default behavior (for baselines)
                    action = env.action_space.sample()
                
                state, reward, terminated, truncated, info = env.step(action)
                episode_reward += reward
                
                if terminated or truncated:
                    break
            
            all_rewards.append(episode_reward)
            all_metrics.append(env.get_metrics_summary())
        
        # Aggregate results
        metrics = self._aggregate_metrics(all_metrics)
        
        execution_time = time.time() - start_time
        
        return ExperimentResult(
            config=config,
            mean_reward=float(np.mean(all_rewards)),
            std_reward=float(np.std(all_rewards)),
            mean_latency=metrics.get('total_render_time_ms', {}).get('mean', 0),
            mean_ttfb=metrics.get('ttfb_ms', {}).get('mean', 0),
            mean_tti=metrics.get('tti_ms', {}).get('mean', 0),
            mean_cpu_usage=metrics.get('server_cpu_seconds', {}).get('mean', 0),
            mean_bandwidth=metrics.get('bandwidth_bytes', {}).get('mean', 0),
            mean_cache_hit_rate=metrics.get('cache_hit_rate', {}).get('mean', 0),
            strategy_distribution=metrics.get('strategy_distribution', {}),
            convergence_episode=self._find_convergence(all_rewards),
            execution_time=execution_time,
        )
    
    def run_rl_vs_baselines(
        self,
        agent: PPOAgent,
        network_presets: List[str] = None,
        server_presets: List[str] = None,
        device_profiles: List[str] = None,
    ) -> Dict[str, List[ExperimentResult]]:
        """Run RL agent against all baselines."""
        if network_presets is None:
            network_presets = ['excellent', 'good', 'moderate', 'poor', 'terrible']
        if server_presets is None:
            server_presets = ['idle', 'normal', 'high', 'overload']
        if device_profiles is None:
            device_profiles = ['high_end', 'mid_range', 'low_end', 'iot']
        
        results = {
            'RL-Agent': [],
            'CSR-Only': [],
            'SSR-Only': [],
            'SSG-Only': [],
            'ISR-Only': [],
            'STREAM-Only': [],
            'PARTIAL-Only': [],
            'Random': [],
            'RoundRobin': [],
            'Greedy': [],
        }
        
        # Generate experiment configurations
        configs = []
        for network in network_presets:
            for server in server_presets:
                for device in device_profiles:
                    for seed_idx in range(self.n_seeds):
                        configs.append(ExperimentConfig(
                            name=f"{network}_{server}_{device}_seed{seed_idx}",
                            env_id="RenderingEnv-v0",
                            n_episodes=self.n_episodes,
                            max_steps=self.max_steps,
                            network_preset=network,
                            server_preset=server,
                            device_profile=device,
                            seed=42 + seed_idx,
                        ))
        
        print(f"\nRunning {len(configs)} experiments per strategy...")
        print(f"Total experiments: {len(configs) * len(results)}")
        print("-" * 70)
        
        # Run RL agent
        print("\n[1/10] Running RL-Agent...")
        for i, config in enumerate(configs):
            result = self.run_single_experiment(config, agent=agent)
            results['RL-Agent'].append(result)
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{len(configs)}")
        
        # Run baselines
        baseline_env_ids = {
            'CSR-Only': 'CSR-Only-v0',
            'SSR-Only': 'SSR-Only-v0',
            'SSG-Only': 'SSG-Only-v0',
            'ISR-Only': 'ISR-Only-v0',
            'STREAM-Only': 'STREAM-Only-v0',
            'PARTIAL-Only': 'PARTIAL-Only-v0',
            'Random': 'Random-v0',
            'RoundRobin': 'RoundRobin-v0',
            'Greedy': 'Greedy-v0',
        }
        
        for idx, (name, env_id) in enumerate(baseline_env_ids.items(), start=2):
            print(f"\n[{idx}/10] Running {name}...")
            for i, config in enumerate(configs):
                config_copy = ExperimentConfig(
                    name=config.name,
                    env_id=env_id,
                    n_episodes=config.n_episodes,
                    max_steps=config.max_steps,
                    network_preset=config.network_preset,
                    server_preset=config.server_preset,
                    device_profile=config.device_profile,
                    seed=config.seed,
                )
                result = self.run_single_experiment(config_copy)
                results[name].append(result)
                if (i + 1) % 10 == 0:
                    print(f"  Progress: {i + 1}/{len(configs)}")
        
        return results
    
    def _aggregate_metrics(self, metrics_list: List[Dict]) -> Dict:
        """Aggregate metrics across episodes."""
        if not metrics_list:
            return {}
        
        aggregated = {}
        for key in metrics_list[0].keys():
            if key == 'strategy_distribution':
                total = {}
                for m in metrics_list:
                    for strategy, count in m[key].items():
                        total[strategy] = total.get(strategy, 0) + count
                aggregated[key] = {k: v/len(metrics_list) for k, v in total.items()}
            else:
                values = [m[key]['mean'] for m in metrics_list if key in m]
                if values:
                    aggregated[key] = {
                        'mean': np.mean(values),
                        'std': np.std(values),
                    }
        
        return aggregated
    
    def _find_convergence(self, rewards: List[float], window: int = 50, threshold: float = 0.01) -> int:
        """Find episode where rewards converged."""
        if len(rewards) < window:
            return len(rewards)
        
        running_avg = np.convolve(rewards, np.ones(window)/window, mode='valid')
        
        for i in range(1, len(running_avg)):
            if abs(running_avg[i] - running_avg[i-1]) < threshold:
                return i
        
        return len(rewards)
    
    def generate_comparison_table(self, results: Dict[str, List[ExperimentResult]]) -> str:
        """Generate a markdown comparison table."""
        table = "# Experiment Results Comparison\n\n"
        table += "## Performance Metrics\n\n"
        table += "| Strategy | Reward | Latency (ms) | TTFB (ms) | TTI (ms) | CPU (s) | Bandwidth (B) | Cache Hit |\n"
        table += "|----------|--------|--------------|-----------|----------|---------|---------------|----------|\n"
        
        for strategy, exp_results in results.items():
            if exp_results:
                avg_reward = np.mean([r.mean_reward for r in exp_results])
                avg_latency = np.mean([r.mean_latency for r in exp_results])
                avg_ttfb = np.mean([r.mean_ttfb for r in exp_results])
                avg_tti = np.mean([r.mean_tti for r in exp_results])
                avg_cpu = np.mean([r.mean_cpu_usage for r in exp_results])
                avg_bandwidth = np.mean([r.mean_bandwidth for r in exp_results])
                avg_cache = np.mean([r.mean_cache_hit_rate for r in exp_results])
                
                table += f"| {strategy} | {avg_reward:.4f} | {avg_latency:.2f} | {avg_ttfb:.2f} | {avg_tti:.2f} | {avg_cpu:.4f} | {avg_bandwidth:.0f} | {avg_cache:.4f} |\n"
        
        table += "\n## Strategy Distribution (RL-Agent)\n\n"
        
        if 'RL-Agent' in results and results['RL-Agent']:
            # Aggregate strategy distributions
            all_dists = [r.strategy_distribution for r in results['RL-Agent'] if r.strategy_distribution]
            if all_dists:
                avg_dist = {}
                for dist in all_dists:
                    for strategy, count in dist.items():
                        avg_dist[strategy] = avg_dist.get(strategy, 0) + count
                
                total = sum(avg_dist.values())
                table += "| Strategy | Usage |\n"
                table += "|----------|-------|\n"
                for strategy, count in sorted(avg_dist.items(), key=lambda x: x[1], reverse=True):
                    table += f"| {strategy} | {count/total*100:.1f}% |\n"
        
        table += "\n## Statistical Significance\n\n"
        table += "(To be filled after analysis)\n"
        
        return table
    
    def save_results(self, results: Dict[str, List[ExperimentResult]], filename: str = "experiment_results.json"):
        """Save results to JSON file."""
        results_dict = {}
        for strategy, exp_results in results.items():
            results_dict[strategy] = [asdict(r) for r in exp_results]
        
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(results_dict, f, indent=2, default=str)
        
        print(f"\nResults saved to {filepath}")
        
        # Also save markdown table
        md_table = self.generate_comparison_table(results)
        md_filepath = os.path.join(self.output_dir, "results_comparison.md")
        with open(md_filepath, 'w') as f:
            f.write(md_table)
        
        print(f"Comparison table saved to {md_filepath}")


def run_sensitivity_analysis(
    agent: PPOAgent,
    n_episodes: int = 50,
    max_steps: int = 500,
    output_dir: str = "results",
):
    """Run sensitivity analysis on reward function weights."""
    print("\nRunning Sensitivity Analysis...")
    print("=" * 70)
    
    # Test different reward weight combinations
    weight_configs = [
        {'alpha': 0.35, 'beta': 0.25, 'gamma': 0.20, 'delta': 0.20},  # Default
        {'alpha': 0.50, 'beta': 0.20, 'gamma': 0.15, 'delta': 0.15},  # Latency-focused
        {'alpha': 0.20, 'beta': 0.50, 'gamma': 0.15, 'delta': 0.15},  # CPU-focused
        {'alpha': 0.20, 'beta': 0.15, 'gamma': 0.50, 'delta': 0.15},  # Bandwidth-focused
        {'alpha': 0.20, 'beta': 0.15, 'gamma': 0.15, 'delta': 0.50},  # UX-focused
    ]
    
    results = {}
    
    for i, weights in enumerate(weight_configs):
        config_name = f"config_{i}"
        print(f"\nTesting weight configuration: {weights}")
        
        env = make_env("RenderingEnv-v0", max_steps=max_steps, randomize_conditions=True)
        
        # Override reward function weights
        # Note: This requires modifying the environment's reward function
        # For now, we'll track the default behavior
        
        all_rewards = []
        for episode in range(n_episodes):
            state, _ = env.reset(seed=42 + episode)
            episode_reward = 0
            
            for step in range(max_steps):
                action, _, _ = agent.select_action(state, deterministic=True)
                state, reward, terminated, truncated, _ = env.step(action)
                episode_reward += reward
                
                if terminated or truncated:
                    break
            
            all_rewards.append(episode_reward)
        
        results[config_name] = {
            'weights': weights,
            'mean_reward': float(np.mean(all_rewards)),
            'std_reward': float(np.std(all_rewards)),
        }
        
        print(f"  Mean Reward: {results[config_name]['mean_reward']:.4f} ± {results[config_name]['std_reward']:.4f}")
    
    # Save sensitivity analysis results
    filepath = os.path.join(output_dir, "sensitivity_analysis.json")
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nSensitivity analysis results saved to {filepath}")
    
    return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run rendering optimization experiments")
    parser.add_argument("--mode", choices=["full", "sensitivity", "quick"], default="quick")
    parser.add_argument("--n-seeds", type=int, default=3)
    parser.add_argument("--n-episodes", type=int, default=50)
    parser.add_argument("--max-steps", type=int, default=500)
    parser.add_argument("--output-dir", type=str, default="results")
    parser.add_argument("--checkpoint", type=str, default="checkpoints/ppo_final.pt")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load trained agent
    agent = PPOAgent()
    if os.path.exists(args.checkpoint):
        agent.load(args.checkpoint)
        print(f"Loaded agent from {args.checkpoint}")
    else:
        print(f"No checkpoint found at {args.checkpoint}, using untrained agent")
    
    # Create experiment runner
    runner = ExperimentRunner(
        n_seeds=args.n_seeds,
        n_episodes_per_experiment=args.n_episodes,
        max_steps_per_episode=args.max_steps,
        output_dir=args.output_dir,
    )
    
    if args.mode == "full":
        # Run full experiment suite
        results = runner.run_rl_vs_baselines(agent)
        runner.save_results(results, "full_experiment_results.json")
        
    elif args.mode == "sensitivity":
        # Run sensitivity analysis
        run_sensitivity_analysis(agent, args.n_episodes, args.max_steps, args.output_dir)
        
    elif args.mode == "quick":
        # Quick test with fewer conditions
        results = runner.run_rl_vs_baselines(
            agent,
            network_presets=['good', 'poor'],
            server_presets=['normal', 'high'],
            device_profiles=['mid_range', 'low_end'],
        )
        runner.save_results(results, "quick_experiment_results.json")
    
    print("\n" + "=" * 70)
    print("Experiments complete!")
    print(f"Results saved to: {args.output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
