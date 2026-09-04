"""
Statistical Analysis for Rendering Optimization Experiments

This script performs statistical analysis on experiment results,
including significance tests, effect sizes, and visualization.
"""

import numpy as np
import json
import os
from typing import Dict, List, Tuple
from dataclasses import dataclass
import scipy.stats as stats
from scipy.stats import wilcoxon, ttest_rel, f_oneway, kruskal
import warnings
warnings.filterwarnings('ignore')


@dataclass
class StatisticalResult:
    """Results from statistical tests."""
    test_name: str
    statistic: float
    p_value: float
    effect_size: float
    effect_size_name: str
    significant: bool
    confidence_interval: Tuple[float, float]
    interpretation: str


class StatisticalAnalyzer:
    """Performs statistical analysis on experiment results."""
    
    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha
    
    def compare_two_strategies(
        self,
        strategy_a_rewards: List[float],
        strategy_b_rewards: List[float],
        name_a: str = "Strategy A",
        name_b: str = "Strategy B",
    ) -> StatisticalResult:
        """Compare two strategies using paired statistical tests."""
        
        # Ensure equal length
        min_len = min(len(strategy_a_rewards), len(strategy_b_rewards))
        a = np.array(strategy_a_rewards[:min_len])
        b = np.array(strategy_b_rewards[:min_len])
        
        # Check normality
        _, p_normal_a = stats.shapiro(a[:min(50, len(a))])  # Shapiro limited to 50 samples
        _, p_normal_b = stats.shapiro(b[:min(50, len(b))])
        normal = p_normal_a > 0.05 and p_normal_b > 0.05
        
        # Choose appropriate test
        if normal:
            # Paired t-test
            statistic, p_value = ttest_rel(a, b)
            test_name = "Paired t-test"
        else:
            # Wilcoxon signed-rank test
            try:
                statistic, p_value = wilcoxon(a, b)
                test_name = "Wilcoxon signed-rank"
            except ValueError:
                # If all differences are zero
                statistic, p_value = 0, 1
                test_name = "Wilcoxon signed-rank (degenerate)"
        
        # Effect size (Cohen's d)
        diff = a - b
        pooled_std = np.sqrt((np.var(a) + np.var(b)) / 2)
        if pooled_std > 0:
            cohens_d = np.mean(diff) / pooled_std
        else:
            cohens_d = 0
        
        # Interpret effect size
        abs_d = abs(cohens_d)
        if abs_d < 0.2:
            effect_name = "negligible"
        elif abs_d < 0.5:
            effect_name = "small"
        elif abs_d < 0.8:
            effect_name = "medium"
        else:
            effect_name = "large"
        
        # Confidence interval for mean difference
        sem = stats.sem(diff)
        ci = stats.t.interval(0.95, len(diff) - 1, loc=np.mean(diff), scale=sem)
        
        # Interpretation
        if p_value < self.alpha:
            if np.mean(a) > np.mean(b):
                interpretation = f"{name_a} significantly outperforms {name_b}"
            else:
                interpretation = f"{name_b} significantly outperforms {name_a}"
        else:
            interpretation = f"No significant difference between {name_a} and {name_b}"
        
        return StatisticalResult(
            test_name=test_name,
            statistic=statistic,
            p_value=p_value,
            effect_size=cohens_d,
            effect_size_name=effect_name,
            significant=p_value < self.alpha,
            confidence_interval=ci,
            interpretation=interpretation,
        )
    
    def compare_multiple_strategies(
        self,
        strategy_rewards: Dict[str, List[float]],
    ) -> Dict[str, StatisticalResult]:
        """Compare multiple strategies using ANOVA or Kruskal-Wallis."""
        
        # Ensure all arrays have same length
        min_len = min(len(rewards) for rewards in strategy_rewards.values())
        arrays = {name: np.array(rewards[:min_len]) for name, rewards in strategy_rewards.items()}
        
        # Check normality for all groups
        all_normal = True
        for arr in arrays.values():
            _, p = stats.shapiro(arr[:min(50, len(arr))])
            if p < 0.05:
                all_normal = False
                break
        
        # Choose test
        if all_normal:
            # One-way ANOVA
            f_stat, p_value = f_oneway(*arrays.values())
            test_name = "One-way ANOVA"
            statistic_name = "F-statistic"
        else:
            # Kruskal-Wallis test
            h_stat, p_value = kruskal(*arrays.values())
            test_name = "Kruskal-Wallis"
            statistic_name = "H-statistic"
            f_stat = h_stat
        
        # Effect size (eta-squared for ANOVA, epsilon-squared for Kruskal-Wallis)
        all_values = np.concatenate(list(arrays.values()))
        grand_mean = np.mean(all_values)
        
        ss_between = sum(len(arr) * (np.mean(arr) - grand_mean) ** 2 for arr in arrays.values())
        ss_total = np.sum((all_values - grand_mean) ** 2)
        
        if ss_total > 0:
            eta_squared = ss_between / ss_total
        else:
            eta_squared = 0
        
        # Interpret effect size
        if eta_squared < 0.01:
            effect_name = "negligible"
        elif eta_squared < 0.06:
            effect_name = "small"
        elif eta_squared < 0.14:
            effect_name = "medium"
        else:
            effect_name = "large"
        
        # Overall interpretation
        if p_value < self.alpha:
            interpretation = "Significant differences exist between strategies"
        else:
            interpretation = "No significant differences between strategies"
        
        return {
            "overall": StatisticalResult(
                test_name=test_name,
                statistic=f_stat,
                p_value=p_value,
                effect_size=eta_squared,
                effect_size_name=effect_name,
                significant=p_value < self.alpha,
                confidence_interval=(0, 0),  # Not applicable for omnibus test
                interpretation=interpretation,
            )
        }
    
    def post_hoc_pairwise(
        self,
        strategy_rewards: Dict[str, List[float]],
    ) -> Dict[Tuple[str, str], StatisticalResult]:
        """Perform post-hoc pairwise comparisons with Bonferroni correction."""
        
        strategies = list(strategy_rewards.keys())
        n_comparisons = len(strategies) * (len(strategies) - 1) // 2
        adjusted_alpha = self.alpha / n_comparisons
        
        results = {}
        
        for i in range(len(strategies)):
            for j in range(i + 1, len(strategies)):
                name_a = strategies[i]
                name_b = strategies[j]
                
                result = self.compare_two_strategies(
                    strategy_rewards[name_a],
                    strategy_rewards[name_b],
                    name_a,
                    name_b,
                )
                
                # Adjust p-value for multiple comparisons
                result.p_value = min(result.p_value * n_comparisons, 1.0)
                result.significant = result.p_value < self.alpha
                
                results[(name_a, name_b)] = result
        
        return results
    
    def calculate_confidence_intervals(
        self,
        rewards: List[float],
        confidence: float = 0.95,
    ) -> Tuple[float, float, float]:
        """Calculate mean and confidence interval."""
        arr = np.array(rewards)
        mean = np.mean(arr)
        sem = stats.sem(arr)
        ci = stats.t.interval(confidence, len(arr) - 1, loc=mean, scale=sem)
        
        return mean, ci[0], ci[1]


