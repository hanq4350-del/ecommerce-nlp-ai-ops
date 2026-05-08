import os
import re
from collections import Counter

import pandas as pd
import matplotlib.pyplot as plt


# ========== 0. 中文显示设置 ==========
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False


# ========== 1. 路径设置 ==========
DATA_PATH = "data/reviews.csv"
OUTPUT_DIR = "output"
FIGURE_DIR = "figures"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FIGURE_DIR, exist_ok=True)


# ========== 2. 读取数据 ==========
df = pd.read_csv(DATA_PATH)

print("原始数据规模：", df.shape)
print("字段名：", df.columns.tolist())


# ========== 3. 字段重命名 ==========
df = df.rename(columns={
    "Clothing ID": "clothing_id",
    "Age": "age",
    "Title": "title",
    "Review Text": "review_text",
    "Rating": "rating",
    "Recommended IND": "recommended",
    "Positive Feedback Count": "positive_feedback",
    "Division Name": "division",
    "Department Name": "department",
    "Class Name": "class_name"
})


# ========== 4. 数据清洗 ==========
df = df.drop_duplicates()
df = df.dropna(subset=["review_text"])

df["title"] = df["title"].fillna("")
df["division"] = df["division"].fillna("Unknown")
df["department"] = df["department"].fillna("Unknown")
df["class_name"] = df["class_name"].fillna("Unknown")


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


df["clean_review"] = df["review_text"].apply(clean_text)


# ========== 5. 构建情感标签 ==========
def get_sentiment(rating):
    if rating >= 4:
        return "positive"
    elif rating == 3:
        return "neutral"
    else:
        return "negative"


df["sentiment"] = df["rating"].apply(get_sentiment)

sentiment_map = {
    "positive": "正向",
    "neutral": "中性",
    "negative": "负向"
}

df["sentiment_cn"] = df["sentiment"].map(sentiment_map)

print("清洗后数据规模：", df.shape)
print("情感分布：")
print(df["sentiment_cn"].value_counts())


# ========== 6. 差评主题标签映射 ==========
topic_map = {
    "size_issue": "尺码问题",
    "fabric_quality": "面料质量",
    "color_mismatch": "颜色/图片不符",
    "style_design": "款式设计不符合预期",
    "price_value": "价格感知偏高",
    "return_intention": "退换货倾向明显",
    "other": "其他体验问题"
}


def topic_to_chinese(x):
    return "、".join(
        topic_map.get(item.strip(), item.strip())
        for item in str(x).split(",")
    )


# ========== 7. 商品 / 类目维度指标 ==========
class_metrics = (
    df.groupby("class_name")
    .agg(
        review_count=("review_text", "count"),
        avg_rating=("rating", "mean"),
        recommend_rate=("recommended", "mean"),
        negative_rate=("sentiment", lambda x: (x == "negative").mean()),
        avg_positive_feedback=("positive_feedback", "mean")
    )
    .reset_index()
    .sort_values("review_count", ascending=False)
)

class_metrics.to_csv(
    os.path.join(OUTPUT_DIR, "class_metrics.csv"),
    index=False,
    encoding="utf-8-sig"
)

print("类目指标表已保存：output/class_metrics.csv")


# ========== 8. 类目异常识别 / 异动分析 ==========
overall_avg_rating = df["rating"].mean()
overall_recommend_rate = df["recommended"].mean()
overall_negative_rate = (df["sentiment"] == "negative").mean()


def identify_anomaly(row):
    anomaly_types = []

    # 规则 1：平均评分低于整体均值 0.2 分以上
    if row["avg_rating"] < overall_avg_rating - 0.2:
        anomaly_types.append("平均评分偏低")

    # 规则 2：推荐率低于整体推荐率 5 个百分点以上
    if row["recommend_rate"] < overall_recommend_rate - 0.05:
        anomaly_types.append("推荐率偏低")

    # 规则 3：负向评论占比高于整体负向率 5 个百分点以上
    if row["negative_rate"] > overall_negative_rate + 0.05:
        anomaly_types.append("负向评论占比偏高")

    if len(anomaly_types) == 0:
        return "正常"

    return "、".join(anomaly_types)


