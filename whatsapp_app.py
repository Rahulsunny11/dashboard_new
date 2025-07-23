import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import json
import plotly.express as px # Import Plotly Express for charting
# Import column_config for enhanced dataframe customization
from streamlit import column_config

# Custom CSS for overall font and bolding
st.markdown(
    """
    <style>
    html, body, [class*="st-"] {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-weight: normal;
    }
    .st-emotion-cache-10trblm { /* Targets metric labels */
        font-weight: bold !important;
    }
    .st-emotion-cache-1g8p9z { /* Targets metric values */
        font-weight: bold !important;
    }
    /* General bolding for text in markdown */
    strong {
        font-weight: bold !important;
    }
    /* Bold column headers in st.dataframe */
    .st-emotion-cache-nahz7x th {
        font-weight: bold !important;
    }
    /* Removed custom styling for chart titles and containers */
    </style>
    """,
    unsafe_allow_html=True
)

# st.cache_data decorator for caching
@st.cache_data
def load_data():
    chat  = pd.read_csv(r'https://docs.google.com/spreadsheets/d/e/2PACX-1vQC9pyPzVed8E19Ftg7HhgFkIf8hArSRhhfO0u_e7PxluqV2_TnENJOc0uEVWPyN75l49MJbuqERhJC/pub?gid=844866925&single=true&output=csv')
    members = pd.read_csv(r'https://docs.google.com/spreadsheets/d/e/2PACX-1vQC9pyPzVed8E19Ftg7HhgFkIf8hArSRhhfO0u_e7PxluqV2_TnENJOc0uEVWPyN75l49MJbuqERhJC/pub?gid=1894345747&single=true&output=csv')
    msgs = pd.read_csv(r'https://docs.google.com/spreadsheets/d/e/2PACX-1vQC9pyPzVed8E19Ftg7HhgFkIf8hArSRhhfO0u_e7PxluqV2_TnENJOc0uEVWPyN75l49MJbuqERhJC/pub?gid=2112209162&single=true&output=csv')
    reactions = pd.read_csv(r'https://docs.google.com/spreadsheets/d/e/2PACX-1vQC9pyPzVed8E19Ftg7HhgFkIf8hArSRhhfO0u_e7PxluqV2_TnENJOc0uEVWPyN75l49MJbuqERhJC/pub?gid=991085987&single=true&output=csv')
    add_leave = pd.read_csv(r'https://docs.google.com/spreadsheets/d/e/2PACX-1vQC9pyPzVed8E19Ftg7HhgFkIf8hArSRhhfO0u_e7PxluqV2_TnENJOc0uEVWPyN75l49MJbuqERhJC/pub?gid=1838297829&single=true&output=csv')
    return chat, members, msgs, reactions, add_leave

chat, members, msgs, reactions, add_leave = load_data()

# Standardize chat timestamps
chat['chat_created_at'] = pd.to_datetime(chat['chat_created_at'], dayfirst=True, errors='coerce')
chat['date_new'] = chat['chat_created_at'].dt.date
chat['hour'] = chat['chat_created_at'].dt.hour
chat['chat_name'] = chat['chat_name'].str.strip()

# --- MODIFIED: Extract booth number and remove rows with empty booth numbers ---
chat['booth_number'] = chat['chat_name'].str.extract(r'(\d+)$')
# Drop rows where 'booth_number' is NaN (meaning no numeric booth number was extracted)
chat = chat.dropna(subset=['booth_number']).copy()

# --- MODIFIED: Filter out rows with empty chat_name and those containing "#ERROR!" ---
chat = chat[
    (chat['chat_name'] != '') &
    (~chat['chat_name'].str.contains('#ERROR!', na=False))
].copy()

# Infer chat_type for filtering based on user request
# Assuming 'chat_type' column would exist in a real dataset.
# For demonstration, infer from chat_id. Adjust if 'chat_type' is directly in your CSV.
chat['chat_type'] = chat['chat_id'].apply(lambda x: 'group' if '@g.us' in str(x) else 'private')

# Filter only group chats using the new 'chat_type' column
group_chat = chat[chat['chat_type'] == 'group'].copy()

