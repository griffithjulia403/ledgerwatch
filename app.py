import pandas as pd
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files.get('file')

    if file is None or file.filename == '':
        return render_template('index.html', error_message="Please upload a CSV file.")

    try:
        df = pd.read_csv(file)
    except Exception as e:
        return render_template('index.html', error_message=f"Error reading CSV: {e}")

    # Identify the Year column
    year_col = None
    for col in df.columns:
        if col.strip().lower() == "year":
            year_col = col
            break

    if year_col is None:
        return render_template('index.html', error_message="Your CSV must include a 'Year' column.")

    # Preview table
    preview_html = df.head().to_html(classes="table table-sm table-bordered", index=False)

    # Numeric columns except Year
    numeric_df = df.drop(columns=[year_col], errors='ignore').select_dtypes(include='number')

    if numeric_df.empty:
        return render_template(
            'results.html',
            preview_html=preview_html,
            anomalies_html=None,
            anomalous_years=None,
            explanations=None,
            message="No numeric columns found."
        )

    # Year-over-year % change
    pct_change = numeric_df.pct_change() * 100

    # Flag anomalies where any % change > 40%
    threshold = 40
    anomalies_mask = pct_change.abs().max(axis=1) > threshold
    anomalies_df = df[anomalies_mask]

    if anomalies_df.empty:
        return render_template(
            'results.html',
            preview_html=preview_html,
            anomalies_html=None,
            anomalous_years=None,
            explanations=None,
            message="No anomalies detected."
        )

    anomalous_years = anomalies_df[year_col].tolist()
    anomalies_html = anomalies_df.to_html(classes="table table-sm table-bordered", index=False)

    # Build explanations
    explanations = []
    for idx, row in anomalies_df.iterrows():
        year = row[year_col]
        changes = pct_change.loc[idx]

        flagged_cols = changes[changes.abs() > threshold]

        for col, change in flagged_cols.items():
            direction = "increased" if change > 0 else "decreased"
            percent = abs(change)

            # WHY IT MATTERS (simple accounting logic)
            if col.lower() in ["revenue", "sales"]:
                if change > 0:
                    reason = "This may indicate unusually high sales activity, one‑time gains, or aggressive revenue recognition."
                else:
                    reason = "This may indicate declining demand, customer loss, or potential shifts in revenue timing."
            
            elif col.lower() in ["netincome", "net_income", "profit"]:
                if change > 0:
                    reason = "This may reflect one‑time gains, cost changes, or accounting adjustments."
                else:
                    reason = "This may reflect operational losses, write‑downs, or changes in expense reporting."

            elif "liab" in col.lower():
                if change > 0:
                    reason = "This may indicate new debt, liquidity needs, or refinancing activity."
                else:
                    reason = "This may indicate debt repayment or restructuring."

            elif "asset" in col.lower():
                if change > 0:
                    reason = "This may indicate acquisitions or asset growth."
                else:
                    reason = "This may indicate asset sales, write‑downs, or impairment."

            elif "equity" in col.lower():
                if change > 0:
                    reason = "This may indicate retained earnings growth or capital contributions."
                else:
                    reason = "This may indicate losses, dividends, or equity withdrawals."

            else:
                reason = "This metric changed significantly compared to prior years."

            explanations.append(
                f"In {year}, <strong>{col}</strong> {direction} by <strong>{percent:.1f}%</strong>. {reason}"
            )

    return render_template(
        'results.html',
        preview_html=preview_html,
        anomalies_html=anomalies_html,
        anomalous_years=anomalous_years,
        explanations=explanations,
        message="We found unusual year-over-year changes."
    )

if __name__ == '__main__':
    print("LedgerWatch is starting...")
    app.run(debug=True)