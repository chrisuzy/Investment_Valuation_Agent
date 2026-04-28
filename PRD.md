1\. 全局数据字典与总控文档

\# Main\_PRD\_Global\_Dictionary.md

\# 投资估值自动化系统 - 全局数据字典与总架构



\## 1. 核心设计原则

1\. \*\*变量强类型化\*\*：所有子模块必须严格引用本字典中定义的变量名，绝对禁止使用任何变体。

2\. \*\*测试驱动开发 (TDD)\*\*：每个模块开发完成后，Claude Code 必须使用 Capital IQ 插件获取真实公司（如 AAPL 或 MSFT）的数据，执行模块末尾的测试用例并核对结果。



\## 2. 全局变量数据字典 (Global Data Dictionary)



\### A. 宏观与风险变量 (Macro \& Risk Inputs)

\* `Risk\_Free\_Rate`: 无风险利率 (十/二三十年期国债收益率)

\* `Equity\_Risk\_Premium`: 股权风险溢价 (ERP)

\* `Country\_Risk\_Premium`: 国家风险溢价 (CRP)

\* `Tax\_Rate\_Marginal`: 边际税率/法定税率 (用于折现率和利息税盾)

\* `Tax\_Rate\_Effective`: 有效税率 (用于当前收益计算)

\* `Default\_Spread`: 公司债务违约利差



\### B. 财务原始输入变量 (Raw Financial Inputs from Capital IQ)

\* `Revenues`: 营业收入

\* `EBIT`: 息税前利润 (未调整)

\* `EBITDA`: 息税折旧摊销前利润 (未调整)

\* `Net\_Income`: 净利润 (未调整)

\* `Interest\_Expense`: 利息费用

\* `CapEx`: 资本支出 (Capital Expenditures)

\* `D\_A`: 折旧与摊销 (Depreciation \& Amortization)

\* `Noncash\_WC`: 非现金营运资本

\* `Change\_in\_Noncash\_WC`: 非现金营运资本变动

\* `Net\_Debt\_Issued`: 净债务发行 (新发债务 - 偿还债务)

\* `Cash\_and\_Marketable\_Securities`: 现金及交易性金融资产

\* `BV\_Equity`: 股权账面价值 (Book Value of Equity)

\* `BV\_Debt`: 债务账面价值 (Book Value of Debt)

\* `MV\_Equity`: 股权市场价值 (市值)

\* `MV\_Debt`: 债务市场价值

\* `Shares\_Outstanding`: 发行在外基础股数 (Primary shares outstanding)



\### C. 报表调整专用输入变量 (Inputs for Adjustments)

\* `Amortization\_Period\_n`: 研发费用摊销年限 (通常为3, 5, 或10年)

\* `R\_and\_D\_Expense\_Current`: 当期研发费用

\* `R\_and\_D\_Expense\_Past\_t`: 过去第 t 年的研发费用 ($t = 1, 2, ..., n$)

\* `Operating\_Lease\_Expense\_Current`: 当期经营租赁费用

\* `Operating\_Lease\_Commitment\_t`: 未来第 t 年的租赁承诺金额



\### D. 调整后中间与输出变量 (Adjusted \& Calculated Variables)

\* `Unamortized\_R\_and\_D`: 未摊销研发资产价值

\* `Amortization\_R\_and\_D`: 研发资产本期摊销额

\* `PV\_of\_Operating\_Leases`: 经营租赁的债务现值

\* `Adjusted\_EBIT`: 调整后息税前利润

\* `Adjusted\_Net\_Income`: 调整后净利润

\* `Adjusted\_BV\_Equity`: 调整后股权账面价值

\* `Adjusted\_MV\_Debt`: 调整后债务市场价值

\* `Adjusted\_Invested\_Capital`: 调整后投入资本

\* `Reinvestment\_Firm`: 公司总再投资额

\* `Reinvestment\_Equity`: 股权总再投资额

\* `FCFF`: 公司自由现金流

\* `FCFE`: 股权自由现金流

\* `ROIC`: 投入资本回报率

\* `ROE`: 净资产收益率

\* `RIR\_Firm`: 公司再投资率 (Reinvestment Rate)

\* `RIR\_Equity`: 股权再投资率 (Equity Reinvestment Rate)



\### E. 资本成本与估值变量 (Cost of Capital \& Valuation)

\* `Beta\_U`: 无杠杆 Beta

\* `Beta\_L`: 杠杆 Beta

