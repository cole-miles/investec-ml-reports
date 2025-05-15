# Investec ML Reports

**Investec ML Reports** is a Python-based application that connects to the Investec Programmable Banking API, fetches all outgoing (DEBIT) transactions for a user, stores them in a local database, and uses machine learning (Prophet) to forecast future monthly spending. The project is built with FastAPI, SQLAlchemy, and Prophet, and is designed for easy deployment and extensibility.

---

## Features

- **Full Transaction Fetching:**
  Fetches all DEBIT transactions from an Investec account, handling pagination and date ranges to ensure complete history.

- **Data Storage:**
  Stores users and their transactions in a local SQLite database using SQLAlchemy. (Postgres will be used when final version is released)

- **Monthly Aggregation:**
  Aggregates transactions into monthly totals for analysis and forecasting.

- **Outlier Handling:**
  Detects and removes (or caps) outlier months to improve the accuracy of forecasts.

- **Machine Learning Forecast:**
  Uses Facebook Prophet to predict next month’s spending, providing a confidence interval and trend analysis.

- **REST API:**
  FastAPI endpoints for:
    - Creating users
    - Fetching and saving transactions
    - Generating spending forecasts
    - Deleting users and all their data

---

## Quickstart

Will update once production version is released.

## API Endpoints

- `POST /users/`
  Create a new user.

- `POST /users/{user_id}/transactions/`
  Fetch all DEBIT transactions for the user and save them to the database (shows progress in logs).

- `GET /users/{user_id}/report`
  Generate a monthly spending forecast for the user, with outlier handling and trend analysis.

- `DELETE /users/{user_id}`
  Delete a user and all their transactions.

---

## Example Output

```json
{
  "next_month_forecast": {
    "amount": 29774.03,
    "confidence_interval": {
      "lower": 29681.89,
      "upper": 29850.44
    }
  },
  "trend": {
    "percentage": 4.9,
    "direction": "up"
  },
  "historical": {
    "average_monthly": 11145.94
  }
}
```

---

## Future Features

- **Transaction Categorization:**
  Automatic categorization of transactions (e.g., groceries, rent, entertainment) using ML/NLP.

- **User Notifications:**
  Email or push notifications for monthly reports, budget warnings, or unusual spending.

- **Web Dashboard:**
  Interactive dashboard for users to view their spending history, forecasts, and insights.

- **Budget Recommendations:**
  Personalized budget suggestions and alerts based on spending patterns.

- **Anomaly Detection:**
  Highlighting months with unusual or suspicious activity.

- **Multi-user Support:**
  OAuth or other secure authentication for multiple users.

- **Cloud Deployment:**
  One-click deployment to Render.com or similar platforms, with scheduled background jobs.

- **Advanced Forecasting:**
  Support for alternative models (e.g., ARIMA, LSTM) and comparison of forecast accuracy.

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

---

## License

MIT License

---

## Acknowledgements

- [Investec Programmable Banking](https://developer.investec.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Prophet](https://facebook.github.io/prophet/)
- [SQLAlchemy](https://www.sqlalchemy.org/)

---

**Questions?**
Open an issue or contact the maintainer.