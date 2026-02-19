import streamlit as st
import pandas as pd
import chainladder as cl
from datetime import datetime
import pickle
import json
import os
import io

st.set_page_config(layout="wide")
pd.set_option('display.max_columns', None)
pd.options.display.float_format = '{:,.0f}'.format
#pd.options.display.max_rows = 999


# Initialize session state
if "step" not in st.session_state:
    st.session_state.step = 1

if "df" not in st.session_state:
    st.session_state.df = None

# ---- FUNCTIONS TO CHANGE STEPS ----
def next_step():
    if st.session_state.df is not None:
        st.session_state.step += 1
    else:
        st.warning("Please load a file before proceeding.")

def previous_step():
    st.session_state.step -= 1

segments = []

# ---- HELPER FUNCTIONS ----

def format_numeric(df):
    """
    Format all numeric columns in a dataframe with comma separators
    and no decimal places (e.g., 1,234,567).

    Returns a copy of the formatted dataframe.
    """
    df_formatted = df.copy()

    for col in df_formatted.select_dtypes(include=['number']).columns:
        df_formatted[col] = df_formatted[col].apply(lambda x: f"{x:,.0f}")

    return df_formatted


def format_numeric_nans(df):
    """
    Format all numeric columns in a dataframe with comma separators
    and no decimal places (e.g., 1,234,567). Negative values are shown
    in brackets (e.g., -2 -> (2)). Replace NaNs with empty strings.

    Returns a copy of the formatted dataframe.
    """
    df_formatted = df.copy()

    for col in df_formatted.select_dtypes(include=['number']).columns:
        df_formatted[col] = df_formatted[col].apply(
            lambda x: "" if pd.isna(x)
            else (f"({abs(x):,.0f})" if x < 0 else f"{x:,.0f}")
        )

    return df_formatted


def format_four_decimals(df):
    """
    Format all numeric columns in a dataframe with 4 decimal places.
    Negative values are shown in brackets (e.g., -2 -> (2.0000)).
    Replace NaNs with empty strings.

    Returns a copy of the formatted dataframe.
    """
    df_formatted = df.copy()

    for col in df_formatted.select_dtypes(include=['number']).columns:
        df_formatted[col] = df_formatted[col].apply(
            lambda x: "" if pd.isna(x)
            else (f"({abs(x):.4f})" if x < 0 else f"{x:.4f}")
        )

    return df_formatted


def to_month_start(x):
    """
    Convert a date or collection of dates to the first day of the month.
    Works on scalars, lists, Series, and DataFrame columns.
    """
    return pd.to_datetime(x).dt.to_period("M").dt.to_timestamp()


def map_year_min_to_jan1(date_series: pd.Series) -> pd.Series:
    """
    For each year in the datetime series:
      - Find the minimum date
      - Replace it with January 1st of that year
    """
    # Ensure datetime
    ds = pd.to_datetime(date_series)

    # Find min date per year
    min_dates = ds.groupby(ds.dt.year).transform('max')

    # Construct January 1st for each year
    jan1 = pd.to_datetime(ds.dt.year.astype(str) + "-12-31")

    # Replace only the min date in each year
    return ds.where(ds != min_dates, jan1)

def adjust_year_max_to_dec15(date_series: pd.Series) -> pd.Series:
    """
    For each year in the datetime series:
      - Find the maximum date for that year
      - Replace it with Dec 15 of that same year
    Returns a new Series with adjusted dates.
    """
    # Ensure datetime
    ds = pd.to_datetime(date_series)

    # Get max date per year
    max_dates = ds.groupby(ds.dt.year).transform('max')

    # Compute the replacement Dec 15 date for each entry
    dec15 = pd.to_datetime(ds.dt.year.astype(str) + "-12-15")

    # Replace only where date == max date in the year
    return ds.where(ds != max_dates, dec15)



def adjust_quarter_max_to_15th(date_series: pd.Series) -> pd.Series:
    ds = pd.to_datetime(date_series)
    quarters = ds.dt.to_period('Q')
    max_dates = ds.groupby(quarters).transform('max')
    quarter_start = quarters.dt.end_time
    quarter_15th = quarter_start
    return ds.where(ds != max_dates, quarter_15th)