\* `D\_E\_Ratio`: 市场价值债务股权比 (Adjusted\_MV\_Debt / MV\_Equity)

\* `Cost\_of\_Equity`: 股权资本成本

\* `Cost\_of\_Debt\_PreTax`: 税前债务成本

\* `Cost\_of\_Debt\_AfterTax`: 税后债务成本

\* `WACC`: 加权平均资本成本

\* `Expected\_Growth\_EBIT`: 预期 EBIT 增长率

\* `Stable\_Growth\_Rate`: 永续稳定增长率

\* `Terminal\_Value\_Firm`: 公司终值

\* `Value\_of\_Operating\_Assets`: 核心运营资产价值

\* `Value\_of\_Equity`: 股权总内在价值

\* `Value\_Per\_Share`: 每股内在价值



\### F. 期权与相对估值变量 (Options \& Multiples)

\* `Option\_S`: 标的资产当前价值

\* `Option\_K`: 期权平均行权价

\* `Option\_t`: 期权平均剩余到期时间

\* `Option\_Variance`: 资产价值方差

\* `Option\_y`: 股息率或延迟成本

\* `Number\_of\_Options`: 未行权期权总数

\* `Value\_of\_Options`: 员工期权总市场价值

\* `PE\_Ratio`: 市盈率

\* `PBV\_Ratio`: 市净率

\* `EV\_EBITDA`: 企业价值倍数

\* `EV\_Sales`: 企业价值/销售额倍数

2\. 第一模块：财务报表调整

\# Module\_1\_Financial\_Adjustments.md

\# 会计报表清洗与调整模块



\## 1. 模块说明

将研发费用（R\&D）资本化为资产，并将未并表的经营租赁（Operating Leases）债务化，以还原公司真实的盈利能力和资本投入。



\## 2. 数学公式



\### A. 研发费用资本化 (Capitalizing R\&D)

\* \*\*Inputs\*\*: `Amortization\_Period\_n`, `R\_and\_D\_Expense\_Current`, 数组 `R\_and\_D\_Expense\_Past\_t` ($t \\in \[1, n]$), `EBIT`, `Net\_Income`, `BV\_Equity`

\* \*\*Intermediate \& Outputs\*\*:

&nbsp;   \* `Unamortized\_R\_and\_D` = $\\sum\_{t=1}^{n} \\left( R\\\_and\\\_D\\\_Expense\\\_Past\\\_t \\times \\frac{n-t}{n} \\right)$

&nbsp;   \* `Value\_of\_Research\_Asset` = `R\_and\_D\_Expense\_Current` + `Unamortized\_R\_and\_D`

&nbsp;   \* `Amortization\_R\_and\_D` = $\\sum\_{t=1}^{n} \\left( \\frac{R\\\_and\\\_D\\\_Expense\\\_Past\\\_t}{n} \\right)$

&nbsp;   \* `Adjusted\_EBIT` = `EBIT` + `R\_and\_D\_Expense\_Current` - `Amortization\_R\_and\_D`

&nbsp;   \* `Adjusted\_Net\_Income` = `Net\_Income` + `R\_and\_D\_Expense\_Current` - `Amortization\_R\_and\_D`

&nbsp;   \* `Adjusted\_BV\_Equity` = `BV\_Equity` + `Value\_of\_Research\_Asset`



\### B. 经营租赁债务化 (Capitalizing Operating Leases)

\* \*\*Inputs\*\*: 数组 `Operating\_Lease\_Commitment\_t`, `Cost\_of\_Debt\_PreTax`, `Operating\_Lease\_Expense\_Current`, `MV\_Debt`

\* \*\*Intermediate \& Outputs\*\*:

&nbsp;   \* `PV\_of\_Operating\_Leases` = $\\sum \\frac{Operating\\\_Lease\\\_Commitment\\\_t}{(1 + Cost\\\_of\\\_Debt\\\_PreTax)^t}$

&nbsp;   \* `Adjusted\_MV\_Debt` = `MV\_Debt` + `PV\_of\_Operating\_Leases`

&nbsp;   \* `Imputed\_Interest\_Expense` = `PV\_of\_Operating\_Leases` $\\times$ `Cost\_of\_Debt\_PreTax`

&nbsp;   \* `Imputed\_Depreciation` = `Operating\_Lease\_Expense\_Current` - `Imputed\_Interest\_Expense`

