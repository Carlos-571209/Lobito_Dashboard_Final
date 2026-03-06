import streamlit as st
import numpy as np
import numpy_financial as npf
import plotly.graph_objects as go

# 1. Page Configuration (Must be first)
st.set_page_config(page_title="Lobito Refinery Dashboard", layout="wide", initial_sidebar_state="expanded")

# 2. Sidebar: Inputs & Stress Tests
st.sidebar.header("Macroeconomic Inputs (WACC)")
rf = st.sidebar.slider("US 10-Year Treasury Yield (%)", 0.0, 10.0, 4.30, 0.1) / 100
beta = st.sidebar.slider("Refining Industry Beta", 0.5, 2.0, 1.10, 0.01)
erp = st.sidebar.slider("Equity Risk Premium (%)", 0.0, 10.0, 5.50, 0.1) / 100
crp = st.sidebar.slider("Angola Country Risk Premium (%)", 0.0, 15.0, 7.20, 0.1) / 100

st.sidebar.divider()

st.sidebar.header("Project Stress Tests")
capex_stress = st.sidebar.slider("CAPEX Overrun/Savings (%)", -30, 50, 0, 1) / 100
rev_stress = st.sidebar.slider("Refining Margin Stress (%)", -30, 30, 0, 1) / 100

# 3. Base Project Parameters (The Engine)
base_capex = 4305.8
base_rev = 11050.0
base_opex = 10260.0

# Apply Stress Tests
live_capex = base_capex * (1 + capex_stress)
live_rev = base_rev * (1 + rev_stress)

debt_ratio = 0.70
cost_of_debt = 0.05
debt_term = 15
tax_rate = 0.25
tax_holiday = 15

# Calculate WACC
cost_of_equity = rf + (beta * erp) + crp
wacc = ((1 - debt_ratio) * cost_of_equity) + (debt_ratio * cost_of_debt)

# 4. Cash Flow Timeline Array Generation (32 Years)
years = np.arange(2025, 2057)
n_years = len(years)

capex_schedule = np.zeros(n_years)
capex_schedule[0], capex_schedule[1], capex_schedule[2] = live_capex*0.20, live_capex*0.40, live_capex*0.40

capacity = np.zeros(n_years)
capacity[3], capacity[4], capacity[5:] = 0.90, 0.95, 1.00 

revenues = capacity * live_rev
opex = capacity * base_opex
ebitda = revenues - opex

depreciation = np.zeros(n_years)
depreciation[3:3+20] = live_capex / 20

# Debt Schedule
total_debt = live_capex * debt_ratio
debt_service = np.zeros(n_years)
interest = np.zeros(n_years)

if cost_of_debt == 0:
    pmt = total_debt / debt_term
else:
    pmt = total_debt * (cost_of_debt * (1 + cost_of_debt)**debt_term) / ((1 + cost_of_debt)**debt_term - 1)

balance = total_debt
for i in range(n_years):
    if i >= 3 and i < (3 + debt_term):
        interest[i] = balance * cost_of_debt
        debt_service[i] = pmt
        balance -= (pmt - interest[i])

# Tax & CFADS Schedule
ebt = ebitda - depreciation - interest
taxes = np.zeros(n_years)
for i in range(n_years):
    if i >= 3 and (i - 2) > tax_holiday and ebt[i] > 0:
        taxes[i] = ebt[i] * tax_rate

cfads = ebitda - taxes
fcff = ebitda - capex_schedule - taxes

# DSCR Calculation
dscr_array = np.zeros(n_years)
for i in range(n_years):
    if debt_service[i] > 0:
        dscr_array[i] = cfads[i] / debt_service[i]
min_dscr = np.min(dscr_array[dscr_array > 0]) if np.any(dscr_array > 0) else 0

# Valuation (CORRECTED)
project_npv = npf.npv(wacc, fcff)
project_irr = npf.irr(fcff)

# 5. Main Dashboard Interface
st.title("Lobito Refinery: Project Finance Dashboard")

# Top KPI Banner
col1, col2, col3, col4 = st.columns(4)
col1.metric("Calculated WACC", f"{wacc*100:.2f}%")

if np.isnan(project_irr) or project_irr < 0:
    col2.metric("Project IRR (Unlevered)", "N/M")
else:
    col2.metric("Project IRR (Unlevered)", f"{project_irr*100:.2f}%")

col3.metric("Project NPV (MM USD)", f"${project_npv:,.0f}")

if min_dscr >= 1.25:
    col4.metric("Minimum DSCR", f"{min_dscr:.2f}x", "Bankable", delta_color="normal")
else:
    col4.metric("Minimum DSCR", f"{min_dscr:.2f}x", "High Risk / Breach", delta_color="inverse")

st.divider()

# 6. Interactive Visualizations
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("CFADS vs. Debt Obligations")
    
    chart_years = years[3:18]
    chart_cfads = cfads[3:18]
    chart_debt = debt_service[3:18]
    
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=chart_years, y=chart_cfads, name='CFADS', marker_color='#2CA02C'))
    fig1.add_trace(go.Scatter(x=chart_years, y=chart_debt, name='Debt Service Requirement', mode='lines', line=dict(color='#FF0000', width=3)))
    
    fig1.update_layout(
        xaxis_title="Operating Year",
        yaxis_title="Cash Flow (MM USD)",
        barmode='group',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor='white'
    )
    fig1.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    st.plotly_chart(fig1, use_container_width=True)

with col_chart2:
    st.subheader("Amortization: Principal vs. Interest")
    
    chart_years = years[3:18]
    chart_total_payment = debt_service[3:18]
    chart_interest = interest[3:18]
    chart_principal = chart_total_payment - chart_interest
    
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=chart_years, y=chart_interest, name='Interest', marker_color='#FF7F0E'))
    fig2.add_trace(go.Bar(x=chart_years, y=chart_principal, name='Principal', marker_color='#1F77B4'))
    
    fig2.update_layout(
        xaxis_title="Operating Year",
        yaxis_title="Debt Payment (MM USD)",
        barmode='stack', 
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor='white'
    )
    fig2.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    st.plotly_chart(fig2, use_container_width=True)
