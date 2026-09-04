# Q2 Journal Review Report
## Manuscript: "Adaptive Rendering Optimization via Reinforcement Learning"

**Reviewer:** Independent Review (Simulated Q2 Review)  
**Target Venue:** Journal of Web Engineering (Q2) or Software: Practice and Experience (Q2)  
**Date:** September 4, 2026

---

## Overall Assessment

**Recommendation: Major Revisions Required**

The paper presents an interesting application of RL to web rendering optimization. However, there are significant issues that must be addressed before publication. The work has potential but currently has gaps in novelty, methodology, and presentation that would likely lead to rejection at a Q2 venue.

---

## Summary

The paper proposes RenderRL, a PPO-based framework for adaptive rendering strategy selection in React applications. The authors conduct 2,400 experiments across 10 strategies and 80 conditions, showing that RL achieves medium-to-large effect sizes compared to weaker baselines but is outperformed by SSG-Only.

---

## Detailed Review

### 1. NOVELTY AND CONTRIBUTION (Score: 3/10)

**Strengths:**
- Interesting application domain
- Open-source framework release

**Weaknesses:**

1. **Incremental contribution:** The paper applies standard PPO to a new domain. The novelty is in the application, not the methodology. Q2 journals expect at least one of:
   - Novel algorithm
   - Novel theoretical insight
   - Significant empirical finding
   - Novel formulation

2. **Unclear problem framing:** The paper oscillates between:
   - "RL beats baselines" (now abandoned)
   - "RL provides variance reduction" (not supported by data)
   - "RL discovers interpretable policies" (weakest contribution)
   
   **Fix needed:** Define ONE clear contribution and build entire paper around it.

3. **Contribution #5 is weak:** "Open-source framework" is not a research contribution. It's a nice-to-have.

4. **No comparison to related RL work:** The paper doesn't compare to existing RL-for-systems work. What makes this different from RL for caching, scheduling, or database optimization?

**Recommendation:** Reframe as "empirical study of RL for rendering" with focus on **policy interpretability** and **when adaptive strategies help**.

---

### 2. METHODOLOGY (Score: 4/10)

**Strengths:**
- Formal MDP formulation
- Reasonable hyperparameters

**Weaknesses:**

1. **Simulated environment:** All experiments use a simulated environment, not real systems. This is a major limitation not sufficiently discussed.

   **Fix needed:** 
   - Acknowledge this prominently
   - Add analysis of simulation fidelity
   - Discuss what would change in real deployment

2. **Reward function is arbitrary:**
   ```
   R = 0.5·R_perf + 0.2·R_resource + 0.2·R_cache + 0.1·R_penalty
   ```
   - Why these weights?
   - No sensitivity analysis (ablation study is simulated)
   - No theoretical justification

3. **State space is under-specified:**
   - 15 dimensions listed, but only 12 are clearly defined
   - "content_type_embedding" (4D) is vague
   - "user_engagement" is not defined

4. **Missing details:**
   - How are components actually rendered? (simulated)
   - What's the actual rendering pipeline?
   - How is the environment initialized?

5. **Ablation study is simulated, not real:**
   - Table 5 shows "simulated" performance for different weights
   - This is not a proper ablation study
   - Need to actually train with different weights and report results

**Recommendation:** Either validate on real systems or acknowledge simulation limitations prominently.

---

### 3. EXPERIMENTAL DESIGN (Score: 5/10)

**Strengths:**
- Large number of experiments (2,400)
- Multiple seeds
- Statistical analysis

**Weaknesses:**

1. **Baselines are weak:**
   - All baselines are "Only" strategies (CSR-Only, SSR-Only, etc.)
   - Missing realistic baselines:
     - Next.js defaults (already adaptive)
     - Developer heuristics (SSG for static, SSR for dynamic)
     - Simple adaptive rules (if latency > threshold, switch)

2. **2,400 experiments is misleading:**
   - 10 strategies × 80 conditions × 3 seeds = 2,400
   - But the RL agent is ONE strategy, so it's really:
     - 1 RL agent × 80 conditions × 3 seeds = 240 runs
     - 9 baselines × 80 conditions × 3 seeds = 2,160 runs
   - This inflates the apparent rigor

3. **Statistical analysis issues:**
   - Kruskal-Wallis η² = 0.663 is suspiciously high (typically 0.14-0.34 for large effects)
   - Mann-Whitney U is inappropriate for comparing means (use t-test or bootstrap)
   - Bonferroni correction is overly conservative (consider Holm or FDR)
   - No power analysis

4. **Metrics are unclear:**
   - "Reward" is the primary metric, but what does it measure?
   - How does reward relate to real-world metrics (load time, TTI)?
   - Why is latency a separate metric if it's in the reward?

5. **Missing experimental details:**
   - How many episodes per experiment?
   - What's the training procedure for baselines?
   - How are results averaged across seeds?

**Recommendation:** Add real baselines, clarify metrics, fix statistical analysis.

---

### 4. RESULTS AND ANALYSIS (Score: 4/10)

**Strengths:**
- Effect size analysis is good
- Network degradation analysis is insightful

**Weaknesses:**