# Members
group_members = members[members['chat_id'].isin(group_chat['chat_id'])]
group_sizes = group_members.groupby('chat_id')['contact_phone_number'].nunique().reset_index(name='count')
group_admins = group_members[group_members['contact_is_admin'] == True].groupby('chat_id')['contact_phone_number'].nunique()

def group_category(row, admin_counts):
    if row['count'] == 1:
        return "2-Way Group"
    elif row['chat_id'] in admin_counts.index and admin_counts.loc[row['chat_id']] >= 1:
        return "Admin Managed Group"
    else:
        return "Multi-Participant Group (No Admin)"

group_sizes['type'] = group_sizes.apply(lambda row: group_category(row, group_admins), axis=1)

# Messages
msgs['timestamp'] = pd.to_datetime(msgs['received_at_date'] + ' ' + msgs['received_at_time'], errors='coerce')
msgs['date_new'] = msgs['timestamp'].dt.date
msgs['hour'] = msgs['timestamp'].dt.hour
msgs['mimetype'] = msgs['media'].apply(lambda x: json.loads(x).get('mimetype') if pd.notnull(x) else 'text')

# Reactions
reactions['timestamp'] = pd.to_datetime(reactions['timestamp'], errors='coerce')
reactions['date_new'] = reactions['timestamp'].dt.date
reactions['hour'] = reactions['timestamp'].dt.hour

# Add/Leave
add_leave['timestamp'] = pd.to_datetime(add_leave['timestamp'], errors='coerce')
add_leave['date_new'] = add_leave['timestamp'].dt.date
add_leave['hour'] = add_leave['timestamp'].dt.hour

# --- Clean IDs for display ---
def clean_id(df, column_name):
    if column_name in df.columns:
        df[column_name] = df[column_name].astype(str).str.replace('@c.us', '').str.replace('@g.us', '')
    return df

members = clean_id(members.copy(), 'contact_phone_number')
msgs = clean_id(msgs.copy(), 'sender_phone')
reactions = clean_id(reactions.copy(), 'sender_id')
# chat_id is used for filtering, so we only clean it for display if needed later, not at source.

# --- Streamlit Dashboard ---
st.set_page_config(page_title="WhatsApp Group Dashboard", layout="wide")
st.title("📱 WhatsApp Group Engagement Dashboard")

# --- Sidebar Filters ---
st.sidebar.header("Filters")

# Date Range Filter
# Find min/max dates across all relevant dataframes
all_dates = pd.concat([
    chat['date_new'].dropna(),
    msgs['date_new'].dropna(),
    reactions['date_new'].dropna(),
    add_leave['date_new'].dropna()
])

min_date = all_dates.min() if not all_dates.empty else datetime.now().date()
max_date = all_dates.max() if not all_dates.empty else datetime.now().date()


filtered_chat = chat
filtered_msgs = msgs
filtered_reactions = reactions
filtered_add_leave = add_leave

if min_date and max_date:
    selected_date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    # Ensure selected_date_range is a tuple of two dates
    if len(selected_date_range) == 2:
        start_date, end_date = selected_date_range
    elif len(selected_date_range) == 1: # If only one date is selected, assume it's both start and end
        start_date = end_date = selected_date_range[0]
    else: # Default to full range if selection is incomplete
        start_date, end_date = min_date, max_date

    # Apply initial date filters
    filtered_chat = chat[(chat['date_new'] >= start_date) & (chat['date_new'] <= end_date)]
    filtered_msgs = msgs[(msgs['date_new'] >= start_date) & (msgs['date_new'] <= end_date)]
    filtered_reactions = reactions[(reactions['date_new'] >= start_date) & (reactions['date_new'] <= end_date)]
    filtered_add_leave = add_leave[(add_leave['date_new'] >= start_date) & (add_leave['date_new'] <= end_date)]
else:
    st.sidebar.warning("No date data available for filtering.")


# Group Name Filter
# Get unique chat names from the initially filtered chat data, dropping NaN values and empty strings before sorting
valid_group_names = [name for name in filtered_chat['chat_name'].dropna().unique().tolist() if str(name).strip() != '']
group_names = ['All Groups'] + sorted(valid_group_names)
selected_group_name = st.sidebar.selectbox("Select Group Name", group_names)