# ============================================================
#                       STEP 1
# ============================================================
if st.session_state.step == 1:
    st.title("Reserving Data Triangles")
    st.header("Step 1: Load Data")

    # File upload
    uploaded_file = st.file_uploader("Upload file")

    df_loaded = None  # Temporary variable for the loaded DataFrame
    if uploaded_file is not None:
        try:
            # Let pandas try to figure it out
            if uploaded_file.name.endswith('.csv'):
                df_loaded = pd.read_csv(uploaded_file)
                df_OS = pd.read_csv(uploaded_file, sheet_name = 'OS')
            elif uploaded_file.name.endswith(('.xls', '.xlsx')):
                df_loaded = pd.read_excel(uploaded_file)
                df_OS = pd.read_excel(uploaded_file, sheet_name = 'OS')
            elif uploaded_file.name.endswith('.json'):
                df_loaded = pd.read_json(uploaded_file)
                df_OS = pd.read_json(uploaded_file, sheet_name = 'OS')
            elif uploaded_file.name.endswith('.parquet'):
                df_loaded = pd.read_parquet(uploaded_file)
                df_OS = pd.read_parquet(uploaded_file, sheet_name = 'OS')
            else:
                st.error("Unsupported file format")
                st.stop()
                
            #st.dataframe(df)
        except Exception as e:
            st.error(f"Error reading file: {e}")


   
    # If a DataFrame was successfully loaded, store in session state and show preview
    if df_loaded is not None:
        st.session_state.df = df_loaded
        st.session_state.df_OS = df_OS
        st.title('Paid')
        st.dataframe(df_loaded.head())
        st.title('OS')
        st.dataframe(df_OS.head())
        st.info("Preview shows the first 5 rows of your file.")

    # -----------------------------
    # Theme Selector (New)
    # -----------------------------
    st.write("---")
    st.subheader("🎨 Theme Selector")

    theme_options = {"Default-Dark":"""
[theme]
# Primary brand color
primaryColor = "#C02739"            # Your red, still the main accent

# Background colors
backgroundColor = "#1B1F2B"         # Dark slate, not too harsh on eyes
secondaryBackgroundColor = "#272D3A" # Slightly lighter for cards/panels

# Text colors
textColor = "#E5E7EB"               # Soft white, high contrast but not glaring
mutedTextColor = "#A0AEC0"          # Gray for secondary info, less harsh

# Accent & UI colors
accentColor = "#3B82F6"             # Blue highlights, links, buttons
successColor = "#34D399"            # Green for success
warningColor = "#FBBF24"            # Yellow for alerts/warnings
errorColor = "#EF4444"              # Red for errors

# Fonts
font = "Inter, sans-serif"          # Modern, readable

# UI polish
cardBorderColor = "#374151"         # Subtle border for panels/cards
cardShadowColor = "rgba(0,0,0,0.4)" # Soft shadow for depth
buttonHoverColor = "#A31B2A"        # Darker red for hover
"""
,
    "Excel": """
[theme]
primaryColor="#1E1E1E"
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#F3F3F3"
textColor="#000000"
font="sans serif"
"""
,    

        "Excel-2": """
[theme]
primaryColor="#217346"
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#F3F3F3"
textColor="#000000"
font="sans serif"
"""
,
        "Light-Blue": """
[theme]
primaryColor="#C02739"
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#E6ECF8"
textColor="#0F0F0F"
font="sans serif"
"""
,
        "Light-Red": """
[theme]
primaryColor = "#3835ebff"              # soft red for header elements
secondaryBackgroundColor = "#f1aeaeff"  # light blue for index / sidebar
textColor = "#000000"
font = "sans serif"
""",
        "Default-Dark-2":"""
[theme]
# Primary brand color
primaryColor = "#E63946"          # Slightly brighter red for more pop

# Background colors
backgroundColor = "#0F172A"       # Keep your deep navy background
secondaryBackgroundColor = "#1A293B"  # Slightly lighter than background for panels/cards

# Text color
textColor = "#F1FAEE"             # Softer white, easier on the eyes

# Accent colors
accentColor = "#A8DADC"           # Light teal for highlights, links, or buttons
warningColor = "#FFBA08"          # Vibrant yellow for alerts or warnings
successColor = "#06D6A0"          # Fresh green for success messages

# Fonts
font = "Inter, sans-serif"        # Modern, readable sans-serif font

# Optional: border and shadow colors for cards
cardBorderColor = "#334155"       # Subtle dark border
cardShadowColor = "rgba(0,0,0,0.4)"  # Slight shadow for depth
""",
        "Neon":"""
[theme]
primaryColor="#F5FF00"
backgroundColor="#0A001A"
secondaryBackgroundColor="#003A4A"
textColor="#E8FFE8"
font="monospace"
""",

        "Seagreen": """
[theme]
primaryColor="#2E8B57"
backgroundColor="#F0FFF0"
secondaryBackgroundColor="#E0F5E0"
textColor="#000000"
""",
        "Dark Red-Blue": """
[theme]
primaryColor="#FF3333"
backgroundColor="#000022"
secondaryBackgroundColor="#111144"
textColor="#FFFFFF"
""",
        "Light Red-Blue": """
[theme]
primaryColor="#FF3333"
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#E3E8FF"
textColor="#000000"
"""
    }

    selected_theme = st.selectbox("Choose Theme", list(theme_options.keys()))

    if st.button("Apply Theme"):
        config_path = os.path.join(".streamlit", "config.toml")
        os.makedirs(".streamlit", exist_ok=True)

        with open(config_path, "w") as f:
            f.write(theme_options[selected_theme])

        st.success("Theme updated! Please refresh the page to see changes.")



    # Next step button (only active if file is loaded)
    st.button("Next ➜", on_click=next_step, disabled=st.session_state.df is None)

    st.info("Allowed file types: `.xlsx`, `.xls`, or `.xlsm`")


