import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import plotly.io as pio
import numpy as np
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

def get_symbol_data(symbol, timeframe, bars=100):
    """
    Get historical data for a symbol using yfinance
    
    Parameters:
    - symbol: Trading symbol (e.g., 'EURUSD')
    - timeframe: String representing time interval ('5m', '1h', '1d')
    - bars: Number of bars (candles) to fetch
    
    Returns:
    - pandas DataFrame with OHLCV data
    """
    # Convert forex pair format to Yahoo Finance format
    if len(symbol) == 6:
        # It's a forex pair, add =X suffix for Yahoo Finance
        yahoo_symbol = f"{symbol[:3]}{symbol[3:]}=X"
    elif symbol == "BTCUSD":
        yahoo_symbol = "BTC-USD"
    else:
        yahoo_symbol = symbol
    
    # Map timeframe to yfinance interval and period
    interval_mapping = {
        'M5': '5m',
        'H1': '1h',
        'D1': '1d'
    }
    
    # Map period based on timeframe and number of bars
    # Yahoo Finance limitations:
    # 1h data: max 730 days
    # 5m data: max 60 days
    # 1d data: much longer history available
    if timeframe == 'M5':
        # For 5m data, Yahoo only provides ~60 days of history
        period = "60d"
    elif timeframe == 'H1':
        # For hourly data, limit to 730 days max
        days = min(730, max(60, int(bars * 1.5)))  # Add buffer but don't exceed limit
        period = f"{days}d"
    else:
        # For daily data, use standard approach
        period = f"{min(1825, max(365, bars*2))}d"  # Limit to 5 years max
    
    # Get data from Yahoo Finance
    try:
        interval = interval_mapping.get(timeframe, '1d')
        df = yf.download(
            yahoo_symbol, 
            period=period, 
            interval=interval, 
            progress=False
        )
        
        # Ensure we have the number of bars requested
        if len(df) > bars:
            df = df.iloc[-bars:]
        
        # Make sure there's data
        if df.empty:
            st.error(f"No data available for {symbol} with timeframe {timeframe}")
            return None
        
        # Handle multi-index columns if present
        if isinstance(df.columns, pd.MultiIndex):
            # First level is usually the column type (Open, High, etc.)
            # We just need the first level for our candlestick chart
            new_df = pd.DataFrame()
            new_df['time'] = df.index
            new_df['open'] = df['Open'].values
            new_df['high'] = df['High'].values
            new_df['low'] = df['Low'].values
            new_df['close'] = df['Close'].values
            
            # Volume may be present but not required
            if 'Volume' in df.columns:
                new_df['volume'] = df['Volume'].values
                
            df = new_df
        else:
            # Reset index to have datetime as a column
            df = df.reset_index()
            
            # Rename columns to standard lowercase format
            column_mapping = {}
            for col in df.columns:
                if col == 'Date' or col == 'Datetime':
                    column_mapping[col] = 'time'
                else:
                    column_mapping[col] = col.lower()
                    
            df = df.rename(columns=column_mapping)
        
        # Check if required columns exist
        required_cols = ['time', 'open', 'high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required columns: {missing_cols}")
            return None
        
        return df
        
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {str(e)}")
        
        # If we get a specific error about timeframe limits, try with a shorter period
        if "The requested range must be within the last" in str(e):
            try:
                # Try with a more conservative period based on the error
                if timeframe == 'H1':
                    st.warning(f"Retrying with a shorter period (365 days) for {symbol}")
                    df = yf.download(
                        yahoo_symbol, 
                        period="365d",  # Conservative 1 year
                        interval=interval, 
                        progress=False
                    )
                elif timeframe == 'M5':
                    st.warning(f"Retrying with a shorter period (30 days) for {symbol}")
                    df = yf.download(
                        yahoo_symbol, 
                        period="30d",  # Conservative 30 days
                        interval=interval, 
                        progress=False
                    )
                
                # Process the data if the retry succeeded
                if df is not None and not df.empty:
                    # Ensure we have the number of bars requested
                    if len(df) > bars:
                        df = df.iloc[-bars:]
                        
                    # Handle multi-index columns if present
                    if isinstance(df.columns, pd.MultiIndex):
                        new_df = pd.DataFrame()
                        new_df['time'] = df.index
                        new_df['open'] = df['Open'].values
                        new_df['high'] = df['High'].values
                        new_df['low'] = df['Low'].values
                        new_df['close'] = df['Close'].values
                        
                        # Volume may be present but not required
                        if 'Volume' in df.columns:
                            new_df['volume'] = df['Volume'].values
                            
                        df = new_df
                    else:
                        # Reset index to have datetime as a column
                        df = df.reset_index()
                        
                        # Rename columns to standard lowercase format
                        column_mapping = {}
                        for col in df.columns:
                            if col == 'Date' or col == 'Datetime':
                                column_mapping[col] = 'time'
                            else:
                                column_mapping[col] = col.lower()
                                
                        df = df.rename(columns=column_mapping)
                    
                    # Check if required columns exist
                    required_cols = ['time', 'open', 'high', 'low', 'close']
                    missing_cols = [col for col in required_cols if col not in df.columns]
                    if missing_cols:
                        st.error(f"Missing required columns: {missing_cols}")
                        return None
                    
                    st.success(f"Successfully fetched {len(df)} bars with reduced time range")
                    return df
            except Exception as retry_error:
                st.error(f"Retry also failed: {str(retry_error)}")
                return None
        return None

def calculate_rsi(data, periods=14):
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    
    # Avoid division by zero
    loss = loss.replace(0, np.nan)
    rs = gain / loss
    rs = rs.fillna(0)
    
    return 100 - (100 / (1 + rs))

def plot_symbol_data(df, symbol, timeframe, visible_bars=None):
    """
    Plot candlestick chart with indicators using plotly
    
    Parameters:
    - df: pandas DataFrame with OHLCV data
    - symbol: Trading symbol
    - timeframe: String representing time interval
    - visible_bars: Number of bars to show in the chart (defaults to all available)
    
    Returns:
    - Plotly figure object
    """
    # Check if we have data
    if df is None or len(df) < 5:  # Need at least a few data points
        st.error(f"Not enough data points for {symbol} with timeframe {timeframe}")
        return None
    
    # Limit the data to the specified number of visible bars
    if visible_bars and visible_bars < len(df):
        chart_df = df.iloc[-visible_bars:]
    else:
        chart_df = df.copy()
        
    # Calculate moving averages and RSI
    chart_df['MA20'] = df['close'].rolling(window=20).mean()  # Use full dataset for better MA calculation
    chart_df['MA50'] = df['close'].rolling(window=50).mean()  # Use full dataset for better MA calculation
    chart_df['RSI'] = calculate_rsi(df)  # Use full dataset for better RSI calculation
    
    # Get current price (last closing price)
    current_price = chart_df['close'].iloc[-1]  # Proper way to get the scalar value

    # Create subplots with secondary y-axis for RSI
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, 
                        row_heights=[0.7, 0.3])

    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=chart_df['time'],
            open=chart_df['open'],
            high=chart_df['high'],
            low=chart_df['low'],
            close=chart_df['close'],
            name=symbol
        ), row=1, col=1
    )

    # Add moving averages
    fig.add_trace(
        go.Scatter(
            x=chart_df['time'],
            y=chart_df['MA20'],
            line=dict(color='yellow', width=1),
            name='20 MA'
        ), row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=chart_df['time'],
            y=chart_df['MA50'],
            line=dict(color='orange', width=1),
            name='50 MA'
        ), row=1, col=1
    )

    # Calculate and add support/resistance
    resistance = chart_df['high'].rolling(window=20).max()
    support = chart_df['low'].rolling(window=20).min()

    fig.add_trace(
        go.Scatter(
            x=chart_df['time'],
            y=resistance,
            line=dict(color='red', width=1, dash='dash'),
            name='Resistance'
        ), row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=chart_df['time'],
            y=support,
            line=dict(color='green', width=1, dash='dash'),
            name='Support'
        ), row=1, col=1
    )

    # Add current price line with dynamic formatting
    if current_price < 1000:
        price_annotation = f"Current Price: {current_price:.5f}"
    else:
        price_annotation = f"Current Price: {current_price:.2f}"
    
    fig.add_hline(
        y=current_price,
        line_width=2,
        line_dash="solid",
        line_color="red",
        annotation=dict(
            text=price_annotation,
            align="left",
            xanchor="left",
            bgcolor="rgba(0,0,0,0.8)",
            font=dict(color="white")
        ),
        row=1,
        col=1
    )

    # Add RSI
    fig.add_trace(
        go.Scatter(
            x=chart_df['time'],
            y=chart_df['RSI'],
            line=dict(color='purple', width=1),
            name='RSI'
        ), row=2, col=1
    )

    # Add RSI overbought/oversold lines
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # Update layout
    title_text = f'{symbol} Candlestick Chart ({timeframe})'
    if visible_bars and visible_bars < len(df):
        title_text += f' - Last {visible_bars} Bars'
        
    fig.update_layout(
        title=title_text,
        yaxis_title='Price',
        yaxis2_title='RSI',
        xaxis_title='Time',
        template='plotly_dark',
        height=800,  # Increased height to accommodate RSI
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(0,0,0,0.5)"
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Rockwell"
        )
    )

    # Update RSI subplot
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)

    # Save the chart as an image
    try:
        filename = f'{symbol}_{timeframe}.png'
        pio.write_image(fig, filename)
    except Exception as e:
        # Try saving with a different backend if kaleido fails
        try:
            # Save as PNG using matplotlib instead
            import matplotlib.pyplot as plt
            from plotly.io import to_image
            
            img_bytes = to_image(fig, format='png')
            with open(filename, 'wb') as f:
                f.write(img_bytes)
        except Exception:
            pass

    return st.plotly_chart(fig, use_container_width=True)