class ResultsVisualizer:
    """Generates visualizations for experiment results."""
    
    def __init__(self, output_dir: str = "figures"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def plot_learning_curves(
        self,
        rl_rewards: List[float],
        baseline_rewards: Dict[str, List[float]],
        window: int = 50,
        save_path: str = "learning_curves.png",
    ):
        """Plot learning curves with moving average."""
        try:
            import matplotlib.pyplot as plt
            
            if not rl_rewards and not baseline_rewards:
                print("Skipping learning curves plot: no data")
                return
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # RL learning curve
            if rl_rewards and len(rl_rewards) > window:
                rl_smooth = np.convolve(rl_rewards, np.ones(window)/window, mode='valid')
                ax.plot(rl_smooth, label='RL-Agent', linewidth=2, color='blue')
            elif rl_rewards:
                ax.plot(rl_rewards, label='RL-Agent', linewidth=2, color='blue')
            
            # Baseline averages (horizontal lines)
            colors = ['red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
            for (name, rewards), color in zip(baseline_rewards.items(), colors):
                if rewards:
                    avg = np.mean(rewards)
                    ax.axhline(y=avg, label=f'{name} (avg)', linestyle='--', color=color, alpha=0.7)
            
            ax.set_xlabel('Episode')
            ax.set_ylabel('Reward')
            ax.set_title('Learning Curves: RL-Agent vs Baselines')
            ax.legend(loc='lower right')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, save_path), dpi=150)
            plt.close()
            
            print(f"Saved learning curves to {save_path}")
            
        except ImportError:
            print("matplotlib not available, skipping visualization")
    
    def plot_strategy_distribution(
        self,
        strategy_dist: Dict[str, float],
        save_path: str = "strategy_distribution.png",
    ):
        """Plot strategy distribution pie chart."""
        try:
            import matplotlib.pyplot as plt
            
            # Filter out zero values and empty distributions
            filtered_dist = {k: v for k, v in strategy_dist.items() if v > 0}
            
            if not filtered_dist:
                print(f"Skipping strategy distribution plot: no data")
                return
            
            fig, ax = plt.subplots(figsize=(8, 8))
            
            labels = list(filtered_dist.keys())
            sizes = list(filtered_dist.values())
            colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
            
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                colors=colors,
                autopct='%1.1f%%',
                startangle=90,
            )
            
            ax.set_title('RL-Agent Strategy Distribution')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, save_path), dpi=150)
            plt.close()
            
            print(f"Saved strategy distribution to {save_path}")
            
        except ImportError:
            print("matplotlib not available, skipping visualization")
    
    def plot_performance_comparison(
        self,
        results: Dict[str, Dict[str, float]],
        metric: str = "mean_latency",
        save_path: str = "performance_comparison.png",
    ):
        """Plot bar chart comparing strategies on a metric."""
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            strategies = list(results.keys())
            values = [results[s].get(metric, 0) for s in strategies]
            
            bars = ax.bar(strategies, values, color=plt.cm.viridis(np.linspace(0.2, 0.8, len(strategies))))
            
            ax.set_xlabel('Strategy')
            ax.set_ylabel(metric.replace('_', ' ').title())
            ax.set_title(f'Strategy Comparison: {metric.replace("_", " ").title()}')
            ax.tick_params(axis='x', rotation=45)
            
            # Add value labels on bars
            for bar, value in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    f'{value:.2f}',
                    ha='center',
                    va='bottom',
                )
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, save_path), dpi=150)
            plt.close()
            
            print(f"Saved performance comparison to {save_path}")
            
        except ImportError:
            print("matplotlib not available, skipping visualization")
    
    def plot_boxplots(
        self,
        strategy_rewards: Dict[str, List[float]],
        save_path: str = "reward_boxplots.png",
    ):
        """Plot boxplots of rewards for each strategy."""
        try:
            import matplotlib.pyplot as plt
            
            # Filter out empty lists
            filtered = {k: v for k, v in strategy_rewards.items() if v}
            
            if not filtered:
                print("Skipping boxplots: no data")
                return
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            strategies = list(filtered.keys())
            data = [filtered[s] for s in strategies]
            
            bp = ax.boxplot(data, labels=strategies, patch_artist=True)
            
            colors = plt.cm.Set3(np.linspace(0, 1, len(strategies)))
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
            
            ax.set_xlabel('Strategy')
            ax.set_ylabel('Reward')
            ax.set_title('Reward Distribution by Strategy')
            ax.tick_params(axis='x', rotation=45)
            ax.grid(True, alpha=0.3, axis='y')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, save_path), dpi=150)
            plt.close()
            
            print(f"Saved boxplots to {save_path}")
            
        except ImportError:
            print("matplotlib not available, skipping visualization")