# ============================================================
#                       STEP 2
# ============================================================
elif st.session_state.step == 2:
    st.title("Step 2: Reserving Configuration")


    segments = st.session_state.df['Line of Business'].unique().tolist()
    q0 = st.radio("0. Reserving Segment?", segments)
    q1 = st.radio("1. Would you like to use Accident years or Underwriting years?", ["Accident", "Underwriting"])
    q2 = st.radio("2. What type of analysis are you looking for?", ["Gross + RI", "Gross + Net", "Gross"])
    q3 = st.radio("3. Salvage and Subrogation applicable?", ["Yes", "No"])
    ss_choice3 = ""
    if q3 == "Yes":
        ss_choice3 = st.selectbox(
            "Select SS breakup preference:",
            ["Gross and SS separately", "Net of SS"]
        )

    q4 = st.radio("4. Large Claims separately?", ["Yes", "No"])
    threshold, ss_choice4 = 0, ""
    if q4 == "Yes":
        threshold = st.number_input("Enter threshold for large claims:", min_value=0.0, step=1.0)
        ss_choice4 = st.selectbox(
            "What do you want to do with claims above the threshold?",
            ["Cap Claims", "Exclude Claims"]
        )

    q5 = st.radio("5. Reopened Claims?", ["Yes", "No"])
    ss_choice5 = ""
    if q5 == "Yes":
        ss_choice5 = st.selectbox(
            "Select preference:",
            ["Calculate IBNR separately", "All together"]
        )

    q6 = st.radio("6. Policy Measure?", ["Exposures", "Earned Premiums", "Neither"])
    q7 = st.radio("7. ALAE?", ["Yes", "No"])
    ss_choice7 = ""
    if q7 == "Yes":
        ss_choice7 = st.selectbox(
            "Select preference:",
            ["Separate", "All together"]
        )

    q8 = st.radio("8. Tail Factor Aggregation?", ["Yes", "No"])
    q9 = st.radio("9. Do you want Frequency/Severity?", ["Yes", "No"])
    q10 = st.radio("10. Reserving methodology?", ["Paid only", "Paid + Incurred"])
    q11 = st.radio("11. Development period?", ["Yearly", "Quarterly", "Monthly"])



    # -----------------------------
    # Store current selections in session_state
    # -----------------------------

    if "config" in globals() or "config" in locals():
        st.session_state.q0 = st.session_state.get("q0", q0)
        st.session_state.q1 = st.session_state.get("q1", q1)
        st.session_state.q2 = st.session_state.get("q2", q2)
        st.session_state.q3 = st.session_state.get("q3", q3)
        st.session_state.q4 = st.session_state.get("q4", q4)
        st.session_state.q5 = st.session_state.get("q5", q5)
        st.session_state.q6 = st.session_state.get("q6", q6)
        st.session_state.q7 = st.session_state.get("q7", q7)
        st.session_state.q8 = st.session_state.get("q8", q8)
        st.session_state.q9 = st.session_state.get("q9", q9)
        st.session_state.q10 = st.session_state.get("q10", q10)
        st.session_state.q11 = st.session_state.get("q11", q11)

        st.session_state.ss_choice3 = st.session_state.get("ss_choice3", ss_choice3)
        st.session_state.ss_choice4 = st.session_state.get("ss_choice4", ss_choice4)
        st.session_state.ss_choice5 = st.session_state.get("ss_choice5", ss_choice5)
        st.session_state.ss_choice7 = st.session_state.get("ss_choice7", ss_choice7)
        st.session_state.threshold = st.session_state.get("threshold", threshold)
    else:
        st.session_state.q0 = q0
        st.session_state.q1 = q1
        st.session_state.q2 = q2
        st.session_state.q3 = q3
        st.session_state.q4 = q4
        st.session_state.q5 = q5
        st.session_state.q6 = q6
        st.session_state.q7 = q7
        st.session_state.q8 = q8
        st.session_state.q9 = q9
        st.session_state.q10 = q10
        st.session_state.q11 = q11
        st.session_state.ss_choice3 = ss_choice3
        st.session_state.ss_choice4 = ss_choice4
        st.session_state.ss_choice5 = ss_choice5
        st.session_state.ss_choice7 = ss_choice7
        st.session_state.threshold = threshold

        # Display results
    #st.write("---")
    #st.subheader("Selected Options")
    #st.markdown(f"**1. Segment:** {q0}") # Implemented
    #st.markdown(f"**2. Valuation Year:** {q1}") # Needs more clarification
    #st.markdown(f"**3. Analysis Type:** {q2}") # Needs more clarification
    #st.markdown(f"**4. SS:** {q3} {ss_choice3}") # Implemented
    #st.markdown(f"**5. Large Claims:** {q4} {threshold} {ss_choice4}") # Implemented
    #st.markdown(f"**6. Reopened Claims:** {q5} {ss_choice5}") # Yet to be implemented
    #st.markdown(f"**7. Policy Measure:** {q6}") # Needs more clarification
    #st.markdown(f"**8. ALAE:** {q7} {ss_choice7}") # Implemented
    #st.markdown(f"**9. Tail Factor Aggregation:** {q8}") # Needs more clarification
    #st.markdown(f"**10. Frequency/Severity:** {q9}") # Yet to be implemented and maybe needs more clarification
    #st.markdown(f"**11. Reserving Methodology:** {q10}") # Implemented
    #st.markdown(f"**12. Development Period:** {q11}") # Implemented


    st.button("Next ➜", on_click=next_step)




