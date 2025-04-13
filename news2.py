import streamlit as st
from datetime import datetime, timedelta
import requests
import json
import base64
from PIL import Image, ImageDraw
import os

# Initialize API keys
GEMINI_API_KEY = "AIzaSyCNslLSywpb3HPEBZF-Qbjb7APf75wzefQ"

# Currency code to name mapping
CURRENCY_MAP = {
    "USD": "US Dollar",
    "EUR": "Euro",
    "GBP": "British Pound",
    "JPY": "Japanese Yen",
    "AUD": "Australian Dollar",
    "CAD": "Canadian Dollar",
    "CHF": "Swiss Franc",
    "NZD": "New Zealand Dollar",
    "BTC": "Bitcoin"
}

def get_news(topic):
    try:
        # Construct search query based on the currency pair
        if len(topic) == 6 and topic in [
            "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD",
            "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD",
            "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD",
            "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD",
            "GBPUSD", "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD",
            "USDCAD", "USDCHF", "USDJPY"
        ]:
            # Split the currency pair into base and quote currencies
            base_currency = topic[:3]
            quote_currency = topic[3:]
            
            # Get full names of currencies if available
            base_name = CURRENCY_MAP.get(base_currency, base_currency)
            quote_name = CURRENCY_MAP.get(quote_currency, quote_currency)
            
            # Create a search-optimized query
            query = f"Latest financial news about {topic} forex pair and {base_name} {quote_name} exchange rate"
            
        elif topic == "BTCUSD":
            query = "Latest Bitcoin price news and market updates"
        else:
            # Default query for unknown symbols
            query = f"Latest financial news about {topic} trading"
        
        # Call the Gemini API with Google Search grounding
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": f"{query}. Please provide 3-5 recent news articles with title, date, source, and summary for each. Format each as Title: [title] Date: [date] Source: [source] Summary: [detailed summary]"}
                ]
            }],
            "tools": [
                {
                    "google_search": {}
                }
            ]
        }
        
        with st.spinner('Searching for latest news...'):
            response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract content from Gemini response
            content = ""
            if 'candidates' in data and len(data['candidates']) > 0:
                candidate = data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    content = ''.join([part.get('text', '') for part in parts if 'text' in part])
            
            # Parse content to extract articles
            articles = []
            sections = content.split('\n\n')
            
            current_article = {}
            for section in sections:
                if section.startswith('Title:'):
                    # Start of a new article
                    if current_article and 'title' in current_article:
                        articles.append(current_article)
                    current_article = {'title': section.replace('Title:', '').strip()}
                elif 'Date:' in section:
                    for line in section.split('\n'):
                        if line.startswith('Date:'):
                            current_article['date'] = line.replace('Date:', '').strip()
                        elif line.startswith('Source:'):
                            current_article['source'] = line.replace('Source:', '').strip()
                elif 'Summary:' in section:
                    current_article['body'] = section.replace('Summary:', '').strip()
            
            # Add the last article if it exists
            if current_article and 'title' in current_article:
                articles.append(current_article)
                
            # If no structured articles were found, create a single article with the full content
            if not articles:
                articles = [{
                    'title': f'News for {topic}',
                    'body': content,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'source': 'Google Search'
                }]
            
            # Also store grounding information if available
            if 'groundingMetadata' in data['candidates'][0]:
                grounding = data['candidates'][0]['groundingMetadata']
                search_queries = grounding.get('webSearchQueries', [])
                sources = []
                
                if 'groundingChunks' in grounding:
                    for chunk in grounding['groundingChunks']:
                        if 'web' in chunk and 'uri' in chunk['web'] and 'title' in chunk['web']:
                            sources.append({
                                'uri': chunk['web']['uri'],
                                'title': chunk['web']['title']
                            })
                
                # Add sources to session state for reference
                st.session_state.search_sources = sources
                st.session_state.search_queries = search_queries
            
            return articles
            
        else:
            st.error(f"API request failed with status code: {response.status_code}")
            st.error(f"Response content: {response.text}")
            return []
            
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return []

