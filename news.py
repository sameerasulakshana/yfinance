import streamlit as st
from datetime import datetime, timedelta
import requests
import json
import base64
from PIL import Image, ImageDraw

# Initialize API keys
GEMINI_API_KEY = "AIzaSyCNslLSywpb3HPEBZF-Qbjb7APf75wzefQ"
PERPLEXITY_API_KEY = "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"

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
        # Calculate date range (kept for reference)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        # Enhanced search query based on the currency pair
        if len(topic) == 6 and topic in [
            "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD",
            "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD",
            "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD",
            "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD",
            "GBPUSD", "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD",
            "USDCAD", "USDCHF", "USDJPY", "BTCUSD"
        ]:
            # Split the currency pair into base and quote currencies
            base_currency = topic[:3]
            quote_currency = topic[3:]
            
            # Get full names of currencies if available
            base_name = CURRENCY_MAP.get(base_currency, base_currency)
            quote_name = CURRENCY_MAP.get(quote_currency, quote_currency)
            
            # Create a comprehensive query
            query = f"Give me latest news affecting {topic} forex pair, as well as news about {base_name} ({base_currency}) and {quote_name} ({quote_currency}) that could impact their exchange rate. Focus on economic indicators, central bank decisions, and geopolitical events."
        
        elif topic == "BTCUSD":
            query = "Give me latest news affecting Bitcoin (BTC) and US Dollar (USD) that could impact the BTCUSD price. Include cryptocurrency market trends, regulations, and relevant US economic news."
        
        else:
            # Default query for unknown symbols
            query = f"What are the latest news for forex currency pair {topic} in the last 24 hours?"
        
        # Perplexity API endpoint
        url = "https://api.perplexity.ai/chat/completions"
        
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "user", "content": query}
            ],
            "max_tokens": 1000
        }
        
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Add instructions for formatting
        query += " Format each article with Title, Date, Source, and a lot of detailed information."
        payload["messages"][0]["content"] = query
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract content from Perplexity response
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # Parse content to extract articles
            # This is a simple parsing approach - can be improved based on actual response format
            articles = []
            sections = content.split('\n\n')
            
            current_article = {}
            for section in sections:
                if section.startswith('Title:'):
                    # Start of a new article
                    if current_article and 'title' in current_article:
                        articles.append(current_article)
                    current_article = {'title': section.replace('Title:', '').strip()}
                elif 'Date:' in section or 'Published:' in section:
                    for line in section.split('\n'):
                        if line.startswith('Date:'):
                            current_article['date'] = line.replace('Date:', '').strip()
                        elif line.startswith('Published:'):
                            current_article['date'] = line.replace('Published:', '').strip()
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
                    'source': 'Perplexity AI'
                }]
                
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
        
        # Use MT5 timeframe format for image filenames
        timeframe_mapping = {
            'M5': 'M5',
            'H1': 'H1',
            'D1': 'D1'
        }
        
        for timeframe_name in timeframe_mapping.values():
            filename = f'{symbol}_{timeframe_name}.png'
            try:
                img = Image.open(filename)
                img = img.convert('RGB')  # Ensure image is in RGB mode
                
                # Create a drawing object
                draw = ImageDraw.Draw(img)
                
                # Current price line already drawn by MT5 plotting function
                # Just add "Current Price" label if needed for emphasis
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
        
        # Create prompt for Gemini API
        prompt = f"""
        Please analyze the following news articles and technical charts for {symbol}:
        
        NEWS ARTICLES:
        {aggregated_content}
        
        CHARTS:
        The charts show {symbol} price action at multiple timeframes (5 minute, 1 hour, and daily charts).
        The horizontal red line indicates the current price level.
        
        Based on both the news and technical analysis of the charts, please provide:
        1. A summary of key news affecting {symbol}
        2. Technical analysis of the charts
        3. A clear trading recommendation (buy, sell, or hold)
        4. Potential price targets and risk levels
        """
        
        # Prepare the API request for Gemini
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
            }]
        }
        
        # Make the API request
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Extract the generated content from Gemini's response
            if 'candidates' in response_data and len(response_data['candidates']) > 0:
                candidate = response_data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    # Combine all text parts
                    result = ''.join([part.get('text', '') for part in parts if 'text' in part])
                    return result
                else:
                    return "Error: Unable to extract content from API response"
            else:
                return "Error: No candidates in API response"
        else:
            return f"API request failed with status code: {response.status_code}. Response: {response.text}"
            
    except Exception as e:
        return f"Error in analysis: {str(e)}"