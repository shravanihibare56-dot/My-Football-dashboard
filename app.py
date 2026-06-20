import streamlit as st
import os
os.environ["STREAMLIT_LEGACY_SERIALIZE"] = "True"
import requests
import pandas as pd
import matplotlib.pyplot as plt

# ⚙️ CONFIGURATION
API_KEY = "964bf7fbc8msh59462ccd3956050p160456jsnf51e5c04bf49" 
HOST = "free-api-live-football-data.p.rapidapi.com"

headers = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": HOST,
    "Connection": "close"
}

def clean_stat(val):
    try:
        return float(str(val).replace('%','').strip())
    except:
        return 0.0

# 🚀 नवं हुशार फंक्शन: जे JSON मध्ये कुठेही लपलेले स्टॅट्स शोधून काढेल
def get_stat_values(data, keywords):
    if isinstance(data, dict):
        title = str(data.get('title', '')).lower()
        # जर टायटलमध्ये आपला कीवर्ड असेल, तर त्याचे स्टॅट्स परत पाठवा
        if any(kw in title for kw in keywords):
            s = data.get('stats')
            if isinstance(s, list) and len(s) >= 2:
                return s
        # नाहीतर डिक्शनरीच्या आतल्या लेयरमध्ये शोधा
        for v in data.values():
            res = get_stat_values(v, keywords)
            if res: return res
    elif isinstance(data, list):
        # जर लिस्ट असेल, तर प्रत्येक आयटममध्ये शोधा
        for item in data:
            res = get_stat_values(item, keywords)
            if res: return res
    return None

# 🌟 WEB INTERFACE
st.set_page_config(page_title="Live Football Analytics", layout="wide")
st.title("⚽ AUTOMATED REAL-TIME FOOTBALL DASHBOARD")
st.write("---")

st.sidebar.header("🎯 Match Control Center")
test_id = st.sidebar.text_input("RapidAPI Match ID (Optional):", value="")
refresh_btn = st.sidebar.button("🔄 Refresh / Load Data")

@st.cache_data(ttl=300)
def get_live_match_id():
    try:
        url = "https://free-api-live-football-data.p.rapidapi.com/football-current-live"
        res = requests.get(url, headers=headers, timeout=10).json()
        matches = res.get('response', {}).get('live', [])
        if matches:
            first_match = matches[0]
            home_name = first_match.get('home', {}).get('name', 'Home Team')
            away_name = first_match.get('away', {}).get('name', 'Away Team')
            home_score = first_match.get('home', {}).get('score', 0)
            away_score = first_match.get('away', {}).get('score', 0)
            match_id = str(first_match.get('id'))
            return match_id, home_name, away_name, home_score, away_score
    except:
        pass
    return None, "Home Team", "Away Team", 0, 0

if test_id.strip():
    match_id = test_id.strip()
    h_name, a_name = "Home Team", "Away Team"
    home_score, away_score = 0, 0
else:
    match_id, h_name, a_name, home_score, away_score = get_live_match_id()

if not match_id:
    st.warning("😴 सध्या मैदानावर कोणतीही लाईव्ह मॅच सुरू नाहीये. जशी एखादी मॅच सुरू होईल किंवा तुम्ही वर टेस्ट आयडी टाकाल, डेटा लोड होईल!")