# ----------------------------------------------------
# STEP 2.5 — DISPLAY SELECTED OPTIONS (SUMMARY)
# ----------------------------------------------------
elif st.session_state.step == 3:

    #st.write("---")
    st.title("Step 2.5: Selected Configuration")

    q0 = st.session_state.get("q0", "")
    q1 = st.session_state.get("q1", "Accident")
    q2 = st.session_state.get("q2", "Gross")
    q3 = st.session_state.get("q3", "No")
    ss_choice3 = st.session_state.get("ss_choice3", "")
    q4 = st.session_state.get("q4", "No")
    threshold = st.session_state.get("threshold", 0)
    ss_choice4 = st.session_state.get("ss_choice4", "")
    q5 = st.session_state.get("q5", "No")
    ss_choice5 = st.session_state.get("ss_choice5", "")
    q6 = st.session_state.get("q6", "Neither")
    q7 = st.session_state.get("q7", "No")
    ss_choice7 = st.session_state.get("ss_choice7", "")
    q8 = st.session_state.get("q8", "No")
    q9 = st.session_state.get("q9", "No")
    q10 = st.session_state.get("q10", "Paid only")
    q11 = st.session_state.get("q11", "Yearly")


    data = {
        "No.": list(range(1, 13)),   # 1 to 12
        "Item": [
            "Segment", "Valuation Basis", "Analysis Type", "SS",
            "Large Claims", "Reopened Claims", "Policy Measure",
            "ALAE", "Tail Factor Aggregation", "Freq/Severity",
            "Reserving Methodology", "Development Period"
        ],
        "Selection": [
            q0,
            q1,
            q2,
            "Yes — " + ss_choice3 if q3 == "Yes" else "No",
            f"Yes — Threshold={threshold}, Action={ss_choice4}" if q4 == "Yes" else "No",
            "Yes — " + ss_choice5 if q5 == "Yes" else "No",
            q6,
            "Yes — " + ss_choice7 if q7 == "Yes" else "No",
            q8,
            q9,
            q10,
            q11,
        ]
    }

    df = pd.DataFrame(data)
    df = df.set_index("No.") 

    st.table(df, border=True)




    col1, col2 = st.columns(2)
    with col1:
        st.button("⬅ Back", on_click=previous_step)
    with col2:
        st.button("Next ➜", on_click=next_step)



