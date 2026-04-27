# Quantitative Trading

美股优先的量化交易系统 MVP。当前阶段聚焦日线回测、策略接口、风控和模拟交易骨架，不接真实资金账户。

## 当前范围

1. 美股股票和 ETF。
2. 日线策略。
3. 只做多，不加杠杆。
4. 回测和模拟交易优先。
5. Alpaca paper trading 作为后续券商适配目标。

## 本地验证

```bash
python3 -m unittest discover -s tests
python3 scripts/run_sample_backtest.py
```

编译检查：

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m compileall src scripts tests
```

## 打开工作台

```bash
python3 scripts/serve_dashboard.py 8000
```

然后访问 `http://127.0.0.1:8000`。

工作台也支持 GitHub Pages 静态模式。没有本地 API 时，前端会使用浏览器内置的示例回测逻辑生成演示结果。

也可以先安装为本地可编辑包：

```bash
python3 -m pip install -e .
```

## 文档

1. [量化交易系统需求文档](docs/requirements/2026-04-26-quant-trading-system-requirements.md)
2. [美股优先 MVP 推荐方案](docs/requirements/2026-04-26-us-market-mvp-recommendation.md)
3. [美股量化交易 MVP 技术架构](docs/architecture/2026-04-26-us-market-mvp-architecture.md)
