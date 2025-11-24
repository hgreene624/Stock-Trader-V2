# Parameter Complexity and Overfitting in Trading Strategies

**Date**: November 23, 2025
**Context**: Research into best practices for parameter optimization to avoid overfitting

---

## Summary

There is **no magic number** for maximum parameters. The relationship between parameters and overfitting depends on:
- Amount of training data available
- Ratio of training to validation data
- Correlation between parameters

The key principle is: **more parameters require proportionally more data**.

---

## Key Takeaway

**Rule of thumb**: For N parameters, use at least (N+1):1 training-to-validation ratio.

| Parameters | Recommended Train:Val Ratio |
|------------|----------------------------|
| 1 | 2:1 |
| 2 | 3:1 |
| 3 | 4:1 |
| 8 | 9:1 |

With 5 years of data (2020-2024) and 8 parameters, the 70/30 auto-split gives ~2.3:1 ratio - far below the recommended 9:1. This explains why our EA overfit.

---

## Sources and Analysis

### 1. Avoiding Over-fitting in Trading Strategy (MQL5)

**URL**: https://www.mql5.com/en/blogs/post/756386

**Synopsis**: Practical guide from MQL5 community on building optimization processes that avoid overfitting. Focuses on walk-forward analysis and data ratios.

**Key Takeaways**:
- "The data ratio between Initial Optimization and Walk-forward phases is 2:1 when optimizing a single parameter, 3:1 for two parameters, and 4:1 for three parameters"
- Walk-forward analysis is essential - optimize on one period, validate on the next
- Out-of-sample testing must be truly blind (not used in any optimization decisions)

**My Interpretation**: This is the most actionable source. The ratio guideline directly addresses our question - there's no hard parameter limit, but there IS a data requirement that scales with complexity.

---

### 2. The Probability of Backtest Overfitting (PBO)

**URL**: https://medium.com/balaena-quant-insights/the-probability-of-backtest-overfitting-pbo-9ba0ac7fb456

**Synopsis**: Academic approach to quantifying overfitting risk. Introduces the Probability of Backtest Overfitting (PBO) metric from research by Bailey, Borwein, López de Prado, and Zhu.

**Key Takeaways**:
- PBO measures the probability that a strategy selected based on in-sample performance will underperform out-of-sample
- "The more degrees of freedom we allow, the higher the risk that one trial will look good purely by chance"
- Overfitting probability increases with: number of parameters, number of trials, and data mining breadth
- Provides statistical framework rather than rules of thumb

**My Interpretation**: More rigorous than simple ratios, but harder to implement. The core insight is that overfitting is probabilistic - more parameters = higher probability of finding spurious patterns.

---

### 3. How to Spot Backtest Overfitting (David Bailey)

**URL**: https://www.davidhbailey.com/dhbtalks/battle-quants.pdf

**Synopsis**: Presentation slides from David Bailey (Lawrence Berkeley National Laboratory) on detecting and avoiding backtest overfitting. Part of academic research on quantitative finance pitfalls.

**Key Takeaways**:
- References Fermi's famous quote: "With four parameters I can fit an elephant, and with five I can make him wiggle his trunk"
- Introduces Deflated Sharpe Ratio (DSR) which adjusts for multiple testing
- "A higher degrees of freedom necessitates a larger sample size during backtesting to achieve statistical significance"
- Emphasizes that high Sharpe ratios from backtests are almost always overstated

**My Interpretation**: The Fermi quote is why "5 parameters" gets thrown around as a limit - but it's illustrative, not prescriptive. The real insight is about sample size scaling with complexity.

---

### 4. The Three Kinds of (Over) Fitting

**URL**: https://qoppac.blogspot.com/2015/11/the-three-kinds-of-overfitting.html

**Synopsis**: Blog post by Rob Carver (author of "Systematic Trading") categorizing different types of overfitting and how to address each.

**Key Takeaways**:
- Three types: in-sample, out-of-sample, and structural overfitting
- "Your guiding principle should be Einstein's razor: 'Everything should be kept as simple as possible, but no simpler'"
- Less degrees of freedom = less chance for overfitting
- Recommends regularization and parameter selection to reduce complexity

