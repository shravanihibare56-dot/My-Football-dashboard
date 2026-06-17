import streamlit as st
import os
os.environ["STREAMLIT_LEGACY_SERIALIZE"] = "True"
import requests
import pandas as pd
import matplotlib.pyplot as plt

# ⚙️ CONFIGURATION
API_KEY = "c97ee16461mshb91f344f9574d5ap14b4cbjsn6bdee3318502" 
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

# 🌟 WEB INTERFACE
st.set_page_config(page_title="Live Football Analytics", layout="wide")
st.title("⚽ AUTOMATED REAL-TIME FOOTBALL DASHBOARD")
st.write("---")

# एपीआय कॉल्स वाचवण्यासाठी साईडबार डिझाईन
st.sidebar.header("🎯 Match Control Center")
test_id = st.sidebar.text_input("RapidAPI Match ID (Optional):", value="")
refresh_btn = st.sidebar.button("🔄 Refresh / Load Data")

# १. लाईव्ह मॅच आयडी मिळवणे
@st.cache_data(ttl=300) # ५ मिनिटे कॅशे (कॉल्स वाचवण्यासाठी)
def get_live_match_id():
    try:
        url = "https://free-api-live-football-data.p.rapidapi.com/football-current-live"
        res = requests.get(url, headers=headers, timeout=10).json()
        matches = res.get('response', {}).get('live', [])
        
        if matches:
            first_match = matches[0]
            # नवीन API च्या संरचनेनुसार नावे आणि स्कोअर काढणे
            home_name = first_match.get('home', {}).get('name', 'Home')
            away_name = first_match.get('away', {}).get('name', 'Away')
            home_score = first_match.get('home', {}).get('score', 0)
            away_score = first_match.get('away', {}).get('score', 0)
            match_id = str(first_match.get('id'))
            
            return match_id, home_name, away_name, home_score, away_score
    except Exception as e:
        pass
    return None, "Home Team", "Away Team", 0, 0

# आयडी आणि सुरुवातीचा डेटा ठरवणे
if test_id.strip():
    match_id = test_id.strip()
    h_name, a_name = "Home Team", "Away Team"
    home_score, away_score = 0, 0
else:
    match_id, h_name, a_name, home_score, away_score = get_live_match_id()

if not match_id:
    st.warning("😴 सध्या मैदानावर कोणतीही लाईव्ह मॅच सुरू नाहीye. जशी एखादी मॅच सुरू होईल किंवा तुम्ही वर टेस्ट आयडी टाकाल, डेटा लोड होईल!")
else:
    st.sidebar.info(f"Monitoring ID: {match_id}")
    
    if refresh_btn or 'initialized' not in st.session_state:
        st.session_state['initialized'] = True
        
        try:
            with requests.Session() as session:
                session.headers.update(headers)
                
                # २. मॅच डिटेल्स (नावे)
                detail_url = f"https://{HOST}/football-get-match-detail"
                detail_res = session.get(detail_url, params={"eventid": match_id}, timeout=10).json()
                detail_data = detail_res.get('response', {}).get('detail', {})
                
                # जर डीप डिटेल्स मिळाले नाहीत तर मूळ नावे वापरू
                home_team = detail_data.get('home_team_name', h_name)
                away_team = detail_data.get('away_team_name', a_name)
                
                # ३. स्कोअर फेचिंग
                score_url = f"https://{HOST}/football-get-match-score"
                score_res = session.get(score_url, params={"eventid": match_id}, timeout=10).json()
                
                home_goals = home_score
                away_goals = away_score
                
                scores_list = score_res.get('response', {}).get('scores', [])
                if scores_list:
                    for s in scores_list:
                        if s.get('name') == home_team: home_goals = int(s.get('score', home_goals))
                        if s.get('name') == away_team: away_goals = int(s.get('score', away_goals))

                # ४. स्टॅट्स मिळवणे
                stats_url = f"https://{HOST}/football-get-match-statistics"
                stats_res = session.get(stats_url, params={"eventid": match_id}, timeout=10).json()
                
                home_pos, away_pos = 50.0, 50.0
                home_shots, away_shots = 0, 0
                home_yellow, away_yellow = 0, 0
                home_red, away_red = 0, 0
                home_corners, away_corners = 0, 0

                # इथून लूप आणि अचूक कीवर्ड्स सुरू होतात
                for s in stats_res.get('response', {}).get('statistic', []):
                    name = s.get('name', '').lower()
                    if 'poss' in name:
                        home_pos = clean_stat(s.get('home', 50))
                        away_pos = clean_stat(s.get('away', 50))
                    elif 'shot' in name or 'target' in name:
                        home_shots = int(clean_stat(s.get('home', 0)))
                        away_shots = int(clean_stat(s.get('away', 0)))
                    elif 'yellow' in name:
                        home_yellow = int(clean_stat(s.get('home', 0)))
                        away_yellow = int(clean_stat(s.get('away', 0)))
                    elif 'red' in name:
                        home_red = int(clean_stat(s.get('home', 0)))
                        away_red = int(clean_stat(s.get('away', 0)))
                    elif 'corner' in name:
                        home_corners = int(clean_stat(s.get('home', 0)))
                        away_corners = int(clean_stat(s.get('away', 0)))

                # ५. ML Odds Calculation
                base_score = 50
                goal_diff = (home_goals - away_goals) * 25.0
                possession_diff = (home_pos - away_pos) * 0.5
                shots_diff = (home_shots - away_shots) * 4.0
                
                final_odds = base_score + goal_diff + possession_diff + shots_diff
                home_prob = round(max(5, min(95, final_odds)), 2)
                away_prob = round(100 - home_prob, 2)

                # स्क्रीनवर डेटा दाखवणे (डायनॅमिक नावांसह)
                st.header(f"🏆 {home_team} {home_goals} - {away_goals} {away_team}")
                st.write("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📊 Match Statistics")
                    stats_df = pd.DataFrame({
                        "Statistic": ["Possession (%)", "Shots on Target", "Corners", "🟨 Yellow Cards", "🟥 Red Cards"],
                        "Home": [f"{home_pos}%", home_shots, home_corners, home_yellow, home_red],
                        "Away": [f"{away_pos}%", away_shots, away_corners, away_yellow, away_red]
                    })
                    
                    for index, row in stats_df.iterrows():
                        st.write(f"**{row['Statistic']}** : {row['Home']} vs {row['Away']}")
                        
                with col2:
                    st.subheader("📈 ML Win Probability")
                    fig, ax = plt.subplots(figsize=(6, 3))
                    bars = ax.barh([home_team, away_team], [home_prob, away_prob], color=['#FF4B4B', '#1C82AD'], height=0.4)
                    ax.set_xlim(0, 100)
                    for bar in bars:
                        width = bar.get_width()
                        ax.text(width + 2, bar.get_y() + bar.get_height()/2, f'{width}%', va='center', fontweight='bold')
                    st.pyplot(fig)
                    
        except Exception as e:
            st.error(f"डेटा लोड करताना अडचण आली: {e}")
    else:
        st.info("👈 डाव्या बाजूला असलेल्या 'Refresh / Load Data' बटणावर क्लिक करा, डेटा लगेच लोड होईल!")
            
