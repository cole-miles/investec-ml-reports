import pandas as pd
import numpy as np
from prophet import Prophet
from datetime import datetime

def remove_outliers(df, z_thresh=2.5):
    """
    Removes rows where 'y' is more than z_thresh standard deviations from the mean.
    Returns both cleaned data and information about removed outliers.
    """
    mean = df['y'].mean()
    std = df['y'].std()
    z_scores = np.abs((df['y'] - mean) / std)

    outliers = df[z_scores >= z_thresh].copy()
    df_clean = df[z_scores < z_thresh].copy()

    print("\nOutlier Detection Results:")
    print(f"Original months: {len(df)}")
    print(f"Months after outlier removal: {len(df_clean)}")
    if len(outliers) > 0:
        print("\nOutlier months removed:")
        for _, row in outliers.iterrows():
            print(f"Date: {row['ds'].strftime('%Y-%m')}, Amount: R{row['y']:,.2f}")

    return df_clean

def cap_outliers(df, upper_quantile=0.95):
    """
    Caps spending at the specified quantile instead of removing outliers.
    """
    upper = df['y'].quantile(upper_quantile)
    original_values = df[df['y'] > upper].copy()
    df.loc[df['y'] > upper, 'y'] = upper

    print("\nOutlier Capping Results:")
    print(f"Capping threshold: R{upper:,.2f}")
    if len(original_values) > 0:
        print("\nCapped months:")
        for _, row in original_values.iterrows():
            print(f"Date: {row['ds'].strftime('%Y-%m')}, Original: R{row['y']:,.2f}, Capped to: R{upper:,.2f}")

    return df

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
    monthly = df.groupby(pd.Grouper(key='ds', freq='ME'))['y'].sum().reset_index()

    # Sort by date
    monthly = monthly.sort_values('ds')

    # Fill any missing months with the mean
    monthly = monthly.set_index('ds').asfreq('ME').fillna(monthly['y'].mean()).reset_index()

    print("\nMonthly Spending Summary:")
    print(f"Period: {monthly['ds'].min().strftime('%Y-%m')} to {monthly['ds'].max().strftime('%Y-%m')}")
    print(f"Average monthly spending: R{monthly['y'].mean():,.2f}")
    print(f"Median monthly spending: R{monthly['y'].median():,.2f}")
    print(f"Minimum month: R{monthly['y'].min():,.2f}")
    print(f"Maximum month: R{monthly['y'].max():,.2f}")

    return monthly

def create_prophet_model(df):
    """
    Creates and fits a Prophet model with appropriate parameters for monthly spending.
    """
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.95,
        growth='linear',
        seasonality_mode='multiplicative'
    )

    model.fit(df)
    return model

def make_forecast(model, df, periods=3):
    """
    Generates a forecast for the next few months.
    Returns both the forecast and some statistics.
    """
    # Make future dataframe for next 3 months
    future = model.make_future_dataframe(periods=periods, freq='ME')

    # Make forecast
    forecast = model.predict(future)

    # Get the last actual value from the original data
    last_actual = df['y'].iloc[-1]

    # Get predictions for future months
    predictions = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)

    # Calculate average monthly spending from original data
    average_spending = df['y'].mean()

    print("\nForecast Summary:")
    print(f"Next month's predicted spending: R{predictions['yhat'].iloc[0]:,.2f}")
    print(f"Confidence interval: R{predictions['yhat_lower'].iloc[0]:,.2f} to R{predictions['yhat_upper'].iloc[0]:,.2f}")

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

    monthly_data = remove_outliers(monthly_data, z_thresh=2.5)

    # Create and fit model
    model = create_prophet_model(monthly_data)

    # Make forecast
    forecast_results = make_forecast(model, monthly_data)

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