if selected_group_name != 'All Groups':
    # Filter all dataframes based on the selected group name
    filtered_chat = filtered_chat[filtered_chat['chat_name'] == selected_group_name]
    filtered_msgs = filtered_msgs[filtered_msgs['chat_id'].isin(filtered_chat['chat_id'])]
    filtered_reactions = filtered_reactions[filtered_reactions['chat_id'].isin(filtered_chat['chat_id'])]
    filtered_add_leave = filtered_add_leave[filtered_add_leave['chat_id'].isin(filtered_chat['chat_id'])]


# Booth Number Filter
# Get unique booth numbers from the currently filtered chat data, dropping NaN values before sorting
# Convert to string to ensure consistent sorting, then sort
booth_numbers_raw = filtered_chat['booth_number'].dropna().unique().tolist()
# Custom sort for booth numbers: 'N/A' at the end, then numeric sort
def sort_booth_numbers(x):
    if x == 'N/A':
        return (1, x) # Put N/A at the end
    try:
        return (0, int(x)) # Sort numbers numerically
    except ValueError:
        return (0, x) # Fallback for other non-numeric strings

booth_numbers = ['All Booths'] + sorted(booth_numbers_raw, key=sort_booth_numbers)
selected_booth_number = st.sidebar.selectbox("Select Booth Number", booth_numbers)

if selected_booth_number != 'All Booths':
    # Filter all dataframes based on the selected booth number
    filtered_chat = filtered_chat[filtered_chat['booth_number'].astype(str) == selected_booth_number]
    filtered_msgs = filtered_msgs[filtered_msgs['chat_id'].isin(filtered_chat['chat_id'])]
    filtered_reactions = filtered_reactions[filtered_reactions['chat_id'].isin(filtered_chat['chat_id'])]
    filtered_add_leave = filtered_add_leave[filtered_add_leave['chat_id'].isin(filtered_chat['chat_id'])]


# Overview Metrics (using filtered data)
total_groups = filtered_chat['chat_id'].nunique()
# total_participants and unique_participants should ideally be based on members of the *filtered* groups
# This requires re-calculating group_members based on filtered_chat
filtered_group_members = members[members['chat_id'].isin(filtered_chat['chat_id'])]
total_participants = filtered_group_members['contact_phone_number'].count()
unique_participants = filtered_group_members['contact_phone_number'].nunique()

active_participants = filtered_msgs['sender_phone'].nunique()
percent_active = active_participants / total_participants * 100 if total_participants > 0 else 0
groups_with_msgs = filtered_msgs['chat_id'].nunique()
percent_active_groups = groups_with_msgs / total_groups * 100 if total_groups > 0 else 0

st.header("📊 Overview")
col1, col2, col3, col4, col5 = st.columns(5)

# Beautify cards with bold text and colors
card_style = """
    background-color: #F0F2F6; /* Light gray */
    padding: 15px;
    border-radius: 10px;
    text-align: center;
    font-weight: bold;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.1); /* Add subtle shadow */
"""

with col1:
    st.markdown(f"<div style='{card_style} background-color: #E6F7FF; color: #0056B3;'>Total Groups<br><span style='font-size:32px;'>{total_groups}</span></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div style='{card_style} background-color: #FFF0E6; color: #B35900;'>Total Participants<br><span style='font-size:32px;'>{total_participants}</span></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div style='{card_style} background-color: #E6FFEC; color: #008033;'>Unique Participants<br><span style='font-size:32px;'>{unique_participants}</span></div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div style='{card_style} background-color: #F0E6FF; color: #6600B3;'>% Active Participants<br><span style='font-size:32px;'>{percent_active:.2f}%</span></div>", unsafe_allow_html=True)
with col5:
    st.markdown(f"<div style='{card_style} background-color: #FFE6E6; color: #B30000;'>% Active Groups<br><span style='font-size:32px;'>{percent_active_groups:.2f}%</span></div>", unsafe_allow_html=True)


# Create three columns for the charts with explicit widths and gap
chart_col1, chart_col2, chart_col3 = st.columns([1, 1, 1], gap="medium")

