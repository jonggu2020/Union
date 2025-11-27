from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import webbrowser
from threading import Timer

app = Flask(__name__)
CORS(app)

# ==========================================
# 여기에 발급받은 PUBG API 키를 입력하세요
PUBG_API_KEY = "Bearer 여기에_너의_긴_API_키를_넣어"
# 플랫폼 선택: steam 또는 kakao
PLATFORM = "steam"
# ==========================================

HEADER = {
    "Authorization": PUBG_API_KEY,
    "Accept": "application/vnd.api+json"
}
BASE_URL = f"https://api.pubg.com/shards/{PLATFORM}"

# [변경점 1] 메인 페이지 접속 시 index.html을 보여줌
@app.route('/')
def home():
    return render_template('index.html')

def get_account_id(nickname):
    url = f"{BASE_URL}/players?filter[playerNames]={nickname}"
    res = requests.get(url, headers=HEADER)
    if res.status_code != 200: return None
    return res.json()['data'][0]['id']

@app.route('/search', methods=['GET'])
def search_player():
    nickname = request.args.get('nickname')
    if not nickname: return jsonify({"error": "닉네임 입력 필요"}), 400

    try:
        account_id = get_account_id(nickname)
        if not account_id: return jsonify({"error": "플레이어를 찾을 수 없음"}), 404

        stats_url = f"{BASE_URL}/players/{account_id}/seasons/lifetime"
        stats_res = requests.get(stats_url, headers=HEADER)
        if stats_res.status_code != 200: return jsonify({"error": "전적 조회 실패"}), 404
        
        stats_data = stats_res.json()['data']['attributes']['gameModeStats']
        
        result = {
            "nickname": nickname,
            "account_id": account_id,
            "stats": stats_data
        }
        return jsonify(result)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "서버 내부 오류"}), 500

@app.route('/matches', methods=['GET'])
def get_matches():
    account_id = request.args.get('account_id')
    if not account_id: return jsonify({"error": "계정 ID 필요"}), 400

    try:
        player_url = f"{BASE_URL}/players/{account_id}"
        player_res = requests.get(player_url, headers=HEADER)
        if player_res.status_code != 200: return jsonify({"error": "매치 목록 조회 실패"}), 404
        
        # 최근 15게임 가져오기
        match_ids = [m['id'] for m in player_res.json()['data']['relationships']['matches']['data']][:15]
        
        match_history = []
        for mid in match_ids:
            match_url = f"{BASE_URL}/matches/{mid}"
            m_res = requests.get(match_url, headers=HEADER)
            if m_res.status_code != 200: continue
            m_data = m_res.json()

            attributes = m_data['data']['attributes']
            map_name = attributes.get('mapName', 'Unknown')
            game_mode = attributes.get('gameMode', '-')
            created_at = attributes.get('createdAt')

            my_stats = None
            for item in m_data['included']:
                if item['type'] == 'participant' and item['attributes']['stats']['playerId'] == account_id:
                    my_stats = item['attributes']['stats']
                    break
            
            if my_stats:
                match_history.append({
                    "map": map_name,
                    "mode": game_mode, 
                    "rank": my_stats['winPlace'],
                    "totalRank": attributes.get('cnt' + game_mode.split('-')[0].capitalize(), '?'),
                    "kills": my_stats['kills'],
                    "damage": round(my_stats['damageDealt']),
                    "dbno": my_stats['DBNOs'],
                    "distance": round(my_stats['walkDistance'] + my_stats['rideDistance'] + my_stats['swimDistance']),
                    "timeSurvived": my_stats['timeSurvived'],
                    "date": created_at
                })

        return jsonify(match_history)

    except Exception as e:
        print(f"Error in /matches: {e}")
        return jsonify({"error": "매치 정보 로딩 중 오류"}), 500

def open_browser():
    # 서버 실행 시 브라우저 자동 오픈
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == '__main__':
    # 1초 뒤에 브라우저를 엽니다 (서버가 켜질 시간을 줌)
    Timer(1, open_browser).start()
    app.run(debug=True, port=5000)