
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import requests
import os

# Set page config FIRST
st.set_page_config(page_title="Indian Stock Dashboard", layout="wide")

# Auto-refresh every 5 minutes (300,000 ms)
st_autorefresh(interval=300000, key="data_refresh")

# Get NewsAPI key (optional)
NEWSAPI_KEY = os.getenv("46896818209f4e10b7e689ea8bc06872")
if not NEWSAPI_KEY:
    NEWSAPI_KEY = st.sidebar.text_input("Enter NewsAPI Key (optional):", type="password")

# Sidebar controls
st.sidebar.header("📊 Dashboard Controls")
ticker_input = st.sidebar.text_input(
    "Enter Indian stock symbols (e.g., RELIANCE.NS, TCS.NS, HDFCBANK.NS):", 
    "RELIANCE.NS, TCS.NS"
)
tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

# Time period options
period_options = {
    '1d': '1d', '5d': '5d', '1mo': '1mo', 
    '3mo': '3mo', '6mo': '6mo', '1y': '1y', '5y': '5y'
}
selected_period = st.sidebar.selectbox("Time period:", list(period_options.keys()), index=2)

# Interval settings
interval_options = {
    '1d': '1m', '5d': '5m', '1mo': '1h', 
    '3mo': '1d', '6mo': '1d', '1y': '1d', '5y': '1wk'
}
selected_interval = interval_options[selected_period]

# Toggle features
show_volume = st.sidebar.checkbox("Show Volume", True)
compare_mode = st.sidebar.checkbox("Comparison Mode", True)

# Price alerts
st.sidebar.header("🔔 Price Alerts")
alert_ticker = st.sidebar.selectbox("Select stock for alert:", tickers)
alert_price = st.sidebar.number_input("Set alert price:", value=0.0)
if st.sidebar.button("Set Alert"):
    st.sidebar.success(f"Alert set for {alert_ticker} at ₹{alert_price:.2f}")

# Main dashboard
st.title("📈 Indian Stock Market Dashboard")
st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

@st.cache_data(ttl=300)  # Cache stock data for 5 minutes
def get_stock_data(tickers, period, interval):
    data = yf.download(tickers, period=period, interval=interval, group_by="ticker", progress=False)
    return data

@st.cache_data(ttl=3600)  # Cache news for 1 hour
def get_news(ticker):
    if not NEWSAPI_KEY:
        return []
    
    try:
        # Get company name for better news search
        stock_info = yf.Ticker(ticker).info
        company_name = stock_info.get("shortName", ticker.split(".")[0])
        
        # Fetch news from the last 7 days
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        url = f"https://newsapi.org/v2/everything?q={company_name} OR {ticker}&from={from_date}&to={to_date}&sortBy=publishedAt&apiKey={NEWSAPI_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            articles = response.json().get("articles", [])
            return articles[:5]  # Top 5 articles
    except Exception as e:
        st.error(f"Error fetching news: {e}")
    return []

def create_stock_chart(ticker, data, show_volume=True):
    if ticker not in data.columns.get_level_values(0):
        st.warning(f"No data for {ticker}")
        return None
    
    ticker_data = data[ticker]
    fig = make_subplots(
        rows=2 if show_volume else 1, 
        cols=1, 
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3] if show_volume else [1.0]
    )
    
    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=ticker_data.index,
            open=ticker_data["Open"],
            high=ticker_data["High"],
            low=ticker_data["Low"],
            close=ticker_data["Close"],
            name=f"{ticker} Price"
        ),
        row=1, col=1
    )
    
    # Volume chart (if enabled)
    if show_volume:
        fig.add_trace(
            go.Bar(
                x=ticker_data.index,
                y=ticker_data["Volume"],
                name=f"{ticker} Volume",
                marker_color="rgba(100, 100, 255, 0.5)"
            ),
            row=2, col=1
        )
    
    # Update layout
    fig.update_layout(
        height=600,
        title=f"{ticker} Stock Price",
        xaxis_rangeslider_visible=False,
        hovermode="x unified"
    )
    
    if show_volume:
        fig.update_yaxes(title_text="Price (₹)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    return fig

def create_comparison_chart(tickers, data, metric="Close"):
    fig = go.Figure()
    
    for ticker in tickers:
        if ticker in data.columns.get_level_values(0):
            ticker_data = data[ticker]
            fig.add_trace(
                go.Scatter(
                    x=ticker_data.index,
                    y=ticker_data[metric],
                    name=ticker,
                    mode="lines"
                )
            )
    
    fig.update_layout(
        height=500,
        title=f"Stock Comparison ({metric})",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        yaxis_title="Price (₹)"
    )
    
    return fig

# Fetch and display data
if tickers:
    try:
        data = get_stock_data(tickers, period_options[selected_period], selected_interval)
        
        if compare_mode:
            # Show comparison chart
            comparison_metric = st.selectbox("Compare by:", ["Close", "Open", "High", "Low", "Volume"])
            st.plotly_chart(
                create_comparison_chart(tickers, data, comparison_metric),
                use_container_width=True
            )
        else:
            # Show individual charts
            for ticker in tickers:
                chart = create_stock_chart(ticker, data, show_volume)
                if chart:
                    st.plotly_chart(chart, use_container_width=True)
                
                # Display news
                st.subheader(f"📰 Latest News for {ticker}")
                news = get_news(ticker)
                if news:
                    for article in news:
                        st.write(f"**{article['title']}**")
                        st.write(f"*{article['source']['name']} - {article['publishedAt'][:10]}*")
                        st.write(article['description'])
                        st.markdown(f"[Read more]({article['url']})")
                        st.write("---")
                else:
                    st.info("No recent news found or NewsAPI key not provided.")
        
        # Current price summary
        st.subheader("💰 Current Prices")
        price_data = []
        for ticker in tickers:
            if ticker in data.columns.get_level_values(0):
                last_close = data[ticker]["Close"].iloc[-1]
                prev_close = data[ticker]["Close"].iloc[-2] if len(data[ticker]) > 1 else last_close
                change = last_close - prev_close
                pct_change = (change / prev_close) * 100
                price_data.append({
                    "Stock": ticker,
                    "Price (₹)": f"{last_close:.2f}",
                    "Change (₹)": f"{change:+.2f}",
                    "% Change": f"{pct_change:+.2f}%",
                    "Trend": "🟢" if change >= 0 else "🔴"
                })
        
        if price_data:
            st.dataframe(pd.DataFrame(price_data), hide_index=True)
        
        # Check alerts
        if alert_price > 0 and alert_ticker in data.columns.get_level_values(0):
            current_price = data[alert_ticker]["Close"].iloc[-1]
            if (current_price >= alert_price and data[alert_ticker]["Close"].iloc[-2] < alert_price) or \
               (current_price <= alert_price and data[alert_ticker]["Close"].iloc[-2] > alert_price):
                st.sidebar.warning(f"🚨 ALERT: {alert_ticker} is now at ₹{current_price:.2f}!")
    
    except Exception as e:
        st.error(f"Error fetching data: {e}")
else:
    st.warning("⚠️ Please enter at least one stock symbol (e.g., RELIANCE.NS, TCS.NS)")