def get_anomaly_priority(anomaly_type):
    if anomaly_type == "正常":
        return "低"

    if "负向评论占比偏高" in anomaly_type and "平均评分偏低" in anomaly_type:
        return "高"

    if "推荐率偏低" in anomaly_type and "负向评论占比偏高" in anomaly_type:
        return "高"

    if "平均评分偏低" in anomaly_type or "负向评论占比偏高" in anomaly_type:
        return "中高"

    return "中"


def get_suggested_action(anomaly_type):
    if anomaly_type == "正常":
        return "维持常规监控，关注评论量、评分和推荐率变化。"

    actions = []

    if "平均评分偏低" in anomaly_type:
        actions.append("优先查看低分评论，定位影响评分的核心体验问题")

    if "推荐率偏低" in anomaly_type:
        actions.append("分析用户不推荐原因，重点排查商品预期、详情页表达和售后体验")

    if "负向评论占比偏高" in anomaly_type:
        actions.append("结合差评关键词和主题归因，优先处理高频差评原因")

    return "；".join(actions)


anomaly_df = class_metrics.copy()
anomaly_df["anomaly_type"] = anomaly_df.apply(identify_anomaly, axis=1)
anomaly_df["priority"] = anomaly_df["anomaly_type"].apply(get_anomaly_priority)
anomaly_df["suggested_action"] = anomaly_df["anomaly_type"].apply(get_suggested_action)

anomaly_result = anomaly_df[anomaly_df["anomaly_type"] != "正常"].copy()

priority_order = {"高": 1, "中高": 2, "中": 3, "低": 4}
anomaly_result["priority_order"] = anomaly_result["priority"].map(priority_order)

anomaly_result = anomaly_result.sort_values(
    by=["priority_order", "negative_rate", "avg_rating"],
    ascending=[True, False, True]
)

anomaly_result = anomaly_result.drop(columns=["priority_order"])

anomaly_result.to_csv(
    os.path.join(OUTPUT_DIR, "anomaly_analysis.csv"),
    index=False,
    encoding="utf-8-sig"
)

print("异常类目识别表已保存：output/anomaly_analysis.csv")
print("整体平均评分：", round(overall_avg_rating, 3))
print("整体推荐率：", round(overall_recommend_rate, 3))
print("整体负向评论占比：", round(overall_negative_rate, 3))
print("异常类目数量：", anomaly_result.shape[0])


# ========== 9. 情感分布图 ==========
sentiment_order = ["正向", "中性", "负向"]
sentiment_counts = df["sentiment_cn"].value_counts().reindex(sentiment_order, fill_value=0)

plt.figure(figsize=(6, 4))
plt.bar(sentiment_counts.index, sentiment_counts.values)
plt.title("情感分布")
plt.xlabel("情感类别")
plt.ylabel("评论数量")
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, "sentiment_distribution.png"), dpi=300)
plt.close()


# ========== 10. 评分分布图 ==========
rating_counts = df["rating"].value_counts().sort_index()

plt.figure(figsize=(6, 4))
plt.bar(rating_counts.index, rating_counts.values)
plt.title("评分分布")
plt.xlabel("评分")
plt.ylabel("评论数量")
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, "rating_distribution.png"), dpi=300)
plt.close()


# ========== 11. 高频商品类别平均评分图 ==========
top_classes = class_metrics.head(10).sort_values("avg_rating")

plt.figure(figsize=(8, 5))
plt.barh(top_classes["class_name"], top_classes["avg_rating"])
plt.title("高频商品类别平均评分")
plt.xlabel("平均评分")
plt.ylabel("商品类别")
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, "top_class_avg_rating.png"), dpi=300)
plt.close()


# ========== 12. 异常类目负向评论占比图 ==========
if anomaly_result.shape[0] > 0:
    anomaly_plot = anomaly_result.head(10).sort_values("negative_rate")

    plt.figure(figsize=(8, 5))
    plt.barh(anomaly_plot["class_name"], anomaly_plot["negative_rate"])
    plt.title("异常类目负向评论占比")
    plt.xlabel("负向评论占比")
    plt.ylabel("商品类别")
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURE_DIR, "anomaly_negative_rate.png"), dpi=300)
    plt.close()


