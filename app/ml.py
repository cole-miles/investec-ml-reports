import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.linear_model import HuberRegressor
from typing import List, Dict

def remove_daily_outliers(df, method='iqr', k=1.5):
    daily = df.groupby(df['ds'].dt.date)['y'].sum().reset_index()
    daily['ds'] = pd.to_datetime(daily['ds'])

    if method == 'iqr':
        Q1 = daily['y'].quantile(0.25)
        Q3 = daily['y'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - k * IQR
        upper_bound = Q3 + k * IQR
        outliers = daily[(daily['y'] < lower_bound) | (daily['y'] > upper_bound)]
        daily_clean = daily[(daily['y'] >= lower_bound) & (daily['y'] <= upper_bound)]
        print(f"\n[Outlier Removal] IQR method: Removed {len(outliers)} daily outliers.")
        if len(outliers) > 0:
            print("Outlier days removed:")
            for _, row in outliers.iterrows():
                print(f"  {row['ds'].strftime('%Y-%m-%d')}: R{row['y']:,.2f}")
    elif method == 'zscore':
        mean = daily['y'].mean()
        std = daily['y'].std()
        z_scores = np.abs((daily['y'] - mean) / std)
        outliers = daily[z_scores > k]
        daily_clean = daily[z_scores <= k]
        print(f"\n[Outlier Removal] Z-score method: Removed {len(outliers)} daily outliers.")
        if len(outliers) > 0:
            print("Outlier days removed:")
            for _, row in outliers.iterrows():
                print(f"  {row['ds'].strftime('%Y-%m-%d')}: R{row['y']:,.2f}")
    else:
        raise ValueError("Unknown method for outlier removal.")

    return daily_clean

def cap_monthly_outliers(monthly, upper_quantile=0.95):
    upper = monthly['y'].quantile(upper_quantile)
    monthly['y'] = np.clip(monthly['y'], None, upper)
    print(f"\n[Monthly Capping] Capped monthly spend at R{upper:,.2f}")
    return monthly

def prepare_monthly_data(transactions: List[Dict], cap_quantile=0.95):
    df = pd.DataFrame(transactions)
    df['ds'] = pd.to_datetime(df['date'])
    df['y'] = df['amount'].abs()

    daily_clean = remove_daily_outliers(df, method='iqr', k=1.5)

    # Use 'ME' for month-end to avoid deprecation warning
    monthly = daily_clean.groupby(pd.Grouper(key='ds', freq='ME'))['y'].sum().reset_index()
    monthly = monthly.sort_values('ds')
    monthly = monthly.set_index('ds').asfreq('ME').fillna(monthly['y'].median()).reset_index()
    monthly = cap_monthly_outliers(monthly, upper_quantile=cap_quantile)

    print("\n[Monthly Spending Summary] (after daily outlier removal and capping):")
    print(f"Period: {monthly['ds'].min().strftime('%Y-%m')} to {monthly['ds'].max().strftime('%Y-%m')}")
    print(f"Average monthly spending: R{monthly['y'].mean():,.2f}")
    print(f"Median monthly spending: R{monthly['y'].median():,.2f}")
    print(f"Minimum month: R{monthly['y'].min():,.2f}")
    print(f"Maximum month: R{monthly['y'].max():,.2f}")
    print(monthly)
    return monthly

def forecast_holt_winters(monthly, forecast_periods=1):
    model = ExponentialSmoothing(
        monthly['y'],
        trend='add',
        seasonal=None,
        initialization_method='estimated'
    )
    fit = model.fit()
    forecast = fit.forecast(forecast_periods)
    # Confidence interval: use 25th and 75th percentiles of historical data as a proxy
    ci_lower = monthly['y'].quantile(0.25)
    ci_upper = monthly['y'].quantile(0.75)
    print(f"\n[Holt-Winters] Next month forecast: R{forecast.iloc[0]:,.2f}")
    return float(forecast.iloc[0]), float(ci_lower), float(ci_upper)

def create_lagged_features(monthly, lags=3):
    df = monthly.copy()
    for lag in range(1, lags+1):
        df[f'lag_{lag}'] = df['y'].shift(lag)
    df = df.dropna()
    return df

def forecast_robust_regression(monthly, lags=3):
    df = create_lagged_features(monthly, lags)
    if df.empty:
        raise ValueError("Not enough data for robust regression.")
    X = df[[f'lag_{i}' for i in range(1, lags+1)]].values
    y = df['y'].values
    model = HuberRegressor().fit(X, y)
    last_lags = monthly['y'].iloc[-lags:].values[::-1]
    pred = model.predict([last_lags])[0]
    # Confidence interval: use 25th and 75th percentiles of historical data as a proxy
    ci_lower = monthly['y'].quantile(0.25)
    ci_upper = monthly['y'].quantile(0.75)
    print(f"\n[Robust Regression] Next month forecast: R{pred:,.2f}")
    return float(pred), float(ci_lower), float(ci_upper)

def forecast_spending(transactions: List[Dict]):
    monthly = prepare_monthly_data(transactions)
    avg_monthly = float(monthly['y'].mean())
    last_month = float(monthly['y'].iloc[-1]) if len(monthly) > 0 else 0.0

    if len(monthly) < 6:
        print("\n[Fallback] Not enough data, using median.")
        pred = float(monthly['y'].median())
        ci_lower = float(monthly['y'].quantile(0.25))
        ci_upper = float(monthly['y'].quantile(0.75))
        trend_pct = 0.0
        return {
            'predicted_spending': pred,
            'confidence_interval': {
                'lower': ci_lower,
                'upper': ci_upper
            },
            'trend_percentage': trend_pct,
            'average_monthly_spending': avg_monthly
        }

    # Try Exponential Smoothing
    hw_pred, hw_lower, hw_upper = None, None, None
    try:
        hw_pred, hw_lower, hw_upper = forecast_holt_winters(monthly)
    except Exception as e:
        print(f"[Holt-Winters] Error: {e}")

    # Try Robust Regression
    rr_pred, rr_lower, rr_upper = None, None, None
    try:
        rr_pred, rr_lower, rr_upper = forecast_robust_regression(monthly)
    except Exception as e:
        print(f"[Robust Regression] Error: {e}")

    preds = []
    lowers = []
    uppers = []
    if hw_pred is not None and hw_pred > 0:
        preds.append(hw_pred)
        lowers.append(hw_lower)
        uppers.append(hw_upper)
    if rr_pred is not None and rr_pred > 0:
        preds.append(rr_pred)
        lowers.append(rr_lower)
        uppers.append(rr_upper)

    if preds:
        pred = float(np.mean(preds))
        ci_lower = float(np.min(lowers))
        ci_upper = float(np.max(uppers))
        trend_pct = ((pred - last_month) / last_month * 100) if last_month > 0 else 0.0
    else:
        pred = float(monthly['y'].median())
        ci_lower = float(monthly['y'].quantile(0.25))
        ci_upper = float(monthly['y'].quantile(0.75))
        trend_pct = 0.0

    return {
        'predicted_spending': pred,
        'confidence_interval': {
            'lower': ci_lower,
            'upper': ci_upper
        },
        'trend_percentage': trend_pct,
        'average_monthly_spending': avg_monthly
    }