**My Interpretation**: Adds nuance that overfitting isn't just about parameter count - it's also about model structure and how validation is performed. Simpler is better, but there's a floor below which you can't capture the signal.

---

### 5. Avoiding Backtesting Overfitting by Covariance-Penalties

**URL**: https://arxiv.org/abs/1905.05023

**Synopsis**: Academic paper proposing a mathematical correction for overfitting based on the number of parameters and data used.

**Key Takeaways**:
- Proposes "Covariance-Penalty Correction" to adjust risk metrics given parameter count
- Mathematically formalizes the relationship between parameters and required data
- Provides tools to estimate true out-of-sample performance from in-sample results

**My Interpretation**: Most rigorous approach but requires implementation. Could be used to automatically adjust reported metrics based on parameter complexity.

---

### 6. 9 Mistakes Quants Make that Cause Backtests to Lie

**URL**: https://augmentedtrader.wordpress.com/2015/04/27/9-mistakes-quants-make-that-cause-backtests-to-lie/

**Synopsis**: Practical list of common backtesting errors from quantitative trading practitioners.

**Key Takeaways**:
- "As the degrees of freedom of the model increase, overfitting occurs when in-sample market predictions error decreases and out-of-sample prediction error increases"
- Degrees of freedom include: number of factors, number of parameters, and number of optimization trials
- Common mistake: optimizing on all available data without holdout

**My Interpretation**: Directly describes what happened to us - we optimized on all data, saw great in-sample performance, and got poor out-of-sample results. This is textbook overfitting.

---

## Application to Our System

### What We Did Wrong

1. **8 parameters with 5 years of data**
   - Needed: 9:1 ratio = 4.5 years train, 0.5 years validate
   - Actually used: 5:0 ratio (all data for training)

2. **No validation holdout**
   - Optimized on full 2020-2024 period
   - No unseen data to detect overfitting

3. **Ignored the Fermi warning**
   - With 8 parameters, we can fit any pattern
   - BPS 1.44 was "fitting the elephant"

### What the EA Now Does

1. **Automatic 70/30 split** - Forces validation holdout
2. **Reports both train and validation scores** - Shows degradation
3. **Warns about degradation >50%** - Flags severe overfitting
4. **Shows recommended data ratio** - Informs about complexity cost

### Remaining Improvements

1. **Calculate actual data ratio** and warn if insufficient
2. **Implement Deflated Sharpe Ratio** for more accurate metrics
3. **Add PBO calculation** to quantify overfitting probability
4. **Support explicit train/validate/test splits** in experiment config

---

## Conclusion

The "5 parameter max" is a simplification of a more nuanced principle:

**Overfitting risk scales with parameters, and must be offset by proportionally more data.**

For practical purposes:
- Use the (N+1):1 ratio guideline
- Always validate on held-out data
- Be skeptical of results that seem too good
- Prefer simpler models when performance is similar

---

## References

1. MQL5 Community. (2024). "Avoiding Over-fitting in Trading Strategy (Part 2): A Guide to Building Optimization Processes." https://www.mql5.com/en/blogs/post/756386

2. Ling, L. "The Probability of Backtest Overfitting (PBO)." Balaena Quant Insights. https://medium.com/balaena-quant-insights/the-probability-of-backtest-overfitting-pbo-9ba0ac7fb456

3. Bailey, D.H. "How to Spot Backtest Overfitting." Lawrence Berkeley National Laboratory. https://www.davidhbailey.com/dhbtalks/battle-quants.pdf

4. Carver, R. (2015). "The three kinds of (over) fitting." This Blog is Systematic. https://qoppac.blogspot.com/2015/11/the-three-kinds-of-overfitting.html

5. Coqueret, G., & Milhau, V. (2019). "Avoiding Backtesting Overfitting by Covariance-Penalties." arXiv:1905.05023. https://arxiv.org/abs/1905.05023

6. The Augmented Trader. (2015). "9 Mistakes Quants Make that Cause Backtests to Lie." https://augmentedtrader.wordpress.com/2015/04/27/9-mistakes-quants-make-that-cause-backtests-to-lie/