with chart_col1:
    # Use st.markdown for title to control wrapping and alignment
    st.markdown("<h3 style='white-space: nowrap; text-align: center; font-size: 18px; font-weight: bold; color: #333333;'>🧠 Group Type Distribution</h3>", unsafe_allow_html=True)
    filtered_group_sizes = filtered_group_members.groupby('chat_id')['contact_phone_number'].nunique().reset_index(name='count')
    filtered_group_admins = filtered_group_members[filtered_group_members['contact_is_admin'] == True].groupby('chat_id')['contact_phone_number'].nunique()
    filtered_group_sizes['type'] = filtered_group_sizes.apply(lambda row: group_category(row, filtered_group_admins), axis=1)

    if not filtered_group_sizes.empty:
        group_type_counts = filtered_group_sizes['type'].value_counts().reset_index()
        group_type_counts.columns = ['Group Type', 'Count']

        if not group_type_counts.empty:
            fig = px.pie(group_type_counts, names='Group Type', values='Count',
                         color_discrete_sequence=["#4C78A8", "#57A773", "#F58518"], # Added more colors for pie
                         hole=0.4) # Donut chart
            fig.update_layout(
                height=320, # Adjusted height
                title_text=None, # Explicitly set title_text to None to remove "undefined"
                margin=dict(t=30, b=30, l=30, r=30), # Adjust margins for pie chart
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5) # Legend at bottom
            )
            # Changed to show only values (numbers)
            fig.update_traces(textposition='inside', textinfo='value')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No group type data available for the selected filters.")
    else:
        st.info("No group type data available for the selected filters.")

with chart_col2:
    # Use st.markdown for title to control wrapping and alignment
    st.markdown("<h3 style='white-space: nowrap; text-align: center; font-size: 18px; font-weight: bold; color: #333333;'>📦 Messages by Type</h3>", unsafe_allow_html=True)
    mimetype_msg_counts = filtered_msgs['mimetype'].value_counts().reset_index()
    mimetype_msg_counts.columns = ['Msg Type', 'Count']

    # Rename mimetype categories for better display
    mimetype_msg_counts['Msg Type'] = mimetype_msg_counts['Msg Type'].replace({
        'text': 'Text',
        'video/mp4': 'Video',
        'image/jpeg': 'Image',
        'audio/mpeg': 'Audio'
    })

    if not mimetype_msg_counts.empty:
        if not mimetype_msg_counts.empty:
            fig = px.bar(mimetype_msg_counts, x='Msg Type', y='Count',
                         color_discrete_sequence=["#57A773", "#4C78A8", "#F58518", "#B30000"])
            fig.update_layout(
                xaxis_title=None, # Removed x-axis title
                yaxis_title=None, # Removed y-axis title
                xaxis_tickfont_color='black', 
                yaxis_tickfont_color='black', 
                height=320, # Adjusted height
                title_text=None # Explicitly set title_text to None to remove "undefined"
            )
            # Changed textposition to 'auto'
            fig.update_traces(texttemplate='%{y}', textposition='auto', textfont=dict(color='black', size=12))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No message Msg Type data available for the selected filters.")
    else:
        st.info("No message Msg Type data available for the selected filters.")

with chart_col3:
    # Use st.markdown for title to control wrapping and alignment
    st.markdown("<h3 style='white-space: nowrap; text-align: center; font-size: 18px; font-weight: bold; color: #333333;'>👍 Reactions by Message Type</h3>", unsafe_allow_html=True)
    if not filtered_reactions.empty and not filtered_msgs.empty:
        reactions_with_mimetype = filtered_reactions.merge(
            filtered_msgs[['message_id', 'mimetype']],
            on='message_id',
            how='inner'
        )
        reactions_mimetype_counts = reactions_with_mimetype['mimetype'].value_counts().reset_index()
        reactions_mimetype_counts.columns = ['Msg Type', 'Reaction Count']

        # Rename mimetype categories for better display in reactions chart
        reactions_mimetype_counts['Msg Type'] = reactions_mimetype_counts['Msg Type'].replace({
            'text': 'Text',
            'video/mp4': 'Video',
            'image/jpeg': 'Image',
            'audio/mpeg': 'Audio'
        })

        if not reactions_mimetype_counts.empty:
            if not reactions_mimetype_counts.empty:
                fig = px.bar(reactions_mimetype_counts, x='Msg Type', y='Reaction Count',
                             color_discrete_sequence=["#F58518", "#57A773", "#4C78A8"])
                fig.update_layout(
                    xaxis_title=None, # Removed x-axis title
                    yaxis_title=None, # Removed y-axis title
                    xaxis_tickfont_color='black',
                    yaxis_tickfont_color='black',
                    height=320, # Adjusted height
                    title_text=None # Explicitly set title_text to None to remove "undefined"
                )
                # Changed textposition to 'auto'
                fig.update_traces(texttemplate='%{y}', textposition='auto', textfont=dict(color='black', size=12))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No reaction Msg Type data available for the selected filters.")
    else:
        st.info("Not enough message or reaction data to show reactions by Msg Type for the selected filters.")