# ============================================================
#                       STEP 3
# ============================================================
elif st.session_state.step == 4:
    st.title("Step 3: Incremental Triangles")

    

    # All configuration filters below

    st.session_state.alae_df = None
    st.session_state.alae_triangle = None
    st.session_state.large_claims_df = None
    st.session_state.large_claims_triangle = None
    st.session_state.ss_triangle = None
    st.session_state.ri_triangle = None
    st.session_state.net_ri_df = None

    st.session_state.alae_df_OS = None
    st.session_state.alae_triangle_OS = None
    st.session_state.large_claims_df_OS = None
    st.session_state.large_claims_triangle_OS = None
    st.session_state.ss_triangle_OS = None
    st.session_state.ri_triangle_OS = None
    st.session_state.net_ri_df_OS = None



    # 11 (Development Type)
    st.session_state.grain = 'OMDM'
    if st.session_state.q11 == 'Yearly':
        st.session_state.grain =  'OYDY'
    elif st.session_state.q11 == 'Quarterly':
        st.session_state.grain =  'OQDQ'
    
    
    # 0 (Segment)
    filtered_df = st.session_state.df[(st.session_state.df["Line of Business"] == st.session_state.q0)]
    filtered_df_OS = st.session_state.df_OS[(st.session_state.df_OS["Line of Business"] == st.session_state.q0)]

    # 7 (ALAE)
    if st.session_state.q7 == 'Yes' and st.session_state.ss_choice7 == 'Separate':
        st.session_state.alae_df = filtered_df[filtered_df['Claim/LAE'] == 'LAE'].copy()
        if st.session_state.q11 == 'Yearly':
           st.session_state.alae_df['Payment Date'] = adjust_year_max_to_dec15(st.session_state.alae_df['Payment Date'])
        #elif st.session_state.q11 == 'Quarterly':
        #    st.session_state.alae_df['Payment Date'] = adjust_quarter_max_to_15th(st.session_state.alae_df['Payment Date'])           
        filtered_df = filtered_df[filtered_df['Claim/LAE'] == 'Claim']
        
        st.session_state.alae_df_OS = filtered_df_OS[filtered_df_OS['Claim/LAE'] == 'LAE'].copy()
        if st.session_state.q11 == 'Yearly':
            st.session_state.alae_df_OS['Reporting Date'] = adjust_year_max_to_dec15(st.session_state.alae_df_OS['Reporting Date'])
        filtered_df_OS = filtered_df_OS[filtered_df_OS['Claim/LAE'] == 'Claim']

  
    # 5 (Reopened)
    if st.session_state.q5 == 'Yes' and st.session_state.ss_choice5 == 'Calculate IBNR separately':
        st.session_state.reopen_df = filtered_df[filtered_df['Open/Closed/Reopen'] == 'Reopen'].copy()
        filtered_df = filtered_df[filtered_df['Open/Closed/Reopen'] != 'Reopen']
        
        st.session_state.reopen_df_OS = filtered_df_OS[filtered_df_OS['Open/Closed/Reopen'] == 'Reopen'].copy()
        filtered_df_OS = filtered_df_OS[filtered_df_OS['Open/Closed/Reopen'] != 'Reopen']
        

    # 4 (Large Claims)
    if st.session_state.q4 == 'Yes':
        if st.session_state.ss_choice4 == 'Cap Claims':
            filtered_df['Gross Claim Amount Paid as at'] = filtered_df['Gross Claim Amount Paid as at'].apply(
                lambda x: min(x, st.session_state.threshold)
            )
            
            filtered_df_OS['Gross Claim Amount OS as at'] = filtered_df_OS['Gross Claim Amount OS as at'].apply(
                lambda x: min(x, st.session_state.threshold)
            )

        elif st.session_state.ss_choice4 == 'Exclude Claims':
            st.session_state.large_claims_df = filtered_df[filtered_df['Gross Claim Amount Paid as at'] > st.session_state.threshold].copy()
            filtered_df = filtered_df[filtered_df['Gross Claim Amount Paid as at'] <= st.session_state.threshold]

            st.session_state.large_claims_df_OS = filtered_df_OS[filtered_df_OS['Gross Claim Amount OS as at'] > st.session_state.threshold].copy()
            filtered_df_OS = filtered_df_OS[filtered_df_OS['Gross Claim Amount OS as at'] <= st.session_state.threshold]


    # 3 (Salvage and Subrogation)
    option3_name = 'Gross'
    if st.session_state.q3 == 'Yes' and st.session_state.ss_choice3 == 'Gross and SS separately':
        filtered_df['SS'] = filtered_df['Recoveries'] + filtered_df['Subrogation (Individual)'] + filtered_df['Subrogation (Company)']
        st.session_state.ss_triangle = cl.Triangle(data = filtered_df, origin = 'Accident/Treatment Date', development= 'Payment Date', columns = 'SS')
        
        filtered_df_OS['SS'] = filtered_df_OS['Recoveries'] + filtered_df_OS['Subrogation (Individual)'] + filtered_df_OS['Subrogation (Company)']
        st.session_state.ss_triangle_OS = cl.Triangle(data = filtered_df_OS, origin = 'Accident/Treatment Date', development= 'Reporting Date', columns = 'SS')
    
    elif st.session_state.q3 == 'Yes' and st.session_state.ss_choice3 == 'Net of SS':
        filtered_df['Gross Claim Amount Paid as at'] = filtered_df['Gross Claim Amount Paid as at'] - (filtered_df['Recoveries'] + filtered_df['Subrogation (Individual)'] + filtered_df['Subrogation (Company)'])

        filtered_df_OS['Gross Claim Amount OS as at'] = filtered_df_OS['Gross Claim Amount OS as at'] - (filtered_df_OS['Recoveries'] + filtered_df_OS['Subrogation (Individual)'] + filtered_df_OS['Subrogation (Company)'])
        
        option3_name = 'Net of SS'


    # 2 (Reinsurance)
    if st.session_state.q2 == 'Gross + RI':
        filtered_df['RI'] = filtered_df['RI Proportional'] + filtered_df['RI Non Proportional']
        st.session_state.ri_triangle = cl.Triangle(data = filtered_df, origin = 'Accident/Treatment Date', development= 'Payment Date', columns = 'RI')

        filtered_df_OS['RI'] = filtered_df_OS['RI Proportional'] + filtered_df_OS['RI Non Proportional']
        st.session_state.ri_triangle_OS = cl.Triangle(data = filtered_df_OS, origin = 'Accident/Treatment Date', development= 'Reporting Date', columns = 'RI')

    elif st.session_state.q2 == 'Gross + Net':
        st.session_state.net_ri_df = filtered_df.copy()
        st.session_state.net_ri_df['Gross Claim Amount Paid as at'] = filtered_df['Gross Claim Amount Paid as at'] - (filtered_df['RI Proportional'] + filtered_df['RI Non Proportional'])
    
        st.session_state.net_ri_df_OS = filtered_df_OS.copy()
        st.session_state.net_ri_df_OS['Gross Claim Amount OS as at'] = filtered_df_OS['Gross Claim Amount OS as at'] - (filtered_df_OS['RI Proportional'] + filtered_df_OS['RI Non Proportional'])
    

    st.session_state.option3_name = option3_name
    st.session_state.filtered_df = filtered_df
    st.session_state.filtered_df_OS = filtered_df_OS
    #st.session_state.filtered_df = st.session_state.df[(st.session_state.df["Line of Business"] == st.session_state.q0) & (st.session_state.df["Claim/LAE"] == "Claim")]
    
    #triangle = cl.Triangle(data = filtered_df, origin = "Accident/Treatment Date", development = "Payment Date", columns = "Gross Claim Amount Paid as at" ,is_cumulative = False)
    #triangle = triangle.incr_to_cum()
    #st.write(triangle.grains)
    #triangle = triangle.grain(st.session_state.grain)
    #st.session_state.sheet3_triangle = triangle.cum_to_incr()
    #st.session_state.sheet3_df = st.session_state.sheet3_triangle.to_frame(origin_as_datetime = False)
    #st.session_state.sheet3_df = format_numeric(st.session_state.sheet3_df)
    #st.dataframe(st.session_state.sheet3_df)


    # build a dict of possible objects (use the keys you want shown)
    candidates = {
        st.session_state.option3_name: st.session_state.get("filtered_df"),
        "ALAE": st.session_state.get("alae_df"),
        "Reopened Claims": st.session_state.get("reopen_df"),
        "Large Claims": st.session_state.get("large_claims_df"),
        "SS": st.session_state.get("ss_triangle"),
        "RI": st.session_state.get("ri_triangle"),
        "Net of RI": st.session_state.get("net_ri_df"),
    }

    # keep only non-None entries
    available = {name: obj for name, obj in candidates.items() if obj is not None}

    # handle case where nothing is available
    if not available:
        st.sidebar.info("No dataframes or triangles available to display.")
    else:
        choice = st.sidebar.selectbox("Choose dataset to view", list(available.keys()))
        obj = available[choice]

        # ---- Find corresponding _OS version ----
        obj_OS = None
        original_key = next((k for k, v in st.session_state.items() if v is obj), None)
        if original_key:
            obj_OS = st.session_state.get(original_key + "_OS")


        if hasattr(obj, "columns") and hasattr(obj, "dtypes"):
            obj = cl.Triangle(data = obj, origin = "Accident/Treatment Date", development = "Payment Date", columns = "Gross Claim Amount Paid as at" )
            

        # If it's a triangle-like object, convert to frame; otherwise assume it's already a DataFrame
        if hasattr(obj, "to_frame"):
            obj.is_cumulative = False
            obj = obj.grain(st.session_state.grain)
            obj.development = pd.Index([i+1 for i in range(obj.development.size)]) # Make column names the same
            obj_temp = obj.copy()
            df_to_show = obj.to_frame(origin_as_datetime=False)
        else:
            df_to_show = obj.copy() if hasattr(obj, "copy") else obj


        # OS Conditional
        if st.session_state.q10 == "Paid + Incurred":    
            if hasattr(obj_OS, "columns") and hasattr(obj_OS, "dtypes"):
                obj_OS = cl.Triangle(data = obj_OS, origin = "Accident/Treatment Date", development = "Reporting Date", columns = "Gross Claim Amount OS as at" ,is_cumulative = False)

            # If it's a triangle-like object, convert to frame; otherwise assume it's already a DataFrame
            if hasattr(obj_OS, "to_frame"):
                obj_OS.is_cumulative = False
                obj_OS = obj_OS.grain(st.session_state.grain)
                obj_OS.development = pd.Index([i+1 for i in range(obj_OS.development.size)])
                obj_Incurred = obj_OS + obj_temp # This is where OS becomes incurred
                df_to_show_OS = obj_OS.to_frame(origin_as_datetime=False)
                df_to_show_Incurred = obj_Incurred.to_frame(origin_as_datetime=False)
                #df_to_show_OS = df_to_show_OS + df_to_show
            else:
                df_to_show_OS = obj_OS.copy() if hasattr(obj_OS, "copy") else obj_OS


        # Optional: format numeric columns if you have a helper
        try:
            df_to_show = format_numeric_nans(df_to_show)
            if st.session_state.q10 == "Paid + Incurred":
                df_to_show_OS = format_numeric_nans(df_to_show_OS)
                df_to_show_Incurred = format_numeric_nans(df_to_show_Incurred)
        except Exception:
            pass

        st.title('Paid')
        st.dataframe(
            df_to_show,
            column_config={
                col: st.column_config.TextColumn(width="small")
                for col in df_to_show.columns
            }
        )

        if st.session_state.q10 == "Paid + Incurred":
            st.title('OS')
            st.dataframe(
            df_to_show_OS,
            column_config={
                col: st.column_config.TextColumn(width="small")
                for col in df_to_show_OS.columns
            }
        )   

            st.title('Incurred')
            st.dataframe(
            df_to_show_Incurred,
            column_config={
                col: st.column_config.TextColumn(width="small")
                for col in df_to_show_Incurred.columns
            }
        )        

    # Initialize in-memory comments list
    if "comments" not in st.session_state:
        st.session_state.comments = []

    users = ["Primary", "Reviewer", "Appointed Actuary"]
    selected_user = st.selectbox("Select User", users)

    comment_text = st.text_area("Write your comment:")

    if st.button("Submit"):
        if comment_text.strip():
            st.session_state.comments.append({
                "user": selected_user,
                "text": comment_text,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            st.success("Comment added!")
        else:
            st.warning("Comment cannot be empty.")

    # Show comments (in-memory only)
    st.subheader("All Comments")

    if st.session_state.comments:
        for c in st.session_state.comments:
            st.write(f"**{c['user']}** ({c['time']}): {c['text']}")
    else:
        st.write("No comments yet.")


    col1, col2 = st.columns(2)
    with col1:
        st.button("⬅ Back", on_click=previous_step)
    with col2:
        st.button("Next ➜", on_click=next_step)




# ============================================================
#                       STEP 4
# ============================================================
elif st.session_state.step == 5:
    st.title('Step 4: Cummulative Triangles')

    # build a dict of possible objects (use the keys you want shown)
    candidates = {
        st.session_state.option3_name: st.session_state.get("filtered_df"),
        "ALAE": st.session_state.get("alae_df"),
        "Reopened Claims": st.session_state.get("reopen_df"),
        "Large Claims": st.session_state.get("large_claims_df"),
        "SS": st.session_state.get("ss_triangle"),
        "RI": st.session_state.get("ri_triangle"),
        "Net of RI": st.session_state.get("net_ri_df"),
    }

    # keep only non-None entries
    available = {name: obj for name, obj in candidates.items() if obj is not None}

    # handle case where nothing is available
    if not available:
        st.sidebar.info("No dataframes or triangles available to display.")
    else:
        choice = st.sidebar.selectbox("Choose dataset to view", list(available.keys()))
        obj = available[choice]

        # ---- Find corresponding _OS version ----
        obj_OS = None
        original_key = next((k for k, v in st.session_state.items() if v is obj), None)
        if original_key:
            obj_OS = st.session_state.get(original_key + "_OS")


        if hasattr(obj, "columns") and hasattr(obj, "dtypes"):
            obj = cl.Triangle(data = obj, origin = "Accident/Treatment Date", development = "Payment Date", columns = "Gross Claim Amount Paid as at" ,is_cumulative = False)

        # If it's a triangle-like object, convert to frame; otherwise assume it's already a DataFrame
        if hasattr(obj, "to_frame"):
            obj.is_cumulative = False
            obj = obj.incr_to_cum()
            obj = obj.grain(st.session_state.grain)
            obj.development = pd.Index([i+1 for i in range(obj.development.size)])
            obj_temp = obj.copy()

            df_to_show = obj.to_frame(origin_as_datetime=False)
        else:
            df_to_show = obj.copy() if hasattr(obj, "copy") else obj


        # OS Conditional
        if st.session_state.q10 == "Paid + Incurred":    
            if hasattr(obj_OS, "columns") and hasattr(obj_OS, "dtypes"):
                obj_OS = cl.Triangle(data = obj_OS, origin = "Accident/Treatment Date", development = "Reporting Date", columns = "Gross Claim Amount OS as at" ,is_cumulative = False)

            # If it's a triangle-like object, convert to frame; otherwise assume it's already a DataFrame
            if hasattr(obj_OS, "to_frame"):
                obj_OS.is_cumulative = False
                obj_OS = obj_OS.grain(st.session_state.grain)
                obj_OS.development = pd.Index([i+1 for i in range(obj_OS.development.size)])
                obj_Incurred = obj_OS + obj_temp # This is where OS becomes incurred
                df_to_show_OS = obj_OS.to_frame(origin_as_datetime=False)
                df_to_show_Incurred = obj_Incurred.to_frame(origin_as_datetime=False)
                #df_to_show_OS = df_to_show_OS + df_to_show
            else:
                df_to_show_OS = obj_OS.copy() if hasattr(obj_OS, "copy") else obj_OS


        # Optional: format numeric columns if you have a helper
        try:
            df_to_show = format_numeric_nans(df_to_show)
            if st.session_state.q10 == "Paid + Incurred":
                df_to_show_Incurred = format_numeric_nans(df_to_show_Incurred)
                df_to_show_OS = format_numeric_nans(df_to_show_OS)
        except Exception:
            pass

        st.title('Paid')
        st.dataframe(
            df_to_show,
            column_config={
                col: st.column_config.TextColumn(width="small")
                for col in df_to_show.columns
            }
        )

        if st.session_state.q10 == "Paid + Incurred":
            st.title('OS')
            st.dataframe(
            df_to_show_OS,
            column_config={
                col: st.column_config.TextColumn(width="small")
                for col in df_to_show_OS.columns
            }
        )        
            
            st.title('Incurred')
            st.dataframe(
            df_to_show_Incurred,
            column_config={
                col: st.column_config.TextColumn(width="small")
                for col in df_to_show_Incurred.columns
            }
        )        
    
    # Initialize in-memory comments list
    if "comments" not in st.session_state:
        st.session_state.comments = []

    users = ["Primary", "Reviewer", "Appointed Actuary"]
    selected_user = st.selectbox("Select User", users)

    comment_text = st.text_area("Write your comment:")

    if st.button("Submit"):
        if comment_text.strip():
            st.session_state.comments.append({
                "user": selected_user,
                "text": comment_text,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            st.success("Comment added!")
        else:
            st.warning("Comment cannot be empty.")

    # Show comments (in-memory only)
    st.subheader("All Comments")

    if st.session_state.comments:
        for c in st.session_state.comments:
            st.write(f"**{c['user']}** ({c['time']}): {c['text']}")
    else:
        st.write("No comments yet.")


    col1, col2 = st.columns(2)
    with col1:
        st.button("⬅ Back", on_click=previous_step)
    with col2:
        st.button("Next ➜", on_click=next_step)




# ============================================================
#                       STEP 5
# ============================================================
elif st.session_state.step == 6:
    st.title('Step 5: Ratios and Averages')
    st.title('Link Ratios')

    # build a dict of possible objects (use the keys you want shown)
    candidates = {
        st.session_state.option3_name: st.session_state.get("filtered_df"),
        "ALAE": st.session_state.get("alae_df"),
        "Reopened Claims": st.session_state.get("reopen_df"),
        "Large Claims": st.session_state.get("large_claims_df"),
        "SS": st.session_state.get("ss_triangle"),
        "RI": st.session_state.get("ri_triangle"),
        "Net of RI": st.session_state.get("net_ri_df"),
    }

    # keep only non-None entries
    available = {name: obj for name, obj in candidates.items() if obj is not None}

    # handle case where nothing is available
    if not available:
        st.sidebar.info("No dataframes or triangles available to display.")
    else:
        choice = st.sidebar.selectbox("Choose dataset to view", list(available.keys()))
        obj = available[choice]

        # ---- Find corresponding _OS version ----
        obj_OS = None
        original_key = next((k for k, v in st.session_state.items() if v is obj), None)
        if original_key:
            obj_OS = st.session_state.get(original_key + "_OS")


        if hasattr(obj, "columns") and hasattr(obj, "dtypes"):
            obj = cl.Triangle(data = obj, origin = "Accident/Treatment Date", development = "Payment Date", columns = ["Gross Claim Amount Paid as at", "Earned Premiums"] ,is_cumulative = False)

        # If it's a triangle-like object, convert to frame; otherwise assume it's already a DataFrame
        if hasattr(obj, "to_frame"):
            obj.is_cumulative = False
            obj = obj.incr_to_cum()
            obj = obj.grain(st.session_state.grain)
            obj.development = pd.Index([i+1 for i in range(obj.development.size)])
            #obj.valuation = 
            obj_paid_copy = obj.copy()
            obj_temp = obj['Gross Claim Amount Paid as at'].copy()
            obj = obj['Gross Claim Amount Paid as at'].link_ratio
            df_to_show = obj.to_frame(origin_as_datetime=False)
        else:
            df_to_show = obj.copy() if hasattr(obj, "copy") else obj


        # OS Conditional
        if st.session_state.q10 == "Paid + Incurred":    
            if hasattr(obj_OS, "columns") and hasattr(obj_OS, "dtypes"):
                obj_OS = cl.Triangle(data = obj_OS, origin = "Accident/Treatment Date", development = "Reporting Date", columns = ["Gross Claim Amount OS as at","Earned Premiums"] ,is_cumulative = False)

            # If it's a triangle-like object, convert to frame; otherwise assume it's already a DataFrame
            if hasattr(obj_OS, "to_frame"):
                obj_OS.is_cumulative = False
                obj_OS = obj_OS.grain(st.session_state.grain)
                os_dev = obj_OS.development
                obj_OS.development = pd.Index([i+1 for i in range(obj_OS.development.size)])
                obj_Incurred =  obj_OS['Gross Claim Amount OS as at'] + obj_temp # This is where OS becomes incurred
                obj_Incurred.is_cumulative = True # Necessary for proper averages

                # # Step 1: find the minimum valuation date
                # min_val_date = obj_Incurred.valuation.min()

                # dev_numbers = []
                # # Step 2: loop over origin years
                # for year in obj_Incurred.origin:
                #     # filter valuations for this year
                #     vals_this_year = obj_Incurred.valuation[(obj_Incurred.valuation).year == year]
                #     if len(vals_this_year) == 0:
                #         dev_numbers.append(None)  # or np.nan
                #         continue

                #     # Step 3: get the max month for that year
                #     max_date = vals_this_year.max()

                #     # Step 4: compute month distance from min_val_date
                #     diff_months = (max_date.year - min_val_date.year) * 12 + (max_date.month - min_val_date.month + 1)
                #     dev_numbers.append(diff_months)

                # # Step 5: assign to obj_Incurred.development
                # #obj_Incurred.development = dev_numbers

                obj_Incurred1 = obj_Incurred.copy()
                obj_Incurred = obj_Incurred.link_ratio
                df_to_show_Incurred = obj_Incurred.to_frame(origin_as_datetime=False)
            else:
                df_to_show_OS = obj_OS.copy() if hasattr(obj_OS, "copy") else obj_OS


        # Optional: format numeric columns if you have a helper
        try:
            df_to_show = format_four_decimals(df_to_show)
            if st.session_state.q10 == "Paid + Incurred":
                df_to_show_Incurred = format_four_decimals(df_to_show_Incurred)
        except Exception:
            pass

        st.title('Paid')
        st.dataframe(
            df_to_show,
            column_config={
                col: st.column_config.TextColumn(width="small")
                for col in df_to_show.columns
            }
        )


        # n_periods1 = st.number_input(
        # "Select number of periods:",
        # min_value=1,
        # max_value=20,
        # value=2,
        # step=1
        # )

        avg_method1 = st.selectbox(
        "Select averaging method:",
        options=["simple", "regression", "volume"], 
        index=0
        )

        if st.button("Calculate LDF", key = 'avg_method1'):
            #st.write(obj_paid_copy.values.shape)  
            #obj_Incurred1 = obj_Incurred1.iloc[:, :, (n_periods):4, :]
            #st.write(obj_Incurred1.values.shape)
            #st.write(obj_Incurred1)  

            #dev = obj_Incurred1.development.values[-2:]
            #obj_trim = obj_Incurred1.sel(development=dev)

            #st.write(obj_paid_copy['Gross Claim Amount Paid as at'].valuation)
            #st.write(obj_paid_copy['Gross Claim Amount Paid as at'].valuation_date)
            #st.write(obj_paid_copy['Gross Claim Amount Paid as at'].origin)
            model = cl.Development(average=avg_method1).fit(obj_paid_copy['Gross Claim Amount Paid as at']).ldf_
            obj_avg = model.to_frame()

            st.subheader("Calculated LDF:")
            st.dataframe(obj_avg)    

        if st.session_state.q10 == "Paid + Incurred":
            
            st.title('Incurred')
            st.dataframe(
            df_to_show_Incurred,
            column_config={
                col: st.column_config.TextColumn(width="small")
                for col in df_to_show_Incurred.columns
            }
        )        


            # n_periods2 = st.number_input(
            #    "Select number of periods:",
            #    min_value=1,
            #    max_value=20,
            #    value=2,
            #    step=1, key = 'n2'
            # )

            avg_method2 = st.selectbox(
            "Select averaging method:",
            options=["simple", "regression", "volume"],  # add any others supported by chainladder
            index=0,
            key = 'a2'
            )
        

            if st.button("Calculate LDF", key = 'avg_method2'):
                #st.write(obj_Incurred1.shape)  
                #obj_Incurred1 = obj_Incurred1.iloc[:, :, (n_periods):4, :]
                #st.write(obj_Incurred1.values.shape)
                #st.write(obj_Incurred1)  

                #dev = obj_Incurred1.development.values[-2:]
                #obj_trim = obj_Incurred1.sel(development=dev)


                model = cl.Development(average=avg_method2).fit(obj_Incurred1).ldf_
                obj_avg = model.to_frame()

                st.subheader("Calculated LDF:")
                st.dataframe(obj_avg)                  
            

    col1, col2 = st.columns(2)
    with col1:
        st.button("⬅ Back", on_click=previous_step)
    with col2:
        st.button("Finish")