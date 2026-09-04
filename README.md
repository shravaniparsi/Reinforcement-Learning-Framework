# RL-Based Adaptive Component Rendering Optimization

A reinforcement learning framework for adaptive real-time component rendering optimization in full-stack web applications.

## Overview

This project implements a PPO (Proximal Policy Optimization) agent that dynamically selects rendering strategies (CSR, SSR, SSG, ISR, Streaming SSR, Partial Hydration) based on runtime conditions including network latency, server load, device capabilities, and component characteristics.

## Project Structure

```
rl-rendering/
├── src/
│   ├── app/                    # Next.js pages
│   ├── components/             # 10 React components
│   ├── api/                    # Free API integrations
│   ├── strategies/             # Rendering strategy implementations
│   └── env/                    # RL environment and training
│       ├── rendering_env.py    # OpenAI Gym environment
│       ├── train_ppo.py        # PPO training script
│       ├── experiment_runner.py # Experiment orchestration
│       └── analyze_results.py  # Statistical analysis
├── requirements.txt            # Python dependencies
└── run.sh                      # Setup and run script
```

## Quick Start

```bash
# Setup
./run.sh setup

# Start web app
./run.sh dev

# Train RL agent (5000 episodes)
./run.sh train

# Run experiments
./run.sh experiment

# Analyze results
./run.sh analyze
```

## Free APIs Used

- **FakeStore** - Product data
- **DummyJSON** - Users, carts, posts
- **Dog CEO** - Dog images
- **TheCatAPI** - Cat images
- **TheMealDB** - Recipe data
- **Frankfurter** - Currency exchange rates
- **PokeAPI** - Pokemon data

## Rendering Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| CSR | Client-side rendering | Interactive components |
| SSR | Server-side rendering | SEO, initial load |
| SSG | Static site generation | Static content |
| ISR | Incremental static regeneration | Semi-static content |
| STREAM | Streaming SSR | Large pages |
| PARTIAL | Partial hydration | Mixed content |

## License

MIT