st.header("🚦 Group Health")
st.subheader("Top 5 Most Reacted Messages")
# Engagement & Reactions (using filtered data)
# Merge reactions with messages to get message body and mimetype
reacted_msgs = filtered_reactions.merge(
    filtered_msgs[['message_id', 'message_body', 'mimetype']],
    on='message_id',
    how='inner'
)
# Group by message_id, message_body, mimetype and count reactions
top_reacted_msgs = reacted_msgs.groupby(['message_id', 'message_body', 'mimetype']).size().reset_index(name='No. of Reactions')
top_reacted_msgs = top_reacted_msgs.nlargest(5, 'No. of Reactions')

if not top_reacted_msgs.empty:
    # Rename columns for display
    top_reacted_msgs = top_reacted_msgs.rename(columns={
        'message_body': 'Message',
        'mimetype': 'Msg Type'
    }).drop(columns=['message_id']) # Remove message_id

    # Define column configuration for top_reacted_msgs
    top_reacted_msgs_column_config = {
        "Message": column_config.Column(
            "💬 Message Content",
            help="The content of the message.",
            width="large"
        ),
        "Msg Type": column_config.Column(
            "📄 Message Type",
            help="The type of the message (e.g., text, image, video).",
            width="medium"
        ),
        "No. of Reactions": column_config.Column(
            "👍 Reactions Count",
            help="The total number of reactions received by the message.",
            width="small"
        ),
    }
    st.dataframe(top_reacted_msgs, column_config=top_reacted_msgs_column_config, hide_index=True)
else:
    st.info("No reaction data available for the selected filters.")

st.subheader("Participants Added and Left by Group")
# Added/Left (using filtered data)
added_by_group = filtered_add_leave[filtered_add_leave['type'] == 'add'].groupby('chat_id').size().reset_index(name='Participants Added')
left_by_group = filtered_add_leave[filtered_add_leave['type'] == 'leave'].groupby('chat_id').size().reset_index(name='Participants Left')

# Merge with chat data to get group names and booth numbers
add_leave_summary_df = filtered_chat[['chat_id', 'chat_name', 'booth_number']].drop_duplicates().merge(
    added_by_group, on='chat_id', how='left'
).merge(
    left_by_group, on='chat_id', how='left'
).fillna(0)

# Select and rename columns for display
add_leave_summary_df = add_leave_summary_df.rename(columns={
    'chat_name': 'Group Name',
    'booth_number': 'Booth Number'
}).drop(columns=['chat_id']) # Remove chat_id

# --- NEW: Filter to show groups with 1 or more participants added OR left ---
add_leave_summary_df = add_leave_summary_df[
    (add_leave_summary_df['Participants Added'] >= 1) |
    (add_leave_summary_df['Participants Left'] >= 1)
].copy()


if not add_leave_summary_df.empty:
    # Define column configuration for add_leave_summary_df
    add_leave_summary_column_config = {
        "Group Name": column_config.Column(
            "👥 Group Name",
            help="The name of the WhatsApp group.",
            width="large"
        ),
        "Booth Number": column_config.Column(
            "🎪 Booth Number",
            help="The associated booth number for the group.",
            width="medium"
        ),
        "Participants Added": column_config.Column(
            "➕ Participants Added",
            help="Number of participants added to this group.",
            width="small"
        ),
        "Participants Left": column_config.Column(
            "➖ Participants Left",
            help="Number of participants who left this group.",
            width="small"
        ),
    }
    st.dataframe(add_leave_summary_df, column_config=add_leave_summary_column_config, hide_index=True)
