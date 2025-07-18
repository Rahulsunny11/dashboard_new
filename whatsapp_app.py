import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import json

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
chat['booth_number'] = chat['chat_name'].str.extract(r'(\d+)$')

chat['chat_id'] = chat['chat_id'].astype(str).str.replace('@c.us', '', regex=False)
members['chat_id'] = members['chat_id'].astype(str).str.replace('@c.us', '', regex=False)
msgs['chat_id'] = msgs['chat_id'].astype(str).str.replace('@c.us', '', regex=False)
msgs['sender_phone'] = msgs['sender_phone'].astype(str).str.replace('@c.us', '', regex=False)
reactions['sender_id'] = reactions['sender_id'].astype(str).str.replace('@c.us', '', regex=False)
add_leave['author'] = add_leave['author'].astype(str).str.replace('@c.us', '', regex=False)

chat['chat_id'] = chat['chat_id'].astype(str).str.replace('@g.us', '', regex=False)
members['chat_id'] = members['chat_id'].astype(str).str.replace('@g.us', '', regex=False)
msgs['chat_id'] = msgs['chat_id'].astype(str).str.replace('@g.us', '', regex=False)
msgs['sender_phone'] = msgs['sender_phone'].astype(str).str.replace('@g.us', '', regex=False)
reactions['sender_id'] = reactions['sender_id'].astype(str).str.replace('@g.us', '', regex=False)
add_leave['author'] = add_leave['author'].astype(str).str.replace('@g.us', '', regex=False)

# Filter only group chats
group_chat = chat[chat['chat_type']=='group']

# Members
group_members = members[members['chat_id'].isin(group_chat['chat_id'])]
group_sizes = group_members.groupby('chat_id')['contact_phone_number'].nunique().reset_index(name='count')
group_admins = group_members[group_members['contact_is_admin'] == True].groupby('chat_id')['contact_phone_number'].nunique()

def group_category(row):
    if row['count'] == 1:
        return "Single"
    elif row['chat_id'] in group_admins[group_admins >= 1].index:
        return "Admin Managed"
    else:
        return "2-way"

group_sizes['type'] = group_sizes.apply(group_category, axis=1)

# Messages\msgs['timestamp'] = pd.to_datetime(msgs['received_at_date'] + ' ' + msgs['received_at_time'], errors='coerce')
#msgs['date_new'] = msgs['received_at_date'].dt.date
#msgs['hour'] = msgs['received_at_time'].dt.hour
msgs['timestamp'] = pd.to_datetime(msgs['received_at_date'] + ' ' + msgs['received_at_time'], errors='coerce')
msgs['date_new'] = msgs['timestamp'].dt.date
msgs['hour'] = msgs['timestamp'].dt.hour

# Extract mimetype from media column
msgs['mimetype'] = msgs['media'].apply(lambda x: json.loads(x).get('mimetype') if pd.notnull(x) else 'text')

# Reactions
reactions['timestamp'] = pd.to_datetime(reactions['timestamp'], errors='coerce')
reactions['date_new'] = reactions['timestamp'].dt.date
reactions['hour'] = reactions['timestamp'].dt.hour

# Add/Leave
add_leave['timestamp'] = pd.to_datetime(add_leave['timestamp'], errors='coerce')
add_leave['date_new'] = add_leave['timestamp'].dt.date
add_leave['hour'] = add_leave['timestamp'].dt.hour

# Overview Metrics
total_groups = group_chat['chat_id'].nunique()
total_participants = group_members['contact_phone_number'].count()
unique_participants = group_members['contact_phone_number'].nunique()
active_participants = msgs['sender_phone'].nunique()
percent_active = active_participants / total_participants * 100
groups_with_msgs = msgs['chat_id'].nunique()
percent_active_groups = groups_with_msgs / total_groups * 100

# Engagement & Reactions
engagement = reactions['sender_id'].nunique() / total_participants * 100
top_reacted = reactions.groupby('chat_id').size().nlargest(5)

# Added/Left
added = add_leave[add_leave['type'] == 'add'].groupby('chat_id').size()
left = add_leave[add_leave['type'] == 'leave'].groupby('chat_id').size()

# Mimetype Insights
mimetype_msg_counts = msgs['mimetype'].value_counts()
reactions_mimetype = msgs.merge(reactions, on='message_id', how='left').groupby('mimetype').size()

# POC Mapping (Dummy Mapping, replace with actual mapping)
poc_map = {'919895820344@c.us': 'POC 1', '919946889891@c.us': 'POC 2'}
msgs['POC'] = msgs['sender_phone'].map(poc_map)
reactions['POC'] = reactions['sender_id'].map(poc_map)

if 'chat_id' in msgs.columns and 'message_id' in msgs.columns:
    poc_summary = msgs.groupby('POC').agg({
        'chat_id': pd.Series.nunique,
        'message_id': 'count'
    }).rename(columns={'chat_id': 'Active Groups', 'message_id': 'Messages'})
else:
    poc_summary = pd.DataFrame(columns=['Active Groups', 'Messages'])


# Time Series

def bucket_time(hour):
    if 0 <= hour < 6:
        return '00:00–06:00'
    elif 6 <= hour < 12:
        return '06:00–12:00'
    elif 12 <= hour < 18:
        return '12:00–18:00'
    else:
        return '18:00–24:00'

msgs['time_bucket'] = msgs['hour'].apply(bucket_time)
time_series = msgs.groupby(['date_new', 'time_bucket']).size().unstack(fill_value=0)

# --- Streamlit Dashboard ---
st.set_page_config(page_title="WhatsApp Group Dashboard", layout="wide")
st.title("📱 WhatsApp Group Engagement Dashboard")

st.header("📊 Overview")
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Groups", total_groups)
col2.metric("Total Participants", total_participants)
col3.metric("Unique Participants", unique_participants)
col4.metric("% Active Participants", f"{percent_active:.2f}%")
col5.metric("% Active Groups", f"{percent_active_groups:.2f}%")

st.header("🧠 Group Type Distribution")
st.bar_chart(group_sizes['type'].value_counts())

st.header("🚦 Group Health")
st.subheader("Top 5 Most Reacted Groups")
st.dataframe(top_reacted.reset_index().rename(columns={0: 'Reactions'}))
st.subheader("Participants Added and Left")
add_leave_summary = pd.DataFrame({
    'Added': added,
    'Left': left
}).fillna(0)
st.dataframe(add_leave_summary)

st.header("🧑‍💼 POC Analysis")
st.dataframe(poc_summary)

st.header("📦 Mimetype Distribution")
st.subheader("Messages by Mimetype")
st.bar_chart(mimetype_msg_counts)

st.header("📅 Time Series Analysis")
st.line_chart(time_series)
