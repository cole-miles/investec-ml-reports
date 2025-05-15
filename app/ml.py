import pandas as pd
from prophet import Prophet
from datetime import datetime
import numpy as np

def prepare_monthly_data(transactions):
    """
    Prepares transaction data by aggregating into monthly totals.
    Only considers outgoing transactions (negative amounts).
    """
    # Convert transactions list to DataFrame
    df = pd.DataFrame(transactions)

    # Convert date strings to datetime
    df['ds'] = pd.to_datetime(df['date'])

    # Convert amounts to absolute values (since they're already negative for outgoing)
    df['y'] = df['amount'].abs()

    # Group by month and sum
    monthly = df.groupby(pd.Grouper(key='ds', freq='M'))['y'].sum().reset_index()

    # Sort by date
    monthly = monthly.sort_values('ds')

    # Fill any missing months with 0 or the mean
    monthly = monthly.set_index('ds').asfreq('M').fillna(monthly['y'].mean()).reset_index()

    print("Monthly Data Preview:")
    print(monthly)

    return monthly

def create_prophet_model(df):
    """
    Creates and fits a Prophet model with appropriate parameters for monthly spending.
    """
    model = Prophet(
        # Yearly seasonality for annual patterns (like December spending)
        yearly_seasonality=True,
        # Weekly seasonality doesn't make sense for monthly data
        weekly_seasonality=False,
        # Daily seasonality doesn't make sense for monthly data
        daily_seasonality=False,
        # Higher interval width for more conservative predictions
        interval_width=0.95,
        # Growth can be 'linear' or 'flat' depending on your data
        growth='linear',
        # Seasonality mode can be 'additive' or 'multiplicative'
        seasonality_mode='multiplicative'
    )

    model.fit(df)
    return model

def make_forecast(model, periods=3):
    """
    Generates a forecast for the next few months.
    Returns both the forecast and some statistics.
    """
    # Make future dataframe for next 3 months
    future = model.make_future_dataframe(periods=periods, freq='M')

    # Make forecast
    forecast = model.predict(future)

    # Get the last few actual values and the predictions
    last_actual = forecast['y'].iloc[-periods-1]
    predictions = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)

    # Calculate average monthly spending (from actual data)
    average_spending = forecast['y'].mean()

    return {
        'forecast_df': forecast,
        'predictions': predictions,
        'last_actual': last_actual,
        'average_monthly': average_spending
    }

def forecast_spending(transactions):
    """
    Main function to forecast spending based on transaction history.
    """
    if not transactions:
        raise ValueError("No transactions provided for forecasting")

    # Prepare monthly data
    monthly_data = prepare_monthly_data(transactions)

    if len(monthly_data) < 3:
        raise ValueError("Need at least 3 months of data for forecasting")

    # Create and fit model
    model = create_prophet_model(monthly_data)

    # Make forecast
    forecast_results = make_forecast(model)

    # Get next month's prediction
    next_month_prediction = forecast_results['predictions']['yhat'].iloc[0]

    # Calculate confidence interval
    confidence_lower = forecast_results['predictions']['yhat_lower'].iloc[0]
    confidence_upper = forecast_results['predictions']['yhat_upper'].iloc[0]

    # Calculate trend (percentage change from last actual)
    trend_pct = ((next_month_prediction - forecast_results['last_actual'])
                 / forecast_results['last_actual'] * 100)

    return {
        'predicted_spending': float(next_month_prediction),
        'confidence_interval': {
            'lower': float(confidence_lower),
            'upper': float(confidence_upper)
        },
        'trend_percentage': float(trend_pct),
        'average_monthly_spending': float(forecast_results['average_monthly'])
    }