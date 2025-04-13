import streamlit as st
from news import get_news as get_news_perplexity, summarize_articles as summarize_articles_perplexity
from news2 import get_news as get_news_google, summarize_articles as summarize_articles_google
from yfinance_data import get_symbol_data, plot_symbol_data

def main():
    st.set_page_config(page_title="Symbol Analysis", 
                       page_icon="📊",
                       layout="wide")
    
    st.title("📊 Symbol Analysis")
    
    # Initialize session state variables if they don't exist
    if 'current_symbol' not in st.session_state:
        st.session_state.current_symbol = None
    if 'articles' not in st.session_state:
        st.session_state.articles = []
    if 'charts_generated' not in st.session_state:
        st.session_state.charts_generated = False
    if 'news_source' not in st.session_state:
        st.session_state.news_source = "Google"
    if 'chart_data' not in st.session_state:
        st.session_state.chart_data = {}
    if 'ai_summary' not in st.session_state:
        st.session_state.ai_summary = None
    
    # Function to handle symbol selection from buttons
    def select_symbol(sym):
        previous = st.session_state.current_symbol
        if sym != previous:
            st.session_state.current_symbol = sym
            st.session_state.articles = []
            st.session_state.charts_generated = False
            st.session_state.chart_data = {}
            st.session_state.ai_summary = None
    
    # Add symbol buttons at the top, before the main content
    all_symbols = [
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", 
        "AUDUSD", "USDCAD", "NZDUSD", 
        "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", 
        "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", 
        "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", 
        "CADCHF", "CADJPY", "CHFJPY", "NZDCAD", "NZDCHF", "NZDJPY",
        "BTCUSD"
    ]
    
    # Create a top bar for symbols with small buttons
    st.markdown("### Quick Symbol Access")
    
    # Use custom CSS to make buttons smaller and fit content width
    st.markdown("""
        <style>
            div.row-widget.stButton > button {
                padding: 2px 8px;
                font-size: 12px;
                height: auto;
                width: auto !important;
                flex-grow: 0;
                display: inline-block;
                margin: 2px;
            }
            div.stHorizontalBlock {
                flex-wrap: wrap;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Display symbols in horizontal containers with auto-wrapping
    for i in range(0, len(all_symbols), 6):  # Process 6 symbols at a time
        cols = st.columns(6)
        for j in range(6):
            if i + j < len(all_symbols):
                sym = all_symbols[i + j]
                with cols[j]:
                    # Highlight the selected symbol
                    button_style = "primary" if st.session_state.current_symbol == sym else "secondary"
                    if st.button(sym, key=f"topbtn_{sym}", type=button_style):
                        select_symbol(sym)
    
    st.markdown("---")
    
    # Mobile-friendly layout with sidebar toggle
    with st.sidebar:
        st.subheader("Settings")
        news_source = st.radio(
            "News Source:",
            ["Google (with Search Grounding)", "Perplexity"],
            index=0,
            key="news_source_selector"
        )
        
        # Update session state with selected news source
        st.session_state.news_source = "Google" if "Google" in news_source else "Perplexity"
        
        # Add LLM model selection with a key to ensure it's properly tracked
        llm_model = st.selectbox(
            "LLM Model:",
            [
                "gemini-2.5-pro-exp-03-25",
                "gemini-2.0-flash", 
                "gemini-2.0-flash-lite",
                "gemini-1.5-flash",
                "gemini-1.5-flash-8b"
            ],
            index=0,
            key="model_selector"
        )
        
        # Explicitly store the selected model in session state
        st.session_state.selected_model = llm_model
        
        # Chart configuration options
        st.subheader("Chart Settings")
        total_bars = st.select_slider(
            "Bars to fetch:",
            options=[50, 100, 200, 300, 400, 500, 750, 1000],
            value=500  # Default to 500 bars
        )
        
        visible_bars = st.select_slider(
            "Bars to display:",
            options=[25, 50, 75, 100, 150, 200, 300, 'All'],
            value=300
        )
        if visible_bars == 'All':
            visible_bars = None
    
    # Display current symbol prominently if one is selected
    if st.session_state.current_symbol:
        st.markdown(f"## 📊 Current Symbol: {st.session_state.current_symbol}")
        
        # Action buttons in a row - with combined action button
        col1, col2, col3 = st.columns(3)
        with col1:
            load_charts = st.button("📈 Load Charts", use_container_width=True)
        with col2:
            search_button = st.button("📰 Search News", use_container_width=True)
        with col3:
            combined_action = st.button("🚀 Charts & Analysis", use_container_width=True)
    
    # Display AI Summary at the top if available
    if st.session_state.ai_summary:
        st.markdown("## 🤖 AI Analysis and Trading Decision")
        st.markdown(st.session_state.ai_summary)
        st.markdown("---")
    
    # Remove the duplicate symbol buttons section
    # We still need tabs for charts and news
    if st.session_state.current_symbol:  # Only show tabs when a symbol is selected
        tab1, tab2 = st.tabs(["📈 Charts", "📰 News"])
        
        # Tab 1: Charts
        with tab1:
            # Define a function to load charts
            def load_symbol_charts(symbol):
                with st.spinner('Loading charts from Yahoo Finance...'):
                    timeframes = {
                        'M5': 'M5',
                        'H1': 'H1',
                        'D1': 'D1'
                    }
                    
                    success_count = 0
                    for timeframe_name in timeframes.keys():
                        df = get_symbol_data(symbol, timeframe_name, total_bars)
                        if df is not None and not df.empty:
                            if symbol not in st.session_state.chart_data:
                                st.session_state.chart_data[symbol] = {}
                            st.session_state.chart_data[symbol][timeframe_name] = df
                            
                            plot_symbol_data(df, symbol, timeframe_name, visible_bars)
                            success_count += 1
                        else:
                            st.error(f"Failed to get {timeframe_name} data for {symbol}")
                    
                    if success_count > 0:
                        st.session_state.charts_generated = True
                        st.success(f"Successfully generated {success_count} charts for {symbol}")
                        return True
                    else:
                        st.error("Failed to generate any charts. Please try another symbol.")
                        return False
            
            # Define a function to search news and get AI analysis
            def get_news_and_analysis(symbol):
                with st.spinner(f'Fetching news from {st.session_state.news_source}...'):
                    # Choose the news source based on user selection
                    if st.session_state.news_source == "Google":
                        st.session_state.articles = get_news_google(symbol)
                    else:
                        st.session_state.articles = get_news_perplexity(symbol)
                
                articles = st.session_state.articles
                if not articles:
                    st.warning("No news found for this topic.")
                    return False
                
                st.success(f"Found {len(articles)} articles!")
                
                # Summarize all articles with the selected model
                with st.spinner(f'Analyzing news with {st.session_state.selected_model}...'):
                    # Choose the summarization function based on news source
                    if st.session_state.news_source == "Google":
                        summary = summarize_articles_google(articles, symbol, st.session_state.selected_model)
                    else:
                        summary = summarize_articles_perplexity(articles, symbol, st.session_state.selected_model)
                    
                    # Store the summary in session state for display at the top
                    st.session_state.ai_summary = summary
                    return True
            
            # Handle combined action (load charts and get analysis)
            if combined_action:
                symbol = st.session_state.current_symbol
                charts_success = load_symbol_charts(symbol)
                if charts_success:
                    get_news_and_analysis(symbol)
                    # Use st.rerun() instead of experimental_rerun
                    try:
                        st.rerun()  # Use the current method name in newer Streamlit versions
                    except AttributeError:
                        try:
                            st.experimental_rerun()  # Fallback for older Streamlit versions
                        except AttributeError:
                            st.warning("Please refresh the page to see AI analysis at the top")
            
            # Handle load charts button
            elif load_charts:
                load_symbol_charts(st.session_state.current_symbol)
            elif st.session_state.charts_generated and st.session_state.current_symbol in st.session_state.chart_data:
                # If charts were already generated, show them with current visible_bars setting
                for timeframe_name, df in st.session_state.chart_data[st.session_state.current_symbol].items():
                    plot_symbol_data(df, st.session_state.current_symbol, timeframe_name, visible_bars)
            else:
                st.info("Click 'Load Charts' or 'Charts & Analysis' to generate charts for this symbol.")
        
        # Tab 2: News
        with tab2:
            if search_button:
                try:
                    get_news_and_analysis(st.session_state.current_symbol)
                    
                    # Display news articles
                    articles = st.session_state.articles
                    if articles:
                        # Display AI analysis in the news tab
                        st.markdown("### AI Analysis and Trading Decision")
                        st.write(st.session_state.ai_summary)
                        
                        st.markdown("### Recent News Articles")
                        for article in articles:
                            with st.expander(f"📰 {article['title']}"):
                                st.write(f"**Published:** {article.get('date', 'N/A')}")
                                st.write(f"**Source:** {article.get('source', 'N/A')}")
                                st.write(f"**Summary:** {article.get('body', 'No summary available')}")
                                if 'url' in article and article['url']:
                                    st.markdown(f"[Read Full Article]({article['url']})")
                        
                        # Display sources when using Google search grounding
                        if st.session_state.news_source == "Google" and hasattr(st.session_state, 'search_sources') and st.session_state.search_sources:
                            st.markdown("### Sources")
                            for source in st.session_state.search_sources:
                                st.markdown(f"- [{source['title']}]({source['uri']})")
                
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
            elif combined_action:
                # The combined action button already triggered news search
                pass
            else:
                st.info("Click 'Search News' or 'Charts & Analysis' to get the latest news and AI analysis for this symbol.")
    else:
        st.info("👆 Please select a symbol from the buttons above to begin.")

if __name__ == "__main__":
    main()