def generate_statistical_report(
    results: Dict[str, List[float]],
    output_file: str = "statistical_report.md",
):
    """Generate a comprehensive statistical report."""
    
    analyzer = StatisticalAnalyzer(alpha=0.05)
    
    report = "# Statistical Analysis Report\n\n"
    report += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report += f"**Significance Level (α):** 0.05\n\n"
    
    # Descriptive statistics
    report += "## 1. Descriptive Statistics\n\n"
    report += "| Strategy | N | Mean | Std | Min | Max | Median | P25 | P75 |\n"
    report += "|----------|---|------|-----|-----|-----|--------|-----|-----|\n"
    
    for name, rewards in results.items():
        arr = np.array(rewards)
        report += f"| {name} | {len(arr)} | {np.mean(arr):.4f} | {np.std(arr):.4f} | {np.min(arr):.4f} | {np.max(arr):.4f} | {np.median(arr):.4f} | {np.percentile(arr, 25):.4f} | {np.percentile(arr, 75):.4f} |\n"
    
    # Normality tests
    report += "\n## 2. Normality Tests (Shapiro-Wilk)\n\n"
    report += "| Strategy | W-statistic | p-value | Normal (α=0.05) |\n"
    report += "|----------|-------------|---------|------------------|\n"
    
    for name, rewards in results.items():
        arr = np.array(rewards[:min(50, len(rewards))])
        w_stat, p_value = stats.shapiro(arr)
        normal = "Yes" if p_value > 0.05 else "No"
        report += f"| {name} | {w_stat:.4f} | {p_value:.4f} | {normal} |\n"
    
    # Overall comparison
    report += "\n## 3. Overall Comparison (Omnibus Test)\n\n"
    
    overall_result = analyzer.compare_multiple_strategies(results)
    result = overall_result["overall"]
    
    report += f"- **Test:** {result.test_name}\n"
    report += f"- **Statistic:** {result.statistic:.4f}\n"
    report += f"- **p-value:** {result.p_value:.6f}\n"
    report += f"- **Effect Size (η²):** {result.effect_size:.4f} ({result.effect_size_name})\n"
    report += f"- **Significant:** {'Yes' if result.significant else 'No'}\n"
    report += f"- **Interpretation:** {result.interpretation}\n"
    
    # Pairwise comparisons
    report += "\n## 4. Pairwise Comparisons (Bonferroni-corrected)\n\n"
    report += "| Comparison | Test | Statistic | p-value | Effect Size | Significant | Interpretation |\n"
    report += "|------------|------|-----------|---------|-------------|-------------|----------------|\n"
    
    pairwise_results = analyzer.post_hoc_pairwise(results)
    
    for (name_a, name_b), result in pairwise_results.items():
        report += f"| {name_a} vs {name_b} | {result.test_name} | {result.statistic:.4f} | {result.p_value:.6f} | {result.effect_size:.4f} ({result.effect_size_name}) | {'Yes' if result.significant else 'No'} | {result.interpretation} |\n"
    
    # Confidence intervals
    report += "\n## 5. 95% Confidence Intervals\n\n"
    report += "| Strategy | Mean | Lower CI | Upper CI |\n"
    report += "|----------|------|----------|----------|\n"
    
    for name, rewards in results.items():
        mean, lower, upper = analyzer.calculate_confidence_intervals(rewards)
        report += f"| {name} | {mean:.4f} | {lower:.4f} | {upper:.4f} |\n"
    
    # Effect sizes for RL vs each baseline
    report += "\n## 6. RL-Agent vs Baselines (Cohen's d)\n\n"
    
    if "RL-Agent" in results:
        rl_rewards = results["RL-Agent"]
        report += "| Baseline | Cohen's d | Effect Size | Interpretation |\n"
        report += "|----------|-----------|-------------|----------------|\n"
        
        for name, rewards in results.items():
            if name != "RL-Agent":
                result = analyzer.compare_two_strategies(rl_rewards, rewards, "RL-Agent", name)
                report += f"| {name} | {result.effect_size:.4f} | {result.effect_size_name} | {result.interpretation} |\n"
    
    # Summary
    report += "\n## 7. Summary\n\n"
    
    if "RL-Agent" in results:
        rl_mean = np.mean(results["RL-Agent"])
        best_baseline = max(
            [(name, np.mean(rewards)) for name, rewards in results.items() if name != "RL-Agent"],
            key=lambda x: x[1],
        )
        
        improvement = ((rl_mean - best_baseline[1]) / abs(best_baseline[1]) * 100) if best_baseline[1] != 0 else 0
        
        report += f"- **RL-Agent Mean Reward:** {rl_mean:.4f}\n"
        report += f"- **Best Baseline:** {best_baseline[0]} ({best_baseline[1]:.4f})\n"
        report += f"- **Improvement over Best Baseline:** {improvement:.2f}%\n"
        
        if improvement > 0:
            report += f"\nThe RL-Agent outperforms all baselines by {improvement:.2f}% on average.\n"
        else:
            report += f"\nThe RL-Agent does not outperform the best baseline ({best_baseline[0]}).\n"
    
    # Write report
    with open(output_file, 'w') as f:
        f.write(report)
    
    print(f"\nStatistical report saved to {output_file}")
    
    return report


