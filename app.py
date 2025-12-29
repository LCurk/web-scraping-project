import streamlit as st
import pandas as pd
import json
from transformers import pipeline

# -------------------------------------------------
# Page configuration
# -------------------------------------------------
st.set_page_config(
    page_title="Scraped Data Explorer",
    layout="wide"
)

st.title("📊 Scraped Data Explorer")

# -------------------------------------------------
# Load scraped data
# -------------------------------------------------
@st.cache_data
def load_data():
    with open("scraped_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

data = load_data()

products_df = pd.DataFrame(data["products"])
testimonials_df = pd.DataFrame(data["testimonials"])
reviews_df = pd.DataFrame(data["reviews"])

# -------------------------------------------------
# Prepare reviews data
# -------------------------------------------------
reviews_df["date"] = pd.to_datetime(reviews_df["date"])
reviews_df["month"] = reviews_df["date"].dt.strftime("%b %Y")

# -------------------------------------------------
# Load Transformer sentiment model
# -------------------------------------------------
@st.cache_resource
def load_sentiment_model():
    return pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english"
    )

sentiment_model = load_sentiment_model()

# -------------------------------------------------
# Sidebar navigation
# -------------------------------------------------
st.sidebar.header("Navigation")

section = st.sidebar.radio(
    "Select section",
    ["Products", "Testimonials", "Reviews"]
)

# -------------------------------------------------
# PRODUCTS
# -------------------------------------------------
if section == "Products":
    st.subheader("🛍 Products")

    products_df["price"] = products_df["price"].str.strip()

    st.dataframe(
        products_df,
        use_container_width=True
    )

# -------------------------------------------------
# TESTIMONIALS
# -------------------------------------------------
elif section == "Testimonials":
    st.subheader("💬 Testimonials")

    st.dataframe(
        testimonials_df.sort_values("rating", ascending=False),
        use_container_width=True
    )

# -------------------------------------------------
# REVIEWS + SENTIMENT + CHARTS
# -------------------------------------------------
elif section == "Reviews":
    st.subheader("⭐ Reviews – Month Filter & Sentiment Analysis (2023)")

    # Ordered months
    months_2023 = (
        reviews_df
        .sort_values("date")["month"]
        .unique()
        .tolist()
    )

    selected_month = st.select_slider(
        "Select month",
        options=months_2023
    )

    filtered_reviews = reviews_df[
        reviews_df["month"] == selected_month
    ].sort_values("date", ascending=False)

    st.markdown(f"### Reviews from **{selected_month}**")

    if filtered_reviews.empty:
        st.info("No reviews found for this month.")
    else:
        # -----------------------------
        # Sentiment analysis
        # -----------------------------
        texts = filtered_reviews["text"].tolist()
        results = sentiment_model(texts)

        filtered_reviews = filtered_reviews.copy()
        filtered_reviews["sentiment"] = [r["label"] for r in results]
        filtered_reviews["confidence"] = [round(r["score"], 3) for r in results]

        # -----------------------------
        # Reviews table
        # -----------------------------
        st.dataframe(
            filtered_reviews[
                ["date", "rating", "sentiment", "confidence", "text"]
            ],
            use_container_width=True
        )

        # -----------------------------
        # Aggregation
        # -----------------------------
        sentiment_summary = (
            filtered_reviews
            .groupby("sentiment")
            .agg(
                count=("sentiment", "count"),
                avg_confidence=("confidence", "mean")
            )
            .reset_index()
        )

        sentiment_summary["avg_confidence"] = (
            sentiment_summary["avg_confidence"].round(3)
        )

        # -----------------------------
        # KPI metrics
        # -----------------------------
        col1, col2 = st.columns(2)

        col1.metric(
            "Positive reviews",
            int(
                sentiment_summary.loc[
                    sentiment_summary["sentiment"] == "POSITIVE", "count"
                ].sum()
            )
        )

        col2.metric(
            "Negative reviews",
            int(
                sentiment_summary.loc[
                    sentiment_summary["sentiment"] == "NEGATIVE", "count"
                ].sum()
            )
        )

        # -----------------------------
        # Bar chart (count)
        # -----------------------------
        st.markdown("### 📊 Sentiment Distribution")

        chart_df = sentiment_summary.set_index("sentiment")
        st.bar_chart(chart_df["count"])

        # -----------------------------
        # Average confidence (Advanced)
        # -----------------------------
        st.markdown("### 🧠 Model Confidence (Average)")
        st.dataframe(
            sentiment_summary,
            use_container_width=True
        )

        st.caption(
            "Confidence score predstavlja povprečno verjetnost modela "
            "za napoved POSITIVE ali NEGATIVE sentimenta."
        )

        st.caption(f"Total reviews shown: {len(filtered_reviews)}")
