"""
Parallel Experiment Runner for Cloud

Splits experiments across multiple workers for faster completion.
Can be run on Colab, Kaggle, or multiple terminals.
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, List
import numpy as np

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rendering_env import make_env, RENDERING_STRATEGIES, NUM_STRATEGIES
from train_ppo import PPOAgent


def run_worker(
    worker_id: int,
    total_workers: int,
    n_episodes: int,
    max_steps: int,
    output_dir: str,
    checkpoint_path: str = None,
):
    """Run experiments for a subset of conditions."""
    
    # Load or create agent
    agent = PPOAgent(
        state_dim=15,
        action_dim=NUM_STRATEGIES,
        hidden_dim=256,
        lr=3e-4,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        n_epochs=10,
        batch_size=64,
    )
    
    if checkpoint_path and os.path.exists(checkpoint_path):
        agent.load(checkpoint_path)
        print(f"Worker {worker_id}: Loaded checkpoint")
    else:
        print(f"Worker {worker_id}: Using untrained agent")
    
    # Generate conditions for this worker
    from experiment_runner import ExperimentRunner, ExperimentConfig
    
    runner = ExperimentRunner(
        n_seeds=1,
        n_episodes_per_experiment=n_episodes,
        max_steps_per_episode=max_steps,
        output_dir=output_dir,
    )
    
    # Generate all configs
    network_presets = ['excellent', 'good', 'moderate', 'poor', 'terrible']
    server_presets = ['idle', 'normal', 'high', 'overload']
    device_profiles = ['high_end', 'mid_range', 'low_end', 'iot']
    
    all_configs = []
    for network in network_presets:
        for server in server_presets:
            for device in device_profiles:
                for seed_idx in range(3):  # 3 seeds per condition
                    all_configs.append(ExperimentConfig(
                        name=f"{network}_{server}_{device}_seed{seed_idx}",
                        env_id="RenderingEnv-v0",
                        n_episodes=n_episodes,
                        max_steps=max_steps,
                        network_preset=network,
                        server_preset=server,
                        device_profile=device,
                        seed=42 + seed_idx,
                    ))
    
    # Split configs across workers
    worker_configs = all_configs[worker_id::total_workers]
    
    print(f"Worker {worker_id}: Running {len(worker_configs)} experiments")
    
    # Run experiments
    results = []
    for i, config in enumerate(worker_configs):
        result = runner.run_single_experiment(config, agent)
        results.append(result)
        
        if (i + 1) % 10 == 0:
            print(f"Worker {worker_id}: Progress {i+1}/{len(worker_configs)}")
    
    # Save worker results
    output_file = os.path.join(output_dir, f"worker_{worker_id}_results.json")
    with open(output_file, 'w') as f:
        json.dump([{
            'config': {
                'name': r.config.name,
                'env_id': r.config.env_id,
                'network_preset': r.config.network_preset,
                'server_preset': r.config.server_preset,
                'device_profile': r.config.device_profile,
                'seed': r.config.seed,
            },
            'mean_reward': r.mean_reward,
            'std_reward': r.std_reward,
            'mean_latency': r.mean_latency,
            'mean_ttfb': r.mean_ttfb,
            'mean_tti': r.mean_tti,
            'mean_cpu_usage': r.mean_cpu_usage,
            'mean_bandwidth': r.mean_bandwidth,
            'mean_cache_hit_rate': r.mean_cache_hit_rate,
            'strategy_distribution': r.strategy_distribution,
            'convergence_episode': r.convergence_episode,
        } for r in results], f, indent=2, default=str)
    
    print(f"Worker {worker_id}: Saved {len(results)} results to {output_file}")
    
    return results


def merge_results(output_dir: str, n_workers: int):
    """Merge results from all workers."""
    
    all_results = []
    
    for worker_id in range(n_workers):
        worker_file = os.path.join(output_dir, f"worker_{worker_id}_results.json")
        if os.path.exists(worker_file):
            with open(worker_file, 'r') as f:
                worker_results = json.load(f)
                all_results.extend(worker_results)
    
    # Group by strategy
    strategy_results = {}
    for result in all_results:
        # Determine strategy from config name
        config = result['config']
        strategy = 'RL-Agent'  # All use the same agent
        
        if strategy not in strategy_results:
            strategy_results[strategy] = []
        
        strategy_results[strategy].append(result)
    
    # Save merged results
    merged_file = os.path.join(output_dir, "merged_results.json")
    with open(merged_file, 'w') as f:
        json.dump(strategy_results, f, indent=2, default=str)
    
    print(f"Merged {len(all_results)} results to {merged_file}")
    
    return strategy_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parallel experiment runner")
    parser.add_argument("--worker-id", type=int, required=True, help="Worker ID (0-indexed)")
    parser.add_argument("--total-workers", type=int, required=True, help="Total number of workers")
    parser.add_argument("--n-episodes", type=int, default=100, help="Episodes per experiment")
    parser.add_argument("--max-steps", type=int, default=500, help="Max steps per episode")
    parser.add_argument("--output-dir", type=str, default="parallel_results", help="Output directory")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to trained checkpoint")
    parser.add_argument("--merge", action="store_true", help="Merge results from all workers")
    
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    if args.merge:
        merge_results(args.output_dir, args.total_workers)
    else:
        run_worker(
            worker_id=args.worker_id,
            total_workers=args.total_workers,
            n_episodes=args.n_episodes,
            max_steps=args.max_steps,
            output_dir=args.output_dir,
            checkpoint_path=args.checkpoint,
        )