from datetime import datetime


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze experiment results")
    parser.add_argument("--results-file", type=str, required=True, help="Path to results JSON")
    parser.add_argument("--output-dir", type=str, default="analysis", help="Output directory")
    
    args = parser.parse_args()
    
    # Load results
    with open(args.results_file, 'r') as f:
        results = json.load(f)
    
    # Convert to numpy arrays
    for strategy in results:
        if isinstance(results[strategy], list):
            if results[strategy] and isinstance(results[strategy][0], dict):
                # Extract rewards from experiment results
                results[strategy] = [r['mean_reward'] for r in results[strategy]]
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate statistical report
    report = generate_statistical_report(
        results,
        os.path.join(args.output_dir, "statistical_report.md"),
    )
    
    # Generate visualizations
    visualizer = ResultsVisualizer(args.output_dir)
    
    if 'RL-Agent' in results:
        # Extract baseline rewards
        baseline_rewards = {k: v for k, v in results.items() if k != 'RL-Agent'}
        
        visualizer.plot_learning_curves(
            results['RL-Agent'],
            baseline_rewards,
            save_path="learning_curves.png",
        )
        
        # Extract strategy distribution from RL-Agent experiment results
        rl_results = results['RL-Agent']
        strategy_dist = {}
        if isinstance(rl_results, list) and rl_results:
            for exp in rl_results:
                if isinstance(exp, dict) and 'strategy_distribution' in exp:
                    for strat, count in exp['strategy_distribution'].items():
                        strategy_dist[strat] = strategy_dist.get(strat, 0) + count
        
        if strategy_dist:
            # Normalize to percentages
            total = sum(strategy_dist.values())
            strategy_dist = {k: v/total for k, v in strategy_dist.items()}
        
        visualizer.plot_strategy_distribution(
            strategy_dist,
            save_path="strategy_distribution.png",
        )
    
    visualizer.plot_boxplots(results, save_path="reward_boxplots.png")
    
    print("\nAnalysis complete!")