def summarize_articles(articles, symbol, model="gemini-2.5-pro-exp-03-25"):
    try:
        # Aggregate all article bodies into a single string
        aggregated_content = "\n\n".join(f"Title: {article.get('title', 'N/A')}\nPublished: {article.get('date', 'N/A')}\nSource: {article.get('source', 'N/A')}\nSummary: {article.get('body', 'No summary available')}" for article in articles)
        
        # Read and concatenate the images
        images = []
        
        # Use the MT5 timeframe format
        timeframe_mapping = {
            'M5': 'M5',
            'H1': 'H1',
            'D1': 'D1'
        }
        
        for timeframe_name in timeframe_mapping.values():
            filename = f'{symbol}_{timeframe_name}.png'
            try:
                img = Image.open(filename)
                img = img.convert('RGB')
                
                # Create a drawing object
                draw = ImageDraw.Draw(img)
                
                # Current price line already drawn by MT5 plotting function
                # Just add additional emphasis if needed
                line_y = img.height // 2
                draw.rectangle([(5, line_y - 20), (100, line_y + 5)], fill='black')
                draw.text((10, line_y - 15), "Current Price", fill='white')
                
                images.append(img)
            except Exception as e:
                st.error(f"Error processing image {filename}: {str(e)}")
                continue
        
        # Only process if we have images
        if not images:
            return "Error: Could not process chart images for analysis."
        
        # Concatenate images vertically
        widths, heights = zip(*(i.size for i in images))
        total_height = sum(heights)
        max_width = max(widths)
        
        combined_image = Image.new('RGB', (max_width, total_height))
        y_offset = 0
        for img in images:
            combined_image.paste(img, (0, y_offset))
            y_offset += img.height
        
        # Save the combined image
        combined_image.save('combined_chart.png')
        
        # Read and encode the combined image to base64
        with open('combined_chart.png', 'rb') as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create prompt for analysis with Google Search grounding
        prompt = f"""
        Analyze these news articles and technical charts for {symbol}:
        
        NEWS:
        {aggregated_content}
        
        The charts show {symbol} at 5-minute, 1-hour, and daily timeframes.
        The horizontal red line indicates the current price.
        
        Provide:
        1. Key news summary affecting {symbol}
        2. Technical analysis of the charts
        3. Trading recommendation (buy, sell, or hold)
        4. Price targets and risk levels
        """
        
        # Prepare API request with grounding capability
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64_image
                        }
                    }
                ]
            }],
            "tools": [
                {
                    "google_search": {}
                }
            ]
        }
        
        # Make the API request
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Extract the generated content
            if 'candidates' in response_data and len(response_data['candidates']) > 0:
                candidate = response_data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    result = ''.join([part.get('text', '') for part in parts if 'text' in part])
                    
                    # Add grounding information if available
                    if 'groundingMetadata' in candidate:
                        grounding = candidate['groundingMetadata']
                        if 'groundingChunks' in grounding and len(grounding['groundingChunks']) > 0:
                            result += "\n\n### Sources:\n"
                            for chunk in grounding['groundingChunks']:
                                if 'web' in chunk:
                                    result += f"- {chunk['web'].get('title', 'Unnamed Source')}\n"
                    
                    return result
                else:
                    return "Error: Unable to extract content from API response"
            else:
                return "Error: No candidates in API response"
        else:
            return f"API request failed with status code: {response.status_code}. Response: {response.text}"
            
    except Exception as e:
        return f"Error in analysis: {str(e)}"

# For standalone testing
if __name__ == "__main__":
    st.title("News Search with Google Search Grounding")
    
    symbol = st.text_input("Enter symbol (e.g., EURUSD, BTCUSD):", "EURUSD")
    
    if st.button("Get News"):
        articles = get_news(symbol)
        
        if articles:
            st.success(f"Found {len(articles)} articles!")
            
            for article in articles:
                with st.expander(f"📰 {article['title']}"):
                    st.write(f"**Published:** {article.get('date', 'N/A')}")
                    st.write(f"**Source:** {article.get('source', 'N/A')}")
                    st.write(f"**Summary:** {article.get('body', 'No summary available')}")
            
            # Show analysis
            if st.button("Analyze News and Charts"):
                summary = summarize_articles(articles, symbol)
                st.markdown("### AI Analysis and Trading Decision")
                st.write(summary)
                
            # Show search sources if available
            if hasattr(st.session_state, 'search_sources') and st.session_state.search_sources:
                st.markdown("### Search Sources")
                for source in st.session_state.search_sources:
                    st.markdown(f"- [{source['title']}]({source['uri']})")
        else:
            st.warning("No news found for this symbol.")
