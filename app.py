import os
import re
import pandas as pd
import streamlit as st


# ========== 1. 页面基础设置 ==========
st.set_page_config(
    page_title="电商评论洞察与 AI 运营策略生成系统",
    page_icon="🛍️",
    layout="wide"
)

OUTPUT_DIR = "output"
FIGURE_DIR = "figures"


# ========== 2. 中英文主题关键词配置 ==========
topic_keywords = {
    "尺码问题": [
        "size", "small", "large", "tight", "loose", "big", "short",
        "long", "fit", "fits", "fitting", "petite", "waist", "length",
        "sleeve", "sleeves", "bust", "hips",
        "尺码", "码数", "偏小", "偏大", "太小", "太大", "紧", "宽松",
        "不合身", "不适合", "腰围", "袖子", "衣长", "长度", "版型偏小", "版型偏大"
    ],
    "面料质量": [
        "fabric", "material", "quality", "cheap", "thin", "scratchy",
        "rough", "poor", "bad", "heavy", "lightweight", "polyester",
        "cotton", "linen", "seams", "stitching",
        "面料", "材质", "质量", "质感", "布料", "太薄", "很薄", "粗糙",
        "廉价", "起球", "线头", "做工", "缝线", "不舒服", "扎人", "透", "厚重"
    ],
    "颜色/图片不符": [
        "color", "colors", "picture", "photo", "image", "different",
        "darker", "lighter", "shown", "online", "bright", "faded",
        "颜色", "色差", "图片", "实物", "图片不符", "颜色不符", "和图片不一样",
        "比图片暗", "比图片亮", "显色", "偏色", "褪色", "实物不符"
    ],
    "款式设计不符合预期": [
        "style", "design", "look", "looks", "shape", "flattering",
        "unflattering", "weird", "awkward", "boxy", "cut", "pattern",
        "款式", "设计", "版型", "风格", "上身", "不好看", "显胖", "奇怪",
        "不修身", "不显瘦", "剪裁", "图案", "穿搭", "不符合预期"
    ],
    "价格感知偏高": [
        "price", "expensive", "worth", "value", "money", "overpriced",
        "cost", "sale",
        "价格", "太贵", "贵", "偏贵", "不值", "性价比", "划算",
        "不划算", "价格高", "优惠", "折扣"
    ],
    "退换货倾向明显": [
        "return", "returned", "returning", "exchange", "refund", "sent back",
        "退货", "换货", "退换", "退款", "退回", "想退", "不想留",
        "申请退货", "退掉", "换码"
    ]
}


# ========== 3. 运营策略配置 ==========
strategy_map = {
    "尺码问题": {
        "detail_page": "优化尺码表，补充模特身高、体重、试穿尺码和尺码偏大/偏小提示。",
        "customer_reply": "您好，很抱歉尺码体验没有达到预期。建议您参考详情页尺码表和试穿信息，我们也会继续优化尺码说明。",
        "operation": "对尺码问题高频商品增加“尺码提醒”标签，并针对浏览用户增加尺码推荐提示，降低退换货率。",
        "role": "商品运营 / 内容运营 / 用户运营",
        "review_metrics": "尺码相关差评率、退换货率、尺码咨询量"
    },
    "面料质量": {
        "detail_page": "补充面料成分、厚薄程度、弹性、透气性和近距离材质细节图。",
        "customer_reply": "您好，感谢您的反馈。我们会将面料质感问题反馈给商品团队，并持续优化材质说明和质量控制。",
        "operation": "对面料差评集中的商品进行批次质检复核，必要时调整卖点表达或降低推荐权重。",
        "role": "商品运营 / 供应链协同 / 内容运营",
        "review_metrics": "面料相关差评率、商品评分、退货原因占比"
    },
    "颜色/图片不符": {
        "detail_page": "优化商品图片光线，增加自然光、室内光和买家实拍图，减少颜色预期偏差。",
        "customer_reply": "您好，很抱歉图片展示与实际感受存在差异。我们会优化图片展示，并增加更真实的颜色参考。",
        "operation": "对颜色差异反馈较多的商品增加“颜色以实物为准”说明，并优先补充真实买家图。",
        "role": "商品运营 / 内容运营 / 视觉设计",
        "review_metrics": "图片不符相关差评率、买家图点击率、详情页停留时长"
    },
    "款式设计不符合预期": {
        "detail_page": "在详情页明确版型、适合身材、穿搭场景和上身效果，减少用户对款式的误判。",
        "customer_reply": "您好，感谢您的建议。我们会进一步完善版型和穿搭说明，帮助用户更准确地选择商品。",
        "operation": "根据款式差评内容调整商品推荐人群，将商品推送给更匹配的风格偏好用户。",
        "role": "商品运营 / 推荐策略 / 内容运营",
        "review_metrics": "款式相关差评率、商品评分、推荐率"
    },
    "价格感知偏高": {
        "detail_page": "强化材质、设计、搭配场景和商品价值说明，提升用户对价格的理解。",
        "customer_reply": "您好，感谢您的反馈。我们会综合评估商品定价与优惠活动，为用户提供更好的购买体验。",
        "operation": "针对价格敏感商品设置优惠券、会员价、搭配购或限时折扣，提升转化率。",
        "role": "活动运营 / 商品运营 / 用户运营",
        "review_metrics": "优惠券使用率、转化率、价格相关差评率"
    },
    "退换货倾向明显": {
        "detail_page": "优化购买前尺码推荐、材质说明和退换货规则展示，降低用户决策不确定性。",
        "customer_reply": "您好，很抱歉本次购物体验不佳。您可以根据平台规则申请退换货，我们也会继续优化商品信息展示。",
        "operation": "对退换货倾向明显的商品进行差评复盘，重点排查尺码、面料、图片描述等问题。",
        "role": "客服 / 用户运营 / 商品运营",
        "review_metrics": "退货率、换货率、客服工单量"
    },
    "其他体验问题": {
        "detail_page": "补充商品关键信息，完善用户购买前可能关注的细节说明。",
        "customer_reply": "您好，感谢您的反馈。我们会认真记录您的意见，并持续优化商品和服务体验。",
        "operation": "对该类评论进行人工复核，补充更细分的问题标签，完善商品问题诊断体系。",
        "role": "运营 / 客服 / 商品团队",
        "review_metrics": "主题差评率、商品评分、推荐率"
    }
}


