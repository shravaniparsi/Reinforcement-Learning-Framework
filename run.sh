#!/bin/bash
# RL Rendering Optimization - Setup and Run Script

set -e

echo "=========================================="
echo "RL-Based Adaptive Rendering Optimization"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is required but not installed."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is required but not installed."
    exit 1
fi

# Parse arguments
MODE=${1:-"setup"}

case $MODE in
    setup)
        echo "[1/4] Installing Node.js dependencies..."
        npm install
        
        echo "[2/4] Creating Python virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        
        echo "[3/4] Installing Python dependencies..."
        pip install -r requirements.txt
        
        echo "[4/4] Setup complete!"
        echo ""
        echo "Next steps:"
        echo "  1. Run web app: ./run.sh dev"
        echo "  2. Train RL agent: ./run.sh train"
        echo "  3. Run experiments: ./run.sh experiment"
        ;;
        
    dev)
        echo "Starting Next.js development server..."
        npm run dev
        ;;
        
    build)
        echo "Building Next.js application..."
        npm run build
        ;;
        
    train)
        echo "Training RL agent..."
        source venv/bin/activate 2>/dev/null || true
        cd src/env
        python train_ppo.py --mode train --episodes 5000 --save-dir checkpoints
        cd ../..
        echo "Training complete! Checkpoints saved in src/env/checkpoints/"
        ;;
        
    evaluate)
        echo "Evaluating trained agent..."
        source venv/bin/activate 2>/dev/null || true
        cd src/env
        python train_ppo.py --mode evaluate --checkpoint checkpoints/ppo_final.pt
        cd ../..
        ;;
        
    baselines)
        echo "Running baseline comparisons..."
        source venv/bin/activate 2>/dev/null || true
        cd src/env
        python train_ppo.py --mode baselines --n-episodes 100
        cd ../..
        ;;
        
    experiment)
        echo "Running quick experiments..."
        source venv/bin/activate 2>/dev/null || true
        cd src/env
        python experiment_runner.py --mode quick --n-episodes 50 --max-steps 500
        cd ../..
        echo "Results saved in src/env/results/"
        ;;
        
    experiment:full)
        echo "Running full experiment suite (this may take a while)..."
        source venv/bin/activate 2>/dev/null || true
        cd src/env
        python experiment_runner.py --mode full --n-episodes 100 --max-steps 1000
        cd ../..
        echo "Results saved in src/env/results/"
        ;;
        
    analyze)
        echo "Analyzing experiment results..."
        source venv/bin/activate 2>/dev/null || true
        cd src/env
        if [ -f "results/full_experiment_results.json" ]; then
            python analyze_results.py --results-file results/full_experiment_results.json --output-dir analysis
        elif [ -f "results/quick_experiment_results.json" ]; then
            python analyze_results.py --results-file results/quick_experiment_results.json --output-dir analysis
        else
            echo "No results found. Run experiments first."
            exit 1
        fi
        cd ../..
        echo "Analysis complete! Check src/env/analysis/"
        ;;
        
    test)
        echo "Testing API connections..."
        curl -s "https://fakestoreapi.com/products?limit=1" | head -c 100
        echo ""
        curl -s "https://dog.ceo/api/breeds/image/random" | head -c 100
        echo ""
        curl -s "https://api.thecatapi.com/v1/images/search" | head -c 100
        echo ""
        curl -s "https://www.themealdb.com/api/json/v1/1/random.php" | head -c 100
        echo ""
        curl -s "https://api.frankfurter.app/latest?from=USD" | head -c 100
        echo ""
        echo "API tests complete!"
        ;;
        
    *)
        echo "Usage: ./run.sh [command]"
        echo ""
        echo "Commands:"
        echo "  setup          - Install all dependencies"
        echo "  dev            - Start development server"
        echo "  build          - Build production version"
        echo "  train          - Train RL agent (5000 episodes)"
        echo "  evaluate       - Evaluate trained agent"
        echo "  baselines      - Run baseline comparisons"
        echo "  experiment     - Run quick experiments"
        echo "  experiment:full - Run full experiment suite"
        echo "  analyze        - Analyze results and generate report"
        echo "  test           - Test API connections"
        ;;
esac
