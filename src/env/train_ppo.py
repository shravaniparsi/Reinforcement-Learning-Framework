"""
PPO Training Script for Adaptive Rendering Optimization

This script trains a PPO agent to select optimal rendering strategies
based on system conditions.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
from typing import List, Tuple, Dict
import json
import os
from datetime import datetime

from rendering_env import (
    RenderingEnvironment,
    BaselineEnvironment,
    RandomBaselineEnvironment,
    RoundRobinBaselineEnvironment,
    GreedyBaselineEnvironment,
    RENDERING_STRATEGIES,
    NUM_STRATEGIES,
)


class ActorCritic(nn.Module):
    """Actor-Critic network for PPO."""
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()
        
        # Shared feature extractor
        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
        )
        
        # Actor (policy) head
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim),
        )
        
        # Critic (value) head
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )
    
    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Forward pass returning action logits, values, and entropy."""
        features = self.shared(state)
        
        action_logits = self.actor(features)
        values = self.critic(features)
        
        # Calculate entropy for exploration
        dist = Categorical(logits=action_logits)
        entropy = dist.entropy()
        
        return action_logits, values.squeeze(-1), entropy
    
    def get_action(self, state: torch.Tensor, deterministic: bool = False) -> Tuple[int, float, float]:
        """Select an action given state."""
        with torch.no_grad():
            action_logits, value, _ = self.forward(state)
            dist = Categorical(logits=action_logits)
            
            if deterministic:
                action = torch.argmax(action_logits, dim=-1)
            else:
                action = dist.sample()
            
            log_prob = dist.log_prob(action)
        
        return action.item(), value.item(), log_prob.item()
    
    def evaluate(self, states: torch.Tensor, actions: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Evaluate actions for PPO update."""
        action_logits, values, entropy = self.forward(states)
        dist = Categorical(logits=action_logits)
        log_probs = dist.log_prob(actions)
        
        return log_probs, values, entropy


class RolloutBuffer:
    """Buffer for storing rollout trajectories."""
    
    def __init__(self):
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
        self.dones = []
    
    def add(self, state, action, reward, value, log_prob, done):
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.values.append(value)
        self.log_probs.append(log_prob)
        self.dones.append(done)
    
    def clear(self):
        self.states.clear()
        self.actions.clear()
        self.rewards.clear()
        self.values.clear()
        self.log_probs.clear()
        self.dones.clear()
    
    def compute_returns(self, gamma: float = 0.99, gae_lambda: float = 0.95):
        """Compute GAE returns."""
        returns = []
        advantages = []
        
        # Calculate GAE
        gae = 0
        for t in reversed(range(len(self.rewards))):
            if t == len(self.rewards) - 1:
                next_value = 0
            else:
                next_value = self.values[t + 1]
            
            delta = self.rewards[t] + gamma * next_value * (1 - self.dones[t]) - self.values[t]
            gae = delta + gamma * gae_lambda * (1 - self.dones[t]) * gae
            advantages.insert(0, gae)
            returns.insert(0, gae + self.values[t])
        
        return (
            torch.tensor(returns, dtype=torch.float32),
            torch.tensor(advantages, dtype=torch.float32),
        )
    
    def get_batches(self, batch_size: int):
        """Generate mini-batches."""
        n = len(self.states)
        indices = np.random.permutation(n)
        
        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            batch_indices = indices[start:end]
            
            yield (
                torch.tensor(np.array([self.states[i] for i in batch_indices]), dtype=torch.float32),
                torch.tensor([self.actions[i] for i in batch_indices], dtype=torch.long),
                torch.tensor([self.log_probs[i] for i in batch_indices], dtype=torch.float32),
                torch.tensor([self.rewards[i] for i in batch_indices], dtype=torch.float32),
                torch.tensor([self.values[i] for i in batch_indices], dtype=torch.float32),
                torch.tensor([self.dones[i] for i in batch_indices], dtype=torch.float32),
            )


class PPOAgent:
    """PPO Agent for rendering optimization."""
    
    def __init__(
        self,
        state_dim: int = 15,
        action_dim: int = NUM_STRATEGIES,
        hidden_dim: int = 256,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_range: float = 0.2,
        value_loss_coef: float = 0.5,
        entropy_coef: float = 0.01,
        max_grad_norm: float = 0.5,
        n_epochs: int = 10,
        batch_size: int = 64,
    ):
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_range = clip_range
        self.value_loss_coef = value_loss_coef
        self.entropy_coef = entropy_coef
        self.max_grad_norm = max_grad_norm
        self.n_epochs = n_epochs
        self.batch_size = batch_size
        
        # Device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
        
        # Networks
        self.policy = ActorCritic(state_dim, action_dim, hidden_dim).to(self.device)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)
        
        # Buffer
        self.buffer = RolloutBuffer()
        
        # Training stats
        self.training_step = 0
        self.episode_rewards = []
    
    def select_action(self, state: np.ndarray, deterministic: bool = False) -> Tuple[int, float, float]:
        """Select action given state."""
        state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0).to(self.device)
        action, value, log_prob = self.policy.get_action(state_tensor, deterministic)
        return action, value, log_prob
    
    def update(self) -> Dict[str, float]:
        """Update policy using PPO algorithm."""
        if len(self.buffer.states) == 0:
            return {}
        
        # Compute returns
        returns, advantages = self.buffer.compute_returns(self.gamma, self.gae_lambda)
        
        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # Convert buffer to tensors
        states = torch.tensor(np.array(self.buffer.states), dtype=torch.float32).to(self.device)
        actions = torch.tensor(self.buffer.actions, dtype=torch.long).to(self.device)
        old_log_probs = torch.tensor(self.buffer.log_probs, dtype=torch.float32).to(self.device)
        
        # PPO update
        total_policy_loss = 0
        total_value_loss = 0
        total_entropy_loss = 0
        
        for epoch in range(self.n_epochs):
            # Mini-batch updates
            for batch in self.buffer.get_batches(self.batch_size):
                batch_states, batch_actions, batch_old_log_probs, _, _, _ = batch
                batch_states = batch_states.to(self.device)
                batch_actions = batch_actions.to(self.device)
                batch_old_log_probs = batch_old_log_probs.to(self.device)
                
                # Evaluate current policy
                new_log_probs, values, entropy = self.policy.evaluate(batch_states, batch_actions)
                
                # Calculate policy loss (clipped)
                ratio = torch.exp(new_log_probs - batch_old_log_probs)
                surr1 = ratio * advantages[:len(batch_states)].to(self.device)
                surr2 = torch.clamp(ratio, 1 - self.clip_range, 1 + self.clip_range) * advantages[:len(batch_states)].to(self.device)
                policy_loss = -torch.min(surr1, surr2).mean()
                
                # Calculate value loss
                value_loss = nn.MSELoss()(values, returns[:len(batch_states)].to(self.device))
                
                # Calculate entropy loss (for exploration)
                entropy_loss = -entropy.mean()
                
                # Total loss
                loss = (
                    policy_loss +
                    self.value_loss_coef * value_loss +
                    self.entropy_coef * entropy_loss
                )
                
                # Update
                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.policy.parameters(), self.max_grad_norm)
                self.optimizer.step()
                
                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy_loss += entropy_loss.item()
        
        # Clear buffer
        self.buffer.clear()
        
        n_updates = self.n_epochs * max(1, len(self.buffer.states) // self.batch_size)
        
        return {
            'policy_loss': total_policy_loss / n_updates,
            'value_loss': total_value_loss / n_updates,
            'entropy_loss': total_entropy_loss / n_updates,
        }
    
    def save(self, path: str):
        """Save model checkpoint."""
        torch.save({
            'policy_state_dict': self.policy.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'training_step': self.training_step,
            'episode_rewards': self.episode_rewards,
        }, path)
    
    def load(self, path: str):
        """Load model checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        self.policy.load_state_dict(checkpoint['policy_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.training_step = checkpoint['training_step']
        self.episode_rewards = checkpoint['episode_rewards']


def train(
    env_id: str = "RenderingEnv-v0",
    n_episodes: int = 5000,
    max_steps_per_episode: int = 1000,
    log_interval: int = 100,
    save_interval: int = 500,
    save_dir: str = "checkpoints",
    seed: int = 42,
) -> Dict:
    """Train PPO agent."""
    from rendering_env import make_env
    
    # Create environment
    env = make_env(env_id, max_steps=max_steps_per_episode)
    
    # Set seeds
    np.random.seed(seed)
    torch.manual_seed(seed)
    env.reset(seed=seed)
    
    # Create agent
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
    
    # Create save directory
    os.makedirs(save_dir, exist_ok=True)
    
    # Training loop
    episode_rewards = []
    episode_lengths = []
    episode_strategies = {s: 0 for s in RENDERING_STRATEGIES}
    
    print(f"\nStarting training for {n_episodes} episodes...")
    print(f"Environment: {env_id}")
    print(f"Max steps per episode: {max_steps_per_episode}")
    print(f"Device: {agent.device}")
    print("-" * 60)
    
    for episode in range(n_episodes):
        state, info = env.reset()
        episode_reward = 0
        episode_length = 0
        
        for step in range(max_steps_per_episode):
            # Select action
            action, value, log_prob = agent.select_action(state)
            
            # Take step
            next_state, reward, terminated, truncated, info = env.step(action)
            
            # Store transition
            agent.buffer.add(state, action, reward, value, log_prob, terminated or truncated)
            
            episode_reward += reward
            episode_length += 1
            
            # Track strategy usage
            episode_strategies[info['strategy']] += 1
            
            if terminated or truncated:
                break
            
            state = next_state
        
        # Update policy
        if (episode + 1) % 10 == 0:
            update_info = agent.update()
        
        # Track rewards
        episode_rewards.append(episode_reward)
        episode_lengths.append(episode_length)
        agent.episode_rewards.append(episode_reward)
        
        # Logging
        if (episode + 1) % log_interval == 0:
            avg_reward = np.mean(episode_rewards[-log_interval:])
            avg_length = np.mean(episode_lengths[-log_interval:])
            
            print(f"Episode {episode + 1}/{n_episodes}")
            print(f"  Avg Reward: {avg_reward:.4f}")
            print(f"  Avg Length: {avg_length:.1f}")
            print(f"  Strategies: { {k: v/sum(episode_strategies.values()) for k, v in episode_strategies.items()} }")
            print("-" * 60)
        
        # Save checkpoint
        if (episode + 1) % save_interval == 0:
            checkpoint_path = os.path.join(save_dir, f"ppo_episode_{episode + 1}.pt")
            agent.save(checkpoint_path)
            print(f"Saved checkpoint to {checkpoint_path}")
    
    # Save final model
    final_path = os.path.join(save_dir, "ppo_final.pt")
    agent.save(final_path)
    print(f"\nTraining complete! Final model saved to {final_path}")
    
    # Return training results
    return {
        'episode_rewards': episode_rewards,
        'episode_lengths': episode_lengths,
        'final_strategy_distribution': {k: v/sum(episode_strategies.values()) for k, v in episode_strategies.items()},
        'convergence_episode': find_convergence(episode_rewards),
    }


def find_convergence(rewards: List[float], window: int = 100, threshold: float = 0.01) -> int:
    """Find episode where rewards converged."""
    if len(rewards) < window:
        return len(rewards)
    
    running_avg = np.convolve(rewards, np.ones(window)/window, mode='valid')
    
    for i in range(1, len(running_avg)):
        if abs(running_avg[i] - running_avg[i-1]) < threshold:
            return i
    
    return len(rewards)


def evaluate_agent(
    agent: PPOAgent,
    env_id: str = "RenderingEnv-v0",
    n_episodes: int = 100,
    max_steps: int = 1000,
    seed: int = 123,
) -> Dict:
    """Evaluate trained agent."""
    from rendering_env import make_env
    
    env = make_env(env_id, max_steps=max_steps)
    env.reset(seed=seed)
    
    all_rewards = []
    all_lengths = []
    all_metrics = []
    
    for episode in range(n_episodes):
        state, _ = env.reset()
        episode_reward = 0
        
        for step in range(max_steps):
            action, _, _ = agent.select_action(state, deterministic=True)
            state, reward, terminated, truncated, _ = env.step(action)
            episode_reward += reward
            
            if terminated or truncated:
                break
        
        all_rewards.append(episode_reward)
        all_lengths.append(step + 1)
        all_metrics.append(env.get_metrics_summary())
    
    return {
        'mean_reward': np.mean(all_rewards),
        'std_reward': np.std(all_rewards),
        'mean_length': np.mean(all_lengths),
        'metrics': aggregate_metrics(all_metrics),
    }


def aggregate_metrics(metrics_list: List[Dict]) -> Dict:
    """Aggregate metrics across episodes."""
    if not metrics_list:
        return {}
    
    aggregated = {}
    for key in metrics_list[0].keys():
        if key == 'strategy_distribution':
            # Aggregate strategy distribution
            total = {}
            for m in metrics_list:
                for strategy, count in m[key].items():
                    total[strategy] = total.get(strategy, 0) + count
            aggregated[key] = {k: v/len(metrics_list) for k, v in total.items()}
        else:
            # Aggregate numeric metrics
            values = [m[key]['mean'] for m in metrics_list if key in m]
            if values:
                aggregated[key] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                }
    
    return aggregated


def run_baselines(
    n_episodes: int = 100,
    max_steps: int = 1000,
    seed: int = 42,
) -> Dict:
    """Run all baseline strategies for comparison."""
    from rendering_env import make_env
    
    baselines = {
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
    
    results = {}
    
    for name, env_id in baselines.items():
        print(f"\nEvaluating baseline: {name}")
        env = make_env(env_id, max_steps=max_steps)
        
        all_rewards = []
        all_metrics = []
        
        for episode in range(n_episodes):
            state, _ = env.reset(seed=seed + episode)
            episode_reward = 0
            
            for step in range(max_steps):
                # Baselines use fixed or simple strategies
                action = env.action_space.sample()  # Will be overridden by environment
                state, reward, terminated, truncated, _ = env.step(action)
                episode_reward += reward
                
                if terminated or truncated:
                    break
            
            all_rewards.append(episode_reward)
            all_metrics.append(env.get_metrics_summary())
        
        results[name] = {
            'mean_reward': np.mean(all_rewards),
            'std_reward': np.std(all_rewards),
            'metrics': aggregate_metrics(all_metrics),
        }
        
        print(f"  Mean Reward: {results[name]['mean_reward']:.4f} ± {results[name]['std_reward']:.4f}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train PPO for rendering optimization")
    parser.add_argument("--episodes", type=int, default=5000, help="Number of training episodes")
    parser.add_argument("--max-steps", type=int, default=1000, help="Max steps per episode")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--save-dir", type=str, default="checkpoints", help="Save directory")
    parser.add_argument("--mode", choices=["train", "evaluate", "baselines"], default="train")
    
    args = parser.parse_args()
    
    if args.mode == "train":
        results = train(
            n_episodes=args.episodes,
            max_steps_per_episode=args.max_steps,
            seed=args.seed,
            save_dir=args.save_dir,
        )
        
        # Save results
        results_path = os.path.join(args.save_dir, "training_results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
    elif args.mode == "evaluate":
        agent = PPOAgent()
        agent.load(os.path.join(args.save_dir, "ppo_final.pt"))
        
        results = evaluate_agent(agent, n_episodes=100)
        
        print("\nEvaluation Results:")
        print(f"  Mean Reward: {results['mean_reward']:.4f} ± {results['std_reward']:.4f}")
        print(f"  Mean Length: {results['mean_length']:.1f}")
        print(f"  Metrics: {results['metrics']}")
        
    elif args.mode == "baselines":
        results = run_baselines(n_episodes=100)
        
        # Save results
        results_path = os.path.join(args.save_dir, "baseline_results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print("\nBaseline comparison complete!")
