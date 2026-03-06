import streamlit as st
import numpy as np
import numpy_financial as npf
import plotly.graph_objects as go
import pandas as pd

# 1. Page Configuration
st.set_page_config(page_title="Lobito Refinery Dashboard", layout="wide", initial_sidebar_state="expanded")

# 2. Sidebar: Inputs
st.sidebar.header("Macroeconomic Inputs (WACC)")
rf = st.sidebar.slider("US 10-Year Treasury Yield (%)", 0.0, 10.0, 4.30, 0.1) / 100
beta = st.sidebar.slider("Refining Industry Beta", 0.5, 2.0, 1.10, 0.01)
erp = st.sidebar.slider("Equity Risk Premium (%)", 0.0, 10.0, 5.50, 0.1) / 100
crp = st.sidebar.slider("Angola Country Risk Premium (%)", 0.0, 15.0, 7.20, 0.1) / 100

st.sidebar.divider()

st.sidebar.header("Live Stress Variables")
live_cost_of_debt = st.sidebar.slider("Cost of Debt (%)", 3.0, 12.0, 5.0, 0.25) / 100
capex_stress = st.sidebar.slider("CAPEX Overrun/Savings (%)", -20, 40, 0, 5) / 100

# 3. Base Project Parameters
base_capex = 4305.8
base_rev = 11050.0
base_opex = 10260.0
debt_ratio = 0.70
debt_term = 15
tax_rate = 0.25
tax_holiday = 15

# Apply Live Stress
live_capex = base_capex * (1 + capex_stress)
cost_of_equity = rf + (beta * erp) + crp
wacc = ((1 - debt_ratio) * cost_of_equity) + (debt_ratio * live_cost_of_debt)

# 4. Cash Flow Engine Function
def run_model(c_debt, c_capex):
    years = np.arange(2025, 2057)
    n_years = len(years)
    
    # Capex Schedule
    c_sched = np.zeros(n_years)
    c_sched[0:3] = [c_capex*0.2, c_capex*0.4, c_capex*0.4]
    
    # EBITDA
    capacity = np.zeros(n_years)
    capacity[3], capacity[4], capacity[5:] = 0.9, 0.95, 1.0
    ebitda = (capacity * base_rev) - (capacity * base_opex)
    
    # Debt
    t_debt = c_capex * debt_ratio
    pmt = t_debt * (c_debt * (1 + c_debt)**debt_term) / ((1 + c_debt)**debt_term - 1)
    ds, int_arr = np.zeros(n_years), np.zeros(n_years)
    bal = t_debt
    for i in range(n_years):
        if 3 <= i < 18:
            int_arr[i] = bal * c_debt
            ds[i] = pmt
            bal -= (pmt - int_arr[i])
            
    # Taxes & Valuation
    ebt = ebitda - (c_capex/20) - int_arr
    taxes = np.where((years >= 2041) & (ebt > 0), ebt * tax_rate, 0)
    
    fcff = ebitda - c_sched - taxes
    fcf_equity = (ebitda - taxes - ds) - (c_sched * (1 - debt_ratio))
    
    return npf.irr(fcff), npf.irr(fcf_equity), npf.npv(wacc, fcff), np.sum(int_arr)

# 5. Run Base Case
p_irr, e_irr, p_npv, t_int = run_model(live_cost_of_debt, live_capex)

# 6. Dashboard Layout
st.title("Lobito Refinery: Comprehensive Financial Evaluation")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Equity IRR (FIRR)", f"{e_irr*100:.2f}%")
col2.metric("Project IRR", f"{p_irr*100:.2f}%")
col3.metric("Project NPV (MM)", f"${p_npv:,.1f}")
col4.metric("Total Interest (MM)", f"${t_int:,.0f}")

st.divider()

# 7. Sensitivity Matrix (Interest vs CAPEX)
st.subheader("Sensitivity Matrix: Equity IRR (FIRR) %")
st.write("Cross-impact of Interest Rates and CAPEX variations on Sonangol's Return")

interest_range = [0.04, 0.05, 0.06, 0.07, 0.08]
capex_range = [base_capex * 0.9, base_capex, base_capex * 1.1, base_capex * 1.2]

matrix_data = []
for c in capex_range:
    row = []
    for r in interest_range:
        _, firr, _, _ = run_model(r, c)
        row.append(f"{firr*100:.1f}%")
    matrix_data.append(row)

df_sens = pd.DataFrame(matrix_data, 
                       index=[f"CAPEX: {int((c/base_capex-1)*100):+d}%" for c in capex_range],
                       columns=[f"Interest: {r*100:.0f}%" for r in interest_range])
st.table(df_sens)

# 8. Visualizations
c_left, c_right = st.columns(2)
with c_left:
    st.subheader("Debt Amortization Split")
    fig = go.Figure(data=[
        go.Bar(name='Principal', x=years[3:18], y=[(pmt - (total_debt * (live_cost_of_debt * (1 + live_cost_of_debt)**(18-i)) / ((1 + live_cost_of_debt)**(18-i) - 1))) for i in range(3,18)], marker_color='#1F77B4'),
        go.Bar(name='Interest', x=years[3:18], y=[(total_debt * live_cost_of_debt) for i in range(3,18)], marker_color='#AEC7E8')
    ])
    fig.update_layout(barmode='stack', margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

with c_right:
    st.subheader("Leverage Magnification")
    fig_lev = go.Figure(go.Bar(x=['Project IRR', 'Equity IRR (FIRR)'], y=[p_irr*100, e_irr*100], marker_color=['#1F77B4', '#FF7F0E']))
    fig_lev.update_layout(yaxis_title="%", margin=dict(t=20))
    st.plotly_chart(fig_lev, use_container_width=True)