# ========== 13. 负向评论关键词分析 ==========
negative_df = df[df["sentiment"] == "negative"].copy()

stopwords = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "i", "me", "my", "we", "our", "you", "your", "it", "this", "that",
    "to", "of", "in", "on", "for", "with", "as", "at", "by", "from",
    "so", "very", "too", "not", "be", "have", "has", "had", "would",
    "could", "should", "just", "they", "them", "he", "she", "her",
    "him", "its", "if", "than", "then", "there", "these", "those",
    "also", "more", "all", "one", "two", "three", "really", "much",
    "product", "item", "dress", "shirt", "top", "tracy", "reese",
    "like", "love", "back", "order", "ordered", "read", "when", "out",
    "will", "did", "don", "get", "got", "even", "way", "looked",
    "looks", "look", "because", "made", "retailer", "great", "which"
}

all_words = []

for text in negative_df["clean_review"]:
    words = text.split()
    words = [w for w in words if len(w) > 2 and w not in stopwords]
    all_words.extend(words)

word_counts = Counter(all_words)

keyword_df = pd.DataFrame(
    word_counts.most_common(30),
    columns=["keyword", "count"]
)

keyword_df.to_csv(
    os.path.join(OUTPUT_DIR, "negative_keywords.csv"),
    index=False,
    encoding="utf-8-sig"
)

top_keywords = keyword_df.sort_values("count", ascending=True)

plt.figure(figsize=(8, 6))
plt.barh(top_keywords["keyword"], top_keywords["count"])
plt.title("负向评论高频关键词")
plt.xlabel("出现次数")
plt.ylabel("关键词")
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, "negative_keywords.png"), dpi=300)
plt.close()


# ========== 14. 差评主题归因 ==========
topic_keywords = {
    "size_issue": [
        "size", "small", "large", "tight", "loose", "big", "short",
        "long", "fit", "fits", "fitting", "petite", "waist", "length",
        "sleeve", "sleeves", "bust", "hips"
    ],
    "fabric_quality": [
        "fabric", "material", "quality", "cheap", "thin", "scratchy",
        "rough", "poor", "bad", "heavy", "lightweight", "polyester",
        "cotton", "linen", "seams", "stitching"
    ],
    "color_mismatch": [
        "color", "colors", "picture", "photo", "image", "different",
        "darker", "lighter", "shown", "online", "bright", "faded"
    ],
    "style_design": [
        "style", "design", "look", "looks", "shape", "flattering",
        "unflattering", "weird", "awkward", "boxy", "cut", "pattern"
    ],
    "price_value": [
        "price", "expensive", "worth", "value", "money", "overpriced",
        "cost", "sale"
    ],
    "return_intention": [
        "return", "returned", "returning", "exchange", "refund", "sent back"
    ]
}


def classify_topic(text):
    matched_topics = []

    for topic, keywords in topic_keywords.items():
        for word in keywords:
            if word in text:
                matched_topics.append(topic)
                break

    if len(matched_topics) == 0:
        return "other"

    return ",".join(matched_topics)


negative_df["negative_topic"] = negative_df["clean_review"].apply(classify_topic)
negative_df["negative_topic_cn"] = negative_df["negative_topic"].apply(topic_to_chinese)

topic_summary = (
    negative_df["negative_topic"]
    .value_counts()
    .reset_index()
)

topic_summary.columns = ["negative_topic", "review_count"]
topic_summary["negative_topic_cn"] = topic_summary["negative_topic"].apply(topic_to_chinese)

topic_summary.to_csv(
    os.path.join(OUTPUT_DIR, "negative_topic_summary.csv"),
    index=False,
    encoding="utf-8-sig"
)

top_topics = topic_summary.head(10).sort_values("review_count")

plt.figure(figsize=(10, 6))
plt.barh(top_topics["negative_topic_cn"], top_topics["review_count"])
plt.title("负向评论主题分布")
plt.xlabel("评论数量")
plt.ylabel("负向主题")
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, "negative_topic_distribution.png"), dpi=300)
plt.close()