else:
    st.info("No add/leave data available for the selected filters where participants were added or left.")


st.header("🧑‍💼 POC Analysis (Group Admins as POCs)")
# POC Analysis: Consider group admins as POCs
# Get unique admin phone numbers from the filtered group members
poc_phone_numbers = filtered_group_members[filtered_group_members['contact_is_admin'] == True]['contact_phone_number'].unique()

if len(poc_phone_numbers) > 0:
    poc_data = []
    for poc_phone in poc_phone_numbers:
        # Total groups where this admin is present
        total_groups_for_poc = filtered_group_members[
            (filtered_group_members['contact_phone_number'] == poc_phone) &
            (filtered_group_members['contact_is_admin'] == True)
        ]['chat_id'].nunique()

        # Active groups based on messages sent by this POC
        active_groups_for_poc = filtered_msgs[
            filtered_msgs['sender_phone'] == poc_phone
        ]['chat_id'].nunique()

        # Total messages sent by this POC
        total_messages_by_poc = filtered_msgs[
            filtered_msgs['sender_phone'] == poc_phone
        ].shape[0]

        poc_data.append({
            'POC Phone Number': poc_phone,
            'Total Groups (Admin Of)': total_groups_for_poc,
            'Active Groups (Sent Msgs)': active_groups_for_poc,
            'Total Messages Sent': total_messages_by_poc
        })

    poc_summary_df = pd.DataFrame(poc_data)
    # Define column configuration for poc_summary_df
    poc_summary_column_config = {
        "POC Phone Number": column_config.Column(
            "📞 POC Number",
            help="The phone number of the Point of Contact (Group Admin).",
            width="medium"
        ),
        "Total Groups (Admin Of)": column_config.Column(
            "🏘️ Groups Admin Of",
            help="Total number of groups where this POC is an admin.",
            width="small"
        ),
        "Active Groups (Sent Msgs)": column_config.Column(
            "🗣️ Active Groups",
            help="Number of groups where this POC has sent messages.",
            width="small"
        ),
        "Total Messages Sent": column_config.Column(
            "✉️ Total Messages",
            help="Total number of messages sent by this POC.",
            width="small"
        ),
    }
    st.dataframe(poc_summary_df, column_config=poc_summary_column_config, hide_index=True)
else:
    st.info("No POC (Group Admin) data available for the selected filters.")


st.header("📅 Message Sharing Trend in Groups") # Renamed header
tab1, tab2 = st.tabs(["Hour-wise Trend", "Day-wise Trend"])

with tab1:
    st.subheader("Hour-wise Message Trend")
    if not filtered_msgs.empty:
        hour_wise_trend = filtered_msgs.groupby('hour').size().reset_index(name='Message Count')
        hour_wise_trend['hour_label'] = hour_wise_trend['hour'].apply(lambda x: f"{x:02d}:00")

        if not hour_wise_trend.empty:
            fig = px.line(hour_wise_trend, x='hour_label', y='Message Count',
                          title='Hour-wise Message Trend')
            fig.update_layout(
                xaxis_title='Hour',
                xaxis_title_font_color='black', xaxis_tickfont_color='black',
                yaxis_title_font_color='black', yaxis_tickfont_color='black'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No message data available for hour-wise analysis with the selected filters.")
    else:
        st.info("No message data available for hour-wise analysis with the selected filters.")

with tab2:
    st.subheader("Day-wise Message Trend")
    if not filtered_msgs.empty:
        day_wise_trend = filtered_msgs.groupby('date_new').size().reset_index(name='Message Count')
        day_wise_trend['date_new'] = pd.to_datetime(day_wise_trend['date_new']) # Ensure datetime for Plotly

        if not day_wise_trend.empty:
            fig = px.line(day_wise_trend, x='date_new', y='Message Count',
                          title='Day-wise Message Trend')
            fig.update_layout(
                xaxis_title='Date',
                xaxis_title_font_color='black', xaxis_tickfont_color='black',
                yaxis_title_font_color='black', yaxis_tickfont_color='black'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No message data available for day-wise analysis with the selected filters.")
    else:
        st.info("No message data available for day-wise analysis with the selected filters.")