else:
    st.sidebar.info(f"Monitoring ID: {match_id}")
    
    if refresh_btn or 'initialized' not in st.session_state:
        st.session_state['initialized'] = True
        
        try:
            with requests.Session() as session:
                session.headers.update(headers)
                
                # २. मॅच डिटेल्स
                detail_url = f"https://{HOST}/football-get-match-detail"
                detail_res = session.get(detail_url, params={"eventid": match_id}, timeout=10).json()
                detail_data = detail_res.get('response', {})
                if isinstance(detail_data, list) and len(detail_data) > 0:
                    detail_data = detail_data[0]
                elif not isinstance(detail_data, dict):
                    detail_data = {}
                detail_info = detail_data.get('detail', {})
                
                match_name_raw = detail_info.get('matchName', '')
                if "-vs-" in match_name_raw:
                    teams_part = match_name_raw.split('_')[0]
                    home_team = teams_part.split('-vs-')[0].strip()
                    away_team = teams_part.split('-vs-')[1].strip()
                else:
                    home_team = detail_info.get('home_team_name', h_name)
                    away_team = detail_info.get('away_team_name', a_name)
                
                # ३. स्कोअर
                score_url = f"https://{HOST}/football-get-match-score"
                score_res = session.get(score_url, params={"eventid": match_id}, timeout=10).json()
                home_goals, away_goals = home_score, away_score
                score_resp_data = score_res.get('response', {})
                if isinstance(score_resp_data, list) and len(score_resp_data) > 0:
                    score_resp_data = score_resp_data[0]
                elif not isinstance(score_resp_data, dict):
                    score_resp_data = {}
                scores_list = score_resp_data.get('scores', [])
                if scores_list:
                    for s in scores_list:
                        s_name = s.get('name', '').lower()
                        if home_team.lower() in s_name: home_goals = int(s.get('score', home_goals))
                        elif away_team.lower() in s_name: away_goals = int(s.get('score', away_goals))

                # ४. स्टॅट्स (नवीन स्मार्ट पद्धतीने)
                stats_url = f"https://{HOST}/football-get-match-statistics"
                stats_res = session.get(stats_url, params={"eventid": match_id}, timeout=10).json()
                
                pos_data = get_stat_values(stats_res, ['possession'])
                shots_data = get_stat_values(stats_res, ['shots on target'])
                corners_data = get_stat_values(stats_res, ['corner kicks', 'corners'])
                yellow_data = get_stat_values(stats_res, ['yellow cards'])
                red_data = get_stat_values(stats_res, ['red cards'])

                home_pos = clean_stat(pos_data[0]) if pos_data else 50.0
                away_pos = clean_stat(pos_data[1]) if pos_data else 50.0
                home_shots = int(clean_stat(shots_data[0])) if shots_data else 0
                away_shots = int(clean_stat(shots_data[1])) if shots_data else 0
                home_corners = int(clean_stat(corners_data[0])) if corners_data else 0
                away_corners = int(clean_stat(corners_data[1])) if corners_data else 0
                home_yellow = int(clean_stat(yellow_data[0])) if yellow_data else 0
                away_yellow = int(clean_stat(yellow_data[1])) if yellow_data else 0
                home_red = int(clean_stat(red_data[0])) if red_data else 0
                away_red = int(clean_stat(red_data[1])) if red_data else 0

                # ५. ML Odds
                base_score = 50
                goal_diff = (home_goals - away_goals) * 25.0
                possession_diff = (home_pos - away_pos) * 0.5
                shots_diff = (home_shots - away_shots) * 4.0
                final_odds = base_score + goal_diff + possession_diff + shots_diff
                home_prob = round(max(5, min(95, final_odds)), 2)
                away_prob = round(100 - home_prob, 2)

                # UI Display
                st.header(f"🏆 {home_team} {home_goals} - {away_goals} {away_team}")
                st.write("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📊 Match Statistics")
                    stats_df = pd.DataFrame({
                        "Statistic": ["Possession (%)", "Shots on Target", "Corners", "🟨 Yellow Cards", "🟥 Red Cards"],
                        home_team: [f"{home_pos}%", home_shots, home_corners, home_yellow, home_red],
                        away_team: [f"{away_pos}%", away_shots, away_corners, away_yellow, away_red]
                    })
                    for index, row in stats_df.iterrows():
                        st.write(f"**{row['Statistic']}** : {row[home_team]} vs {row[away_team]}")
                        
                with col2:
                    st.subheader("📈 ML Win Probability")
                    fig, ax = plt.subplots(figsize=(6, 3))
                    bars = ax.barh([home_team, away_team], [home_prob, away_prob], color=['#FF4B4B', '#1C82AD'], height=0.4)
                    ax.set_xlim(0, 100)
                    for bar in bars:
                        width = bar.get_width()
                        ax.text(width + 2, bar.get_y() + bar.get_height()/2, f'{width}%', va='center', fontweight='bold', color='white')
                    st.pyplot(fig)
                    
        except Exception as e:
            st.error(f"डेटा लोड करताना अडचण आली: {e}")
