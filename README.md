# E-commerce Review AI Ops System

基于 NLP 与 Prompt Engineering 的电商评论洞察与 AI 运营策略生成系统。

## 项目简介

本项目基于女性服装电商评论数据，搭建“指标监控—异常识别—NLP 问题归因—Prompt 策略生成”的分析流程，辅助运营人员从用户评论中识别核心痛点，并生成可执行的商品运营优化建议。

项目不是训练大模型，而是将评论分析结果、异常识别结果和差评主题归因结构化为 Prompt 输入，模拟 AI 辅助商品运营决策场景。

## 核心功能

- 评论数据清洗与情感标签构建
- 商品类目指标分析
- 异常类目识别
- 负向评论关键词提取
- 差评主题归因
- AI 运营策略生成 Demo
- Streamlit 本地可视化页面

## 项目结构

```text
ecommerce-review-ai-ops
├── app.py
├── main.py
├── requirements.txt
├── figures
│   ├── rating_distribution.png
│   ├── sentiment_distribution.png
│   ├── negative_keywords.png
│   ├── negative_topic_distribution.png
│   └── anomaly_negative_rate.png
└── output
    ├── class_metrics.csv
    ├── anomaly_analysis.csv
    ├── negative_topic_summary.csv
    └── operation_strategy.csv