&nbsp;   \* `Adjusted\_EBIT` = `Adjusted\_EBIT` + `Operating\_Lease\_Expense\_Current` - `Imputed\_Depreciation` (近似等于 + `Imputed\_Interest\_Expense`)



\## 3. Claude Code / Capital IQ 自行测试与检验环节

> \*\*Claude Code Instruction:\*\* 

> 1. Call Capital IQ API to fetch data for ticker "AAPL" (Apple Inc.). 

> 2. Retrieve `R\_and\_D\_Expense\_Current` and `R\_and\_D\_Expense\_Past\_t` for the last 5 years (`Amortization\_Period\_n` = 5).

> 3. Calculate `Unamortized\_R\_and\_D` and `Amortization\_R\_and\_D` strictly using the formulas above.

> 4. Output a log table comparing `EBIT` vs `Adjusted\_EBIT`, and `BV\_Equity` vs `Adjusted\_BV\_Equity`. Validate that `Adjusted\_EBIT` > `EBIT`.

3\. 第二模块：风险与折现率

\# Module\_2\_Risk\_Parameters.md

\# 风险与资本成本模块



\## 1. 模块说明

计算公司的 `Cost\_of\_Equity`, `Cost\_of\_Debt\_AfterTax`, 及 `WACC`。严格依赖 Bottom-up Beta 和市价权重。



\## 2. 数学公式



\### A. 杠杆 Beta (Levered Beta)

\* \*\*Inputs\*\*: `Beta\_U` (来自同业平均), `Adjusted\_MV\_Debt`, `MV\_Equity`, `Tax\_Rate\_Marginal`

\* \*\*Intermediate \& Outputs\*\*:

&nbsp;   \* `D\_E\_Ratio` = `Adjusted\_MV\_Debt` / `MV\_Equity`

&nbsp;   \* `Beta\_L` = `Beta\_U` $\\times$ $(1 + (1 - Tax\\\_Rate\\\_Marginal) \\times D\\\_E\\\_Ratio)$



\### B. 资本成本计算 (WACC)

\* \*\*Inputs\*\*: `Risk\_Free\_Rate`, `Equity\_Risk\_Premium`, `Beta\_L`, `Cost\_of\_Debt\_PreTax`, `Tax\_Rate\_Marginal`, `Adjusted\_MV\_Debt`, `MV\_Equity`

\* \*\*Outputs\*\*:

&nbsp;   \* `Cost\_of\_Equity` = `Risk\_Free\_Rate` + (`Beta\_L` $\\times$ `Equity\_Risk\_Premium`)

&nbsp;   \* `Cost\_of\_Debt\_AfterTax` = `Cost\_of\_Debt\_PreTax` $\\times$ $(1 - Tax\\\_Rate\\\_Marginal)$

&nbsp;   \* `Weight\_Equity` = `MV\_Equity` / (`MV\_Equity` + `Adjusted\_MV\_Debt`)

&nbsp;   \* `Weight\_Debt` = `Adjusted\_MV\_Debt` / (`MV\_Equity` + `Adjusted\_MV\_Debt`)

&nbsp;   \* `WACC` = (`Cost\_of\_Equity` $\\times$ `Weight\_Equity`) + (`Cost\_of\_Debt\_AfterTax` $\\times$ `Weight\_Debt`)



\## 3. Claude Code / Capital IQ 自行测试与检验环节

> \*\*Claude Code Instruction:\*\*

> 1. Fetch `Beta\_U` for the "Software" or relevant sector for "MSFT" via Capital IQ.

> 2. Fetch MSFT's `MV\_Equity`, `MV\_Debt`, and `Tax\_Rate\_Marginal`. (Assume no lease adjustments for this test).

> 3. Calculate `D\_E\_Ratio`, `Beta\_L`, `Cost\_of\_Equity`, and `WACC` (Assume `Risk\_Free\_Rate`=0.04, `Equity\_Risk\_Premium`=0.05, `Cost\_of\_Debt\_PreTax`=0.05).

> 4. Print execution log. Assert that `WACC` lies between `Cost\_of\_Debt\_AfterTax` and `Cost\_of\_Equity`.

4\. 第三模块：再投资、现金流与增长率

\# Module\_3\_CashFlow\_and\_Growth.md

\# 现金流与基本面增长率模块



\## 1. 模块说明

增长来源于再投资。本模块负责计算真实再投资率，推导公司自由现金流（FCFF）与股权自由现金流（FCFE），以及基于基本面的内生增长率。