# ========== 15. 生成运营策略建议表 ==========
strategy_map = {
    "size_issue": {
        "problem": "尺码偏差 / 版型不合适",
        "strategy": "优化尺码表，增加模特身高体重、试穿报告和尺码推荐说明，降低用户选择成本。",
        "reply": "您好，很抱歉尺码体验没有达到预期。建议您参考详情页尺码表和试穿信息，我们也会继续优化尺码说明。",
        "review_metrics": "尺码相关差评率、退换货率、尺码咨询量"
    },
    "fabric_quality": {
        "problem": "面料质量问题",
        "strategy": "补充材质说明、近距离面料图和洗护建议，重点排查高差评商品的供应批次与品控问题。",
        "reply": "您好，感谢您的反馈。我们会将面料质感问题反馈给商品团队，并持续优化材质说明和质量控制。",
        "review_metrics": "面料相关差评率、商品评分、退货原因占比"
    },
    "color_mismatch": {
        "problem": "颜色 / 图片不符",
        "strategy": "优化商品图片光线，增加真实买家图和不同场景下的颜色展示，减少用户预期偏差。",
        "reply": "您好，很抱歉图片展示与实际感受存在差异。我们会优化图片展示，并增加更真实的颜色参考。",
        "review_metrics": "图片不符相关差评率、买家图点击率、详情页停留时长"
    },
    "style_design": {
        "problem": "款式设计不符合预期",
        "strategy": "在详情页明确版型、适合场景和穿搭建议，减少用户对款式、版型和上身效果的误判。",
        "reply": "您好，感谢您的建议。我们会进一步完善版型和穿搭说明，帮助用户更准确地选择商品。",
        "review_metrics": "款式相关差评率、商品评分、推荐率"
    },
    "price_value": {
        "problem": "价格感知偏高",
        "strategy": "针对价格敏感商品设置优惠券、会员价或搭配购，同时强化材质、设计和穿搭场景卖点。",
        "reply": "您好，感谢您的反馈。我们会综合评估商品定价与优惠活动，为用户提供更好的购买体验。",
        "review_metrics": "优惠券使用率、转化率、价格相关差评率"
    },
    "return_intention": {
        "problem": "退换货倾向明显",
        "strategy": "优化购买前尺码推荐和详情页说明，完善退换货说明，降低因预期偏差导致的退货率。",
        "reply": "您好，很抱歉本次购物体验不佳。您可以根据平台规则申请退换货，我们也会继续优化商品信息展示。",
        "review_metrics": "退货率、换货率、客服工单量"
    },
    "other": {
        "problem": "其他体验问题",
        "strategy": "对评论进行人工复核，补充细分标签，持续完善商品问题诊断体系。",
        "reply": "您好，感谢您的反馈。我们会认真记录您的意见，并持续优化商品和服务体验。",
        "review_metrics": "主题差评率、商品评分、推荐率"
    }
}

strategy_rows = []

for topic, info in strategy_map.items():
    example = negative_df[negative_df["negative_topic"].str.contains(topic, na=False)]

    if len(example) > 0:
        example_review = example.iloc[0]["review_text"]
    else:
        example_review = ""

    strategy_rows.append({
        "negative_topic": topic,
        "negative_topic_cn": topic_map.get(topic, topic),
        "problem": info["problem"],
        "example_review": example_review,
        "operation_strategy": info["strategy"],
        "customer_service_reply": info["reply"],
        "review_metrics": info["review_metrics"]
    })

strategy_df = pd.DataFrame(strategy_rows)

strategy_df.to_csv(
    os.path.join(OUTPUT_DIR, "operation_strategy.csv"),
    index=False,
    encoding="utf-8-sig"
)

print("运营策略表已保存：output/operation_strategy.csv")


# ========== 16. 保存负向评论明细 ==========
negative_df.to_csv(
    os.path.join(OUTPUT_DIR, "negative_reviews_with_topics.csv"),
    index=False,
    encoding="utf-8-sig"
)

print("负向评论主题明细已保存：output/negative_reviews_with_topics.csv")


# ========== 17. 保存清洗后的总表 ==========
df.to_csv(
    os.path.join(OUTPUT_DIR, "clean_reviews.csv"),
    index=False,
    encoding="utf-8-sig"
)

print("清洗后数据已保存：output/clean_reviews.csv")
print("图表已保存到 figures 文件夹")
print("项目 MVP 已完成！")