# ========== 4. 工具函数 ==========
def clean_text(text):
    """
    保留英文、中文和空格，用于中英文混合评论匹配。
    """
    text = str(text).lower()
    text = re.sub(r"[^a-zA-Z\u4e00-\u9fa5\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def identify_topics(comment):
    clean_comment = clean_text(comment)
    matched_topics = []

    for topic, keywords in topic_keywords.items():
        for word in keywords:
            if word in clean_comment:
                matched_topics.append(topic)
                break

    if not matched_topics:
        matched_topics = ["其他体验问题"]

    return matched_topics


def judge_sentiment(comment):
    negative_words = [
        "bad", "poor", "cheap", "thin", "small", "large", "tight",
        "loose", "return", "returned", "disappointed", "awful",
        "terrible", "unflattering", "scratchy", "different",
        "overpriced", "not worth", "doesn't", "didn't", "hate",
        "差", "不好", "失望", "廉价", "太薄", "偏小", "偏大", "不合身",
        "退货", "想退", "不值", "太贵", "色差", "粗糙", "扎人",
        "不好看", "显胖", "不舒服", "质量差", "图片不符", "不满意"
    ]

    positive_words = [
        "good", "great", "love", "beautiful", "perfect", "nice",
        "comfortable", "soft", "flattering", "recommend", "cute",
        "好", "很好", "喜欢", "漂亮", "合适", "舒服", "柔软",
        "推荐", "显瘦", "好看", "满意", "质量好", "值得", "不错"
    ]

    clean_comment = clean_text(comment)

    neg_score = sum(1 for word in negative_words if word in clean_comment)
    pos_score = sum(1 for word in positive_words if word in clean_comment)

    if neg_score > pos_score:
        return "负向"
    elif pos_score > neg_score:
        return "正向"
    else:
        return "中性/待判断"


def judge_priority(topics, sentiment):
    high_risk_topics = {"尺码问题", "面料质量", "退换货倾向明显"}
    medium_risk_topics = {"颜色/图片不符", "价格感知偏高", "款式设计不符合预期"}

    topic_set = set(topics)

    if sentiment == "负向" and len(topic_set & high_risk_topics) >= 2:
        return "高"
    elif sentiment == "负向" and (topic_set & high_risk_topics):
        return "中高"
    elif topic_set & medium_risk_topics:
        return "中"
    else:
        return "低"


def match_roles(topics):
    roles = []
    for topic in topics:
        info = strategy_map.get(topic, strategy_map["其他体验问题"])
        roles.append(info["role"])

    return "；".join(sorted(set(roles)))


def generate_prompt(comment, product_category, topics, sentiment, priority):
    topic_text = "、".join(topics)

    prompt = f"""
你是一名电商服装行业的用户运营分析师。请基于以下用户评论，生成可落地的运营优化建议。

【商品类别】
{product_category}

【用户评论】
{comment}

【情感判断】
{sentiment}

【问题主题】
{topic_text}

【运营优先级】
{priority}

请从以下五个角度输出：
1. 用户核心痛点总结
2. 商品详情页优化建议
3. 客服回复话术
4. 用户触达/运营策略
5. 后续复盘指标建议

要求：
- 建议要具体、可执行；
- 语言适合电商运营场景；
- 支持中文、英文或中英混合评论；
- 不要泛泛而谈；
- 重点关注如何提升评分、推荐率和购买体验。
"""
    return prompt.strip()


def generate_strategy(comment, product_category, topics, sentiment, priority):
    pain_points = []
    detail_suggestions = []
    customer_replies = []
    operation_suggestions = []
    review_metrics = []

    for topic in topics:
        info = strategy_map.get(topic, strategy_map["其他体验问题"])
        pain_points.append(topic)
        detail_suggestions.append(info["detail_page"])
        customer_replies.append(info["customer_reply"])
        operation_suggestions.append(info["operation"])
        review_metrics.append(info["review_metrics"])

    result = {
        "用户核心痛点": "、".join(pain_points),
        "商品详情页优化建议": "；".join(detail_suggestions),
        "客服回复话术": "；".join(customer_replies),
        "用户触达/运营策略": "；".join(operation_suggestions),
        "后续复盘指标": "；".join(sorted(set(review_metrics)))
    }

    return result


# ========== 5. 读取已有结果 ==========
@st.cache_data
def load_data():
    data = {}

    paths = {
        "class_metrics": os.path.join(OUTPUT_DIR, "class_metrics.csv"),
        "strategy": os.path.join(OUTPUT_DIR, "operation_strategy.csv"),
        "topic_summary": os.path.join(OUTPUT_DIR, "negative_topic_summary.csv"),
        "clean_reviews": os.path.join(OUTPUT_DIR, "clean_reviews.csv"),
        "anomaly_analysis": os.path.join(OUTPUT_DIR, "anomaly_analysis.csv"),
    }

    for key, path in paths.items():
        if os.path.exists(path):
            data[key] = pd.read_csv(path)

    return data


data = load_data()


# ========== 6. 页面标题 ==========
st.title("🛍️ 电商评论洞察与 AI 运营策略生成系统")

st.markdown(
    """
    **项目目标：** 基于 NLP 评论分析与 Prompt 策略生成，辅助运营人员快速识别用户痛点并生成优化方案。  

    **项目逻辑：**  
    指标监控 → 异常识别 → NLP 问题归因 → Prompt 结构化 → AI 运营策略生成
    """
)

st.divider()


# ========== 7. 数据概览 ==========
st.header("一、项目概览")

if "clean_reviews" in data:
    clean_reviews = data["clean_reviews"]

    total_reviews = clean_reviews.shape[0]
    avg_rating = round(clean_reviews["rating"].mean(), 2) if "rating" in clean_reviews.columns else "-"
    recommend_rate = round(clean_reviews["recommended"].mean() * 100, 2) if "recommended" in clean_reviews.columns else "-"
    negative_rate = round((clean_reviews["sentiment"] == "negative").mean() * 100, 2) if "sentiment" in clean_reviews.columns else "-"
    positive_rate = round((clean_reviews["sentiment"] == "positive").mean() * 100, 2) if "sentiment" in clean_reviews.columns else "-"
    anomaly_count = data["anomaly_analysis"].shape[0] if "anomaly_analysis" in data else 0

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("评论总量", f"{total_reviews:,}")
    col2.metric("平均评分", avg_rating)
    col3.metric("推荐率", f"{recommend_rate}%")
    col4.metric("正向评论占比", f"{positive_rate}%")
    col5.metric("负向评论占比", f"{negative_rate}%")
    col6.metric("异常类目数", anomaly_count)

else:
    st.warning("未找到 clean_reviews.csv，请先运行 main.py 生成分析结果。")


if "topic_summary" in data and not data["topic_summary"].empty:
    top_topic = data["topic_summary"].iloc[0]
    topic_name = top_topic.get("negative_topic_cn", top_topic.get("negative_topic", "未知主题"))
    topic_count = top_topic.get("review_count", "-")
    st.info(f"当前最高频差评主题：**{topic_name}**，涉及评论数：**{topic_count}**。")


if "anomaly_analysis" in data and not data["anomaly_analysis"].empty:
    top_anomaly = data["anomaly_analysis"].iloc[0]
    st.warning(
        f"当前优先关注异常类目：**{top_anomaly.get('class_name', '未知类目')}**；"
        f"异常类型：**{top_anomaly.get('anomaly_type', '未知')}**；"
        f"优先级：**{top_anomaly.get('priority', '未知')}**。"
    )

st.divider()


# ========== 8. AI 运营策略生成 Demo ==========
st.header("二、AI 运营策略生成 Demo")

st.markdown(
    """
    输入一条具体用户评论后，系统会自动识别情感倾向与用户痛点，
    并基于 Prompt 生成详情页优化、客服回复话术和用户触达策略。  
    支持 **中文评论、英文评论、中英混合评论**。
    """
)

example_comment = (
    "这件连衣裙款式还不错，但是尺码偏小，面料有点薄，颜色和图片也不太一样。"
)

comment_input = st.text_area(
    "请输入一条用户评论：",
    value=example_comment,
    height=120
)

product_category = st.selectbox(
    "请选择商品类别：",
    [
        "连衣裙 / Dresses",
        "针织衫 / Knits",
        "衬衫 / Blouses",
        "裤子 / Pants",
        "毛衣 / Sweaters",
        "夹克 / Jackets",
        "半身裙 / Skirts",
        "未知 / Unknown"
    ]
)

if st.button("生成 AI 运营策略"):
    topics = identify_topics(comment_input)
    sentiment = judge_sentiment(comment_input)
    priority = judge_priority(topics, sentiment)
    roles = match_roles(topics)
    strategy = generate_strategy(comment_input, product_category, topics, sentiment, priority)
    prompt = generate_prompt(comment_input, product_category, topics, sentiment, priority)

    st.subheader("1. NLP 识别结果")

    result_col1, result_col2, result_col3, result_col4 = st.columns(4)

    with result_col1:
        st.success(f"情感判断：{sentiment}")

    with result_col2:
        st.info(f"问题主题：{'、'.join(topics)}")

    with result_col3:
        st.warning(f"运营优先级：{priority}")

    with result_col4:
        st.write(f"适合处理角色：{roles}")

    st.subheader("2. AI 运营策略建议")

    st.markdown(f"**用户核心痛点：** {strategy['用户核心痛点']}")
    st.markdown(f"**商品详情页优化建议：** {strategy['商品详情页优化建议']}")
    st.markdown(f"**客服回复话术：** {strategy['客服回复话术']}")
    st.markdown(f"**用户触达/运营策略：** {strategy['用户触达/运营策略']}")
    st.markdown(f"**后续复盘指标：** {strategy['后续复盘指标']}")

    with st.expander("查看可输入大模型的 Prompt 模板"):
        st.code(prompt, language="text")

st.divider()


# ========== 9. 类目异常识别 ==========
st.header("三、类目异常识别 / 异动分析")

st.markdown(
    """
    该模块基于类目平均评分、推荐率和负向评论占比设置异常识别规则，
    用于定位评分偏低、推荐率偏低或差评率偏高的商品类别。
    """
)

anomaly_fig_col, anomaly_table_col = st.columns([1, 1.2])

with anomaly_fig_col:
    st.subheader("异常类目负向评论占比")
    anomaly_fig = os.path.join(FIGURE_DIR, "anomaly_negative_rate.png")
    if os.path.exists(anomaly_fig):
        st.image(anomaly_fig, use_container_width=True)
        st.caption("业务解读：负向评论占比较高的类目需要优先结合差评主题进行原因定位。")
    else:
        st.warning("未找到异常类目图，请先运行新版 main.py。")

with anomaly_table_col:
    st.subheader("异常类目识别结果")
    if "anomaly_analysis" in data and not data["anomaly_analysis"].empty:
        anomaly_df = data["anomaly_analysis"].copy()

        display_cols = [
            "class_name",
            "review_count",
            "avg_rating",
            "recommend_rate",
            "negative_rate",
            "anomaly_type",
            "priority",
            "suggested_action"
        ]

        available_cols = [c for c in display_cols if c in anomaly_df.columns]

        rename_cols = {
            "class_name": "商品类别",
            "review_count": "评论量",
            "avg_rating": "平均评分",
            "recommend_rate": "推荐率",
            "negative_rate": "负向评论占比",
            "anomaly_type": "异常类型",
            "priority": "优先级",
            "suggested_action": "建议动作"
        }

        st.dataframe(
            anomaly_df[available_cols].rename(columns=rename_cols),
            use_container_width=True
        )

        st.caption("业务解读：通过异常类型与优先级，可以辅助运营判断哪些类目需要优先复盘和优化。")
    else:
        st.info("暂无异常类目结果。请先运行新版 main.py 生成 anomaly_analysis.csv。")

st.divider()


# ========== 10. NLP 评论分析结果 ==========
st.header("四、NLP 评论分析结果")

fig_col1, fig_col2 = st.columns(2)

with fig_col1:
    st.subheader("评分分布")
    rating_fig = os.path.join(FIGURE_DIR, "rating_distribution.png")
    if os.path.exists(rating_fig):
        st.image(rating_fig, use_container_width=True)
        st.caption("业务解读：评分集中在 4-5 分，整体评价偏正向，但低分评论仍可用于定位关键体验问题。")
    else:
        st.warning("未找到评分分布图，请先运行 main.py。")

with fig_col2:
    st.subheader("情感分布")
    sentiment_fig = os.path.join(FIGURE_DIR, "sentiment_distribution.png")
    if os.path.exists(sentiment_fig):
        st.image(sentiment_fig, use_container_width=True)
        st.caption("业务解读：正向评论占比较高，负向评论主要用于进一步拆解用户痛点并生成运营策略。")
    else:
        st.warning("未找到情感分布图，请先运行 main.py。")


fig_col3, fig_col4 = st.columns(2)

with fig_col3:
    st.subheader("负向评论高频关键词")
    keyword_fig = os.path.join(FIGURE_DIR, "negative_keywords.png")
    if os.path.exists(keyword_fig):
        st.image(keyword_fig, use_container_width=True)
        st.caption("业务解读：负向评论中 size、fabric、fit、small 等词较突出，说明用户痛点集中在尺码适配和面料体验。")
    else:
        st.warning("未找到负向关键词图，请先运行 main.py。")

with fig_col4:
    st.subheader("负向评论主题分布")
    topic_fig = os.path.join(FIGURE_DIR, "negative_topic_distribution.png")
    if os.path.exists(topic_fig):
        st.image(topic_fig, use_container_width=True)
        st.caption("业务解读：一条差评可能同时涉及多个问题，因此采用多标签归因方式，更贴近真实用户反馈场景。")
    else:
        st.warning("未找到主题分布图，请先运行 main.py。")

st.divider()


# ========== 11. 商品类别指标表 ==========
st.header("五、商品类别指标分析")

if "class_metrics" in data:
    class_metrics = data["class_metrics"].copy()

    show_cols = [
        "class_name",
        "review_count",
        "avg_rating",
        "recommend_rate",
        "negative_rate",
        "avg_positive_feedback"
    ]

    available_cols = [c for c in show_cols if c in class_metrics.columns]

    rename_cols = {
        "class_name": "商品类别",
        "review_count": "评论量",
        "avg_rating": "平均评分",
        "recommend_rate": "推荐率",
        "negative_rate": "负向评论占比",
        "avg_positive_feedback": "平均正向反馈数"
    }

    st.dataframe(
        class_metrics[available_cols].head(20).rename(columns=rename_cols),
        use_container_width=True
    )

    st.caption("业务解读：该表用于对比不同商品类别的评论量、平均评分、推荐率和差评率，帮助定位优先优化的商品类目。")
else:
    st.info("暂无类目指标表，请先运行 main.py。")


# ========== 12. 运营策略表 ==========
st.header("六、已有差评主题与运营策略表")

if "strategy" in data:
    strategy_df = data["strategy"].copy()

    rename_map = {
        "negative_topic_cn": "中文主题",
        "problem": "问题描述",
        "operation_strategy": "运营策略",
        "customer_service_reply": "客服话术",
        "review_metrics": "复盘指标"
    }

    display_cols = [c for c in rename_map.keys() if c in strategy_df.columns]
    display_df = strategy_df[display_cols].rename(columns=rename_map)

    st.dataframe(display_df, use_container_width=True)

    with st.expander("查看完整策略表"):
        st.dataframe(strategy_df, use_container_width=True)
else:
    st.info("暂无运营策略表，请先运行 main.py。")


st.divider()

st.markdown(
    """
    **项目定位：**  
    该项目不是训练大模型，而是将 NLP 评论分析结果与异常识别结果结构化为 Prompt 输入，
    结合大模型生成思路模拟 AI 辅助商品运营决策场景。
    """
)