\## 2. 数学公式



\### A. 再投资与现金流计算 (Reinvestment \& Cash Flows)

\* \*\*Inputs\*\*: `Adjusted\_EBIT`, `Tax\_Rate\_Marginal`, `CapEx`, `D\_A`, `R\_and\_D\_Expense\_Current`, `Amortization\_R\_and\_D`, `Change\_in\_Noncash\_WC`, `Adjusted\_Net\_Income`, `Net\_Debt\_Issued`

\* \*\*Intermediate\*\*:

&nbsp;   \* `Adjusted\_CapEx` = `CapEx` + `R\_and\_D\_Expense\_Current`

&nbsp;   \* `Adjusted\_D\_A` = `D\_A` + `Amortization\_R\_and\_D`

&nbsp;   \* `Reinvestment\_Firm` = `Adjusted\_CapEx` - `Adjusted\_D\_A` + `Change\_in\_Noncash\_WC`

&nbsp;   \* `Reinvestment\_Equity` = `Reinvestment\_Firm` - `Net\_Debt\_Issued`

\* \*\*Outputs\*\*:

&nbsp;   \* `FCFF` = `Adjusted\_EBIT` $\\times$ $(1 - Tax\\\_Rate\\\_Marginal)$ - `Reinvestment\_Firm`

&nbsp;   \* `FCFE` = `Adjusted\_Net\_Income` - `Reinvestment\_Equity`



\### B. 投入资本与基本面增长率 (ROIC \& Fundamental Growth)

\* \*\*Inputs\*\*: `Adjusted\_BV\_Equity`, `BV\_Debt`, `Cash\_and\_Marketable\_Securities` (均使用上一期期末/本期期初值)

\* \*\*Intermediate\*\*:

&nbsp;   \* `Adjusted\_Invested\_Capital` = `Adjusted\_BV\_Equity` + `BV\_Debt` - `Cash\_and\_Marketable\_Securities`

&nbsp;   \* `ROIC` = (`Adjusted\_EBIT` $\\times$ $(1 - Tax\\\_Rate\\\_Marginal)$) / `Adjusted\_Invested\_Capital` (上一期)

&nbsp;   \* `ROE` = `Adjusted\_Net\_Income` / `Adjusted\_BV\_Equity` (上一期)

&nbsp;   \* `RIR\_Firm` = `Reinvestment\_Firm` / (`Adjusted\_EBIT` $\\times$ $(1 - Tax\\\_Rate\\\_Marginal)$)

&nbsp;   \* `RIR\_Equity` = `Reinvestment\_Equity` / `Adjusted\_Net\_Income`

\* \*\*Outputs\*\*:

&nbsp;   \* `Expected\_Growth\_EBIT` = `ROIC` $\\times$ `RIR\_Firm`

&nbsp;   \* `Expected\_Growth\_NI` = `ROE` $\\times$ `RIR\_Equity`



\## 3. Claude Code / Capital IQ 自行测试与检验环节

> \*\*Claude Code Instruction:\*\*

> 1. Call Capital IQ for "TSLA" (Tesla). Fetch operating inputs for the last 2 fiscal years to compute current FCFF and Growth parameters.

> 2. Implement the formulas above to calculate `Reinvestment\_Firm`, `FCFF`, `ROIC`, and `Expected\_Growth\_EBIT`. 

> 3. Verify constraint: `Expected\_Growth\_EBIT` MUST equal `ROIC` \* `RIR\_Firm`. Output the test proof in the log.

5\. 第四模块：内在绝对估值 (DCF)

\# Module\_4\_Intrinsic\_Valuation.md

\# 内在价值折现模块 (DCF)



\## 1. 模块说明

计算预测期和永续稳定期的现金流现值总和。强制执行“稳定增长期约束”：`Stable\_Growth\_Rate` 不得大于 `Risk\_Free\_Rate`。



\## 2. 数学公式



\### A. 终值计算 (Terminal Value)

\* \*\*Inputs\*\*: 预测期最后一年(第 $n$ 年)的 `FCFF\_n`, `Adjusted\_EBIT\_n`, `WACC\_st` (稳定期WACC), `Stable\_Growth\_Rate`

\* \*\*Constraints\*\*: 

&nbsp;   \* `Stable\_Growth\_Rate` $\\le$ `Risk\_Free\_Rate`