1. **Main result undermines the paper:**
   - SSG-Only beats RL-Agent by 26.7%
   - This is not mentioned in the abstract
   - Should be prominently disclosed

2. **Variance reduction claim is false:**
   - SSG-Only has σ = 19.83
   - RL-Agent has σ = 23.90
   - RL-Agent has HIGHER variance, not lower

3. **Tables are inconsistent:**
   - Table 4 appears twice (variance and effect sizes)
   - Table 5 appears twice (strategy distribution and ablation)
   - Numbers don't always match between text and tables

4. **Figures are not referenced in text:**
   - 10 figures exist but only some are mentioned
   - No figure numbers in captions
   - Figures should be referenced in order

5. **Key findings are under-explained:**
   - Why does RL-Agent prefer PARTIAL (35.3%)?
   - What's special about this combination?
   - How does this compare to developer intuition?

**Recommendation:** Fix inconsistencies, reframe findings, explain key results.

---

### 5. WRITING AND PRESENTATION (Score: 5/10)

**Strengths:**
- Clear structure
- Good use of tables
- Proper academic format

**Weaknesses:**

1. **Language issues:**
   - Mixed Chinese/English (line 77: "最早的 CSR frameworks")
   - Typos (line 331: "混合策略" should be English)
   - Inconsistent terminology

2. **Structure issues:**
   - Related work is too brief (1.5 pages)
   - Methodology lacks depth
   - Discussion is repetitive

3. **Citation issues:**
   - [15] has author "G. xxc663" (invalid)
   - [24] duplicates [9]
   - Some citations are websites, not papers
   - Missing key references (e.g., WebPerf papers)

4. **Missing sections:**
   - No Threats to Validity
   - No Reproducibility checklist
   - No Data Availability statement

5. **Appendix is incomplete:**
   - Table C1 shows "..." instead of full conditions
   - No code availability information

**Recommendation:** Fix language, add missing sections, verify all citations.

---

### 6. FIGURES (Score: 6/10)

**Strengths:**
- Professional appearance
- PDF + PNG formats
- 300 DPI

**Weaknesses:**

1. **Not all figures are referenced:**
   - fig9_ablation and fig10_effect_sizes not in text
   - Some figures lack captions

2. **Figure quality issues:**
   - Small font sizes (may not be readable)
   - Inconsistent color schemes
   - Some figures are too complex

3. **Missing figures:**
   - No comparison to real baselines
   - No scalability results with real components
   - No production deployment results

**Recommendation:** Reference all figures, improve readability, add missing figures.

---

## Specific Issues to Fix

### Critical (Must Fix)

1. **Abstract line 13:** Remove "Variance-Aware" from title (variance is not reduced)
2. **Line 289:** η² = 0.36 vs 0.663 - inconsistent (which is correct?)
3. **Table numbering:** Fix duplicate Table 4 and Table 5
4. **Variance claim:** Remove or correct "35% variance reduction" (it's false)
5. **Chinese text:** Remove all Chinese characters
6. **Citation [15]:** Fix "G. xxc663" to real author name
7. **Citation [24]:** Remove duplicate

### Important (Should Fix)

8. **Add real baselines:** Next.js defaults, developer heuristics
9. **Clarify simulation:** Add "Simulation Limitations" section
10. **Fix statistical tests:** Use appropriate tests (bootstrap, t-test)
11. **Add power analysis:** Show experiments were adequately powered
12. **Add Threats to Validity section**
13. **Add Reproducibility information**

### Nice to Have

14. **Add real-world validation** (even small-scale)
15. **Add sensitivity analysis** for reward weights (actually train, not simulate)
16. **Compare to more recent RL-for-systems work**
17. **Add theoretical analysis** of when adaptation helps

---

## Revision Plan

### Phase 1: Critical Fixes (1-2 days)
1. Fix title (remove "Variance-Aware")
2. Fix all language issues
3. Fix table numbering
4. Remove false claims
5. Fix citations
6. Add missing sections

### Phase 2: Important Fixes (3-5 days)
1. Add real baselines (even if simulated)
2. Add simulation limitations section
3. Fix statistical analysis
4. Add power analysis
5. Add Threats to Validity

### Phase 3: Improvements (5-7 days)
1. Add small real-world validation
2. Add sensitivity analysis
3. Improve figures
4. Final proofreading

---

## Estimated Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| Phase 1 | 1-2 days | Critical fixes |
| Phase 2 | 3-5 days | Important fixes |
| Phase 3 | 5-7 days | Improvements |
| **Total** | **9-14 days** | |

---

## Risk Assessment

**Probability of Acceptance (Current):** 10-20%  
**Probability of Acceptance (After Phase 1):** 30-40%  
**Probability of Acceptance (After Phase 2):** 50-60%  
**Probability of Acceptance (After Phase 3):** 60-70%

---

## Final Recommendation

The paper has potential but needs significant revision. The key issue is **novelty** - the current contribution is incremental. To improve acceptance odds:

1. **Reframe as empirical study** with focus on policy interpretability
2. **Acknowledge limitations** honestly
3. **Add real baselines** and comparisons
4. **Fix all methodological issues**

With these changes, the paper could be suitable for a Q2 venue like Journal of Web Engineering or Software: Practice and Experience.

---

*Review completed on September 4, 2026*