&nbsp;   \* 稳定期假设超额收益消失：`ROIC\_st` = `WACC\_st`

&nbsp;   \* 稳定期再投资率 `RIR\_Firm\_st` = `Stable\_Growth\_Rate` / `ROIC\_st`

\* \*\*Intermediate \& Outputs\*\*:

&nbsp;   \* `FCFF\_n+1` = `Adjusted\_EBIT\_n` $\\times$ $(1 + Stable\\\_Growth\\\_Rate) \\times (1 - Tax\\\_Rate\\\_Marginal) \\times (1 - RIR\\\_Firm\\\_st)$

&nbsp;   \* `Terminal\_Value\_Firm` = `FCFF\_n+1` / (`WACC\_st` - `Stable\_Growth\_Rate`)



\### B. 模型加总 (Firm to Equity Bridge)

\* \*\*Inputs\*\*: `FCFF\_t` ($t=1...n$), `WACC`, `Terminal\_Value\_Firm`, `Cash\_and\_Marketable\_Securities`, `Adjusted\_MV\_Debt`, `Value\_of\_Options` (来自期权模块), `Shares\_Outstanding`

\* \*\*Outputs\*\*:

&nbsp;   \* `Value\_of\_Operating\_Assets` = $\\sum\_{t=1}^{n} \\frac{FCFF\_t}{(1+WACC)^t} + \\frac{Terminal\\\_Value\\\_Firm}{(1+WACC)^n}$

&nbsp;   \* `Value\_of\_Equity` = `Value\_of\_Operating\_Assets` + `Cash\_and\_Marketable\_Securities` - `Adjusted\_MV\_Debt`

&nbsp;   \* `Value\_Per\_Share\_Pre\_Options` = `Value\_of\_Equity` / `Shares\_Outstanding`

&nbsp;   \* `Value\_Per\_Share` = (`Value\_of\_Equity` - `Value\_of\_Options`) / `Shares\_Outstanding`



\## 3. Claude Code / Capital IQ 自行测试与检验环节

> \*\*Claude Code Instruction:\*\*

> 1. Use the projected `FCFF` from Module 3 for a 5-year high-growth period for "TSLA".

> 2. Set `Stable\_Growth\_Rate` equal to `Risk\_Free\_Rate`. Compute `Terminal\_Value\_Firm` using the strict `RIR\_Firm\_st` formula.

> 3. Sum the PVs, add Cash, subtract Debt to find `Value\_of\_Equity`.

> 4. Print valuation bridge log: Operating Assets -> + Cash -> - Debt -> Equity Value -> / Shares -> Value Per Share.

6\. 第五模块：相对估值 (Multiples)

\# Module\_5\_Relative\_Valuation.md

\# 相对估值与倍数理论模块



\## 1. 模块说明

将所有相对倍数（Multiples）解构为其基本面（伴随变量）。计算公司基于其基本面支撑的内在理论倍数（Intrinsic Multiples）。



\## 2. 数学公式 (基于稳定期模型推导)



\### A. 权益倍数 (Equity Multiples)

\* \*\*PE\_Ratio\_Forward (市盈率)\*\*:

&nbsp;   \* 伴随变量: `Expected\_Growth\_EPS`

&nbsp;   \* 公式: `PE\_Ratio\_Forward` = `Payout\_Ratio` / (`Cost\_of\_Equity` - `Stable\_Growth\_Rate`)

\* \*\*PBV\_Ratio (市净率)\*\*:

&nbsp;   \* 伴随变量: `ROE`

&nbsp;   \* 公式: `PBV\_Ratio` = (`ROE` - `Stable\_Growth\_Rate`) / (`Cost\_of\_Equity` - `Stable\_Growth\_Rate`)



\### B. 企业价值倍数 (Firm Value Multiples)

\* \*\*EV\_EBITDA (企业价值/EBITDA)\*\*:

&nbsp;   \* 伴随变量: `RIR\_Firm` 或 `ROIC`

&nbsp;   \* 公式: `EV\_EBITDA` = $\\frac{(1 - Tax\\\_Rate\\\_Marginal) - (\\frac{D\\\_A}{EBITDA} \\times (1 - Tax\\\_Rate\\\_Marginal)) - \\frac{Reinvestment\\\_Firm}{EBITDA}}{WACC - Stable\\\_Growth\\\_Rate}$

\* \*\*EV\_Sales (企业价值/销售额)\*\*:

&nbsp;   \* 伴随变量: `After\_Tax\_Operating\_Margin` = (`Adjusted\_EBIT` $\\times$ $(1 - Tax\\\_Rate\\\_Marginal)$) / `Revenues`

&nbsp;   \* 公式: `EV\_Sales` = `After\_Tax\_Operating\_Margin` $\\times$ $(1 - RIR\\\_Firm)$ / (`WACC` - `Stable\_Growth\_Rate`)



\## 3. Claude Code / Capital IQ 自行测试与检验环节

> \*\*Claude Code Instruction:\*\*

> 1. Pull Capital IQ data for a mature firm, e.g., "KO" (Coca-Cola). 

> 2. Compute its actual `PE\_Ratio\_Forward` from the market.

> 3. Compute its intrinsic `PE\_Ratio\_Forward` using the formula: `Payout\_Ratio` / (`Cost\_of\_Equity` - `Stable\_Growth\_Rate`).

> 4. Print out both values and calculate the percentage discrepancy. Assess if the stock is overvalued or undervalued based purely on fundamentals.

7\. 第六模块：期权定价与最终每股价值调整

\# Module\_6\_Options\_and\_Per\_Share\_Value.md

\# 期权定价与每股价值模块



\## 1. 模块说明

对员工期权稀释效应采用 Black-Scholes 期权模型精确计算。期权会稀释股权价值，绝不能简单地用完全稀释股数法（Fully Diluted Shares）除以总价值。



\## 2. 数学公式



\### A. Black-Scholes 核心模型 (BSM)

\* \*\*Inputs\*\*: 

&nbsp;   \* `Option\_S`: 标的资产当前价值 (`Value\_Per\_Share\_Pre\_Options`，需迭代或直接代入当前未稀释估值)

&nbsp;   \* `Option\_K`: 平均行权价 (`Average\_Strike\_Price\_Options`)

&nbsp;   \* `Option\_t`: 平均剩余寿命 (`Average\_Maturity\_Options\_t`)

&nbsp;   \* `Option\_r`: 对应期限的无风险利率 (`Risk\_Free\_Rate`)

&nbsp;   \* `Option\_Variance`: 资产波动率的平方 ($\\sigma^2$)

&nbsp;   \* `Option\_y`: 股息率 (`Payout\_Ratio` $\\times$ `Net\_Income` / `MV\_Equity`)

\* \*\*Intermediate\*\*:

&nbsp;   \* $d\_1 = \\frac{\\ln(Option\\\_S / Option\\\_K) + (Option\\\_r - Option\\\_y + Option\\\_Variance / 2) \\times Option\\\_t}{\\sqrt{Option\\\_Variance} \\times \\sqrt{Option\\\_t}}$

&nbsp;   \* $d\_2 = d\_1 - \\sqrt{Option\\\_Variance} \\times \\sqrt{Option\\\_t}$

\* \*\*Output\*\*:

&nbsp;   \* `Call\_Value` = $Option\\\_S \\times e^{-Option\\\_y \\times Option\\\_t} \\times N(d\_1) - Option\\\_K \\times e^{-Option\\\_r \\times Option\\\_t} \\times N(d\_2)$



\### B. 期权稀释与每股最终价值

\* \*\*Inputs\*\*: `Number\_of\_Options`, `Call\_Value`, `Value\_of\_Equity`, `Primary\_Shares\_Outstanding`

\* \*\*Outputs\*\*:

&nbsp;   \* `Value\_of\_Options` = `Call\_Value` $\\times$ `Number\_of\_Options`

&nbsp;   \* `Value\_Per\_Share` = (`Value\_of\_Equity` - `Value\_of\_Options`) / `Primary\_Shares\_Outstanding`



\## 3. Claude Code / Capital IQ 自行测试与检验环节

> \*\*Claude Code Instruction:\*\*

> 1. Fetch outstanding employee stock options data for a tech firm like "CSCO" (Cisco) via Capital IQ (`Number\_of\_Options`, `Average\_Strike\_Price\_Options`, `Average\_Maturity\_Options\_t`).

> 2. Execute the BSM model above to find `Call\_Value` and `Value\_of\_Options`.

> 3. Adjust the DCF `Value\_of\_Equity` by subtracting `Value\_of\_Options`, then divide by `Primary\_Shares\_Outstanding`.

> 4. Print a log comparing the naive "Fully Diluted" Value Per Share vs. the BSM-adjusted `Value\_Per\_Share` formula.



