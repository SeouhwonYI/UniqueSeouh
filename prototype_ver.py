import streamlit as st
import pandas as pd
import numpy as np
import requests
import streamlit.components.v1 as components
import psycopg2
import pydeck as pdk
from neo4j import GraphDatabase

class Neo4jConnection:
    def __init__(self, uri, user, pwd):
        self.__uri = uri
        self.__user = user
        self.__pwd = pwd
        self.__driver = None
        try:
            self.__driver = GraphDatabase.driver(self.__uri, auth=(self.__user, self.__pwd))
        except Exception as e:
            print("Failed to create the driver:", e)

    def close(self):
        if self.__driver is not None:
            self.__driver.close()

    def query(self, query, db=None):
        assert self.__driver is not None, "Driver not initialized!"
        session = None
        response = None
        try:
            session = self.__driver.session(database=db) if db is not None else self.__driver.session() 
            response = list(session.run(query))
        except Exception as e:
            print("Query failed:", e)
        finally:
            if session is not None:
                session.close()
        return response

################################################################################################
dbname = ""                             # 왠지는 모르겠으나 local에서는 빈 문자열로 해야 함.
uri_param = "bolt://localhost:7687"     # local - default
user_param = "neo4j"                    # local - default
pwd_param = "1q2w3e4r"                  # 본인이 설정한 비밀번호
################################################################################################

st.set_page_config(page_icon="🧊", layout="wide", menu_items={'About': "# 우리조 화이팅!\nThis is an *extremely* poor prototype T.T"})
def init_connection():
    return psycopg2.connect(**st.secrets)

def run_query(query):
    try:
        conn = init_connection()
        df = pd.read_sql(query,conn)
    except psycopg2.Error as e:
        print("DB error: ", e)
    return df

def run_tx(query):
    try:
        conn = init_connection()
        with conn.cursor() as cur:
            cur.execute(query)
    except psycopg2.Error as e:
        print("DB error: ", e)
        conn.rollback()
    finally:
        conn.commit()
    return

def quit():
    conn = init_connection()
    conn.close()
    return

def search_data(uid):
    check_sql = f"SELECT dep, arr, startid, endid FROM users_search WHERE uid = '{uid}' ORDER BY id DESC limit 3"
    data = run_query(check_sql)
    return data

def load_data(filename):
    # data = pd.read_csv(filename,encoding='UTF-8')
    check_sql = f"SELECT * FROM {filename}"
    data = run_query(check_sql)
    return data

def get_shortest_path(nid1, nid2, road):
    '''
    nid1: 출발 node id int
    nid2: 도착 node id int
    filter: ['Edge', 'gentleEdge', 'noUphillEdge'] string
    Edge: 모든 길
    gentleEdge: |slope| <= 0.5 인 길
    noUphillEdge: slope <= 0.5 인 길
    '''
    cypher = "MATCH (n1: Road {Node: " +str(nid1)+ "}), (n2: Road {Node: " + str(nid2) + "})\n"\
            + "CALL apoc.algo.dijkstra(n1, n2, '" + road + ">', 'dist') YIELD path, weight\n"\
            + "RETURN path, weight"
    
    conn = Neo4jConnection(uri=uri_param, user=user_param, pwd=pwd_param)
    response = conn.query(cypher, db=dbname)
    conn.close()

    path = response[0]["path"]
    weight = response[0]["weight"]

    p_node = []
    p_coord = []
    d_edge = []

    p_node.append(path.start_node.get("Node"))
    p_coord.append((path.start_node.get("lat"), path.start_node.get("long")))
    for node in path:
        # node: 경로 상의 node
        # print(node.start_node.get("nid"))
        p_node.append(node.end_node.get("Node"))
        p_coord.append((node.end_node.get("lat"), node.end_node.get("long")))
        d_edge.append(node['dist'])

    return p_node, p_coord, d_edge


st.title("PathFinder+ 🧑‍🦽👩‍🦼 👨‍🦯 🚶‍♀️")

with st.sidebar:
    st.sidebar.title('✅ Sign In / Sign Up')
    tab1, tab2= st.tabs(['로그인' , '회원가입'])

    with tab1:
        # 사이드바에 select box를 활용하여 종을 선택한 다음 그에 해당하는 행만 추출하여 데이터프레임을 만들고자합니다.
        st.session_state['log_in'] = False
        with st.form("my_form1"):
            uid = st.text_input('ID:', autocomplete="id")
            pwd = st.text_input('Password:', type='password', max_chars=12)
            c1, c2 = st.columns(2)
                
            with c1:
                apply_button = st.form_submit_button("로그인")
            with c2:
                apply_button2 = st.form_submit_button("회원 탈퇴")
            if apply_button:
                if uid and pwd:
                    check_sql = f"SELECT * FROM users WHERE uid = '{uid}'"
                    df_check = run_query(check_sql)
                    if df_check.empty:
                        st.error("해당하는 ID가 없습니다.")
                    else:
                        check_sql = f"SELECT * FROM users WHERE uid = '{uid}' and pwd = '{pwd}'"
                        df_check = run_query(check_sql)
                        if df_check.empty:
                            st.error("password를 다시 확인해주세요.")
                        else:
                            st.success(uid + " 로그인!", icon="✅")
                            st.session_state['log_in'] = True
                            st.session_state['uid'] = uid
                else:
                    st.error("모든 정보를 입력해주세요.")
            
            if apply_button2:
                if uid and pwd:
                    check_sql = f"SELECT * FROM users WHERE uid = '{uid}'"
                    df_check = run_query(check_sql)
                    if df_check.empty:
                        st.error("해당하는 ID가 없습니다.")
                    else:
                        check_sql = f"SELECT * FROM users WHERE uid = '{uid}' and pwd = '{pwd}'"
                        df_check = run_query(check_sql)
                        if df_check.empty:
                            st.error("password를 다시 확인해주세요.")
                        else:
                            check_sql = f"delete FROM users WHERE uid = '{uid}' and pwd = '{pwd}'"
                            run_tx(check_sql)
                            st.success("더 좋은 서비스로 찾아뵙겠습니다.")
                else:
                    st.error("모든 정보를 입력해주세요.")
    if st.session_state['log_in'] == True:
        st.subheader('최근 검색 기록')
        st.write(search_data(uid))

    with tab2:
            st.subheader("회원가입 정보를 입력해주세요.")
            with st.form("my_form2"):
                uname = st.text_input('이름:', autocomplete="name", placeholder="ex: 이서원")
                uid = st.text_input('ID:', autocomplete="id", placeholder="ex: uniqueseouh", max_chars=15)
                pwd = st.text_input('Password:', type='password', max_chars=12, help='6~12자리 비밀번호 입력')
                pnum = st.text_input('전화번호:', max_chars=13, placeholder="ex: 010-1234-5678")
                weak = st.checkbox("보행약자 여부")
                home = st.text_input('도로명 주소:', placeholder="ex: 서울특별시 관악구 관악로 1 서울대학교 942동 3층")
                apply_button = st.form_submit_button("회원가입")
                if apply_button:
                    #입력 형식 체크
                    if uname and uid and pwd:
                        if len(pnum) > 13:
                            st.error("전화번호를 다시 확인해주세요.")
                        elif len(uid) > 15:
                            st.error("ID 길이를 다시 확인해주세요.")
                        elif len(pwd) > 12:
                            st.error("비밀번호 길이를 다시 확인해주세요.")
                        else:
                            check_sql = f"SELECT * FROM users WHERE uid = '{uid}'"
                        if run_query(check_sql).empty:
                                apply_sql = f"INSERT INTO users (uid, uname, pwd, weak, pnum, home) VALUES ('{uid}','{uname}','{pwd}','{weak}','{pnum}','{home}')"
                                run_tx(apply_sql)
                                st.balloons() 
                                st.success("회원가입 완료!")
                        else:
                                st.error("이미 회원 정보가 존재합니다.")
                    else:
                        st.error("모든 정보를 입력해주세요.") 

col1,col2 = st.columns([3,3])
roaddata = load_data('nodes')

with col1 :
    with st.form("startend"):
        st.markdown('1️⃣ 먼저 가고 싶은 곳의 지명을 입력하세요.')
        start = st.text_input('출발지를 입력해주세요.')
        end = st.text_input('도착지를 입력해주세요.')
        if st.form_submit_button('검색'):
            url = 'https://dapi.kakao.com/v2/local/search/keyword.json'
            headers = {'Authorization': 'KakaoAK b06c84b1e9208b0644f9098b79464e3b',
                    'KA': 'sdk/1.0.0 os/javascript origin/http://localhost:8501'}
            startparams = {'query': start}
            endparams = {'query': end}
            startmap, endmap = st.columns(2)
            with startmap:
                response = requests.get(url, headers=headers, params=startparams)
                data = response.json()
                if 'documents' in data:
                    place = data['documents'][0]
                    name = place['place_name']
                    latitude = float(place['y'])
                    longitude = float(place['x'])

                        # Create a DataFrame with place_name, latitude, and longitude columns
                    df = pd.DataFrame({'nodeid': name, 'Latitude': latitude, 'Longitude': longitude}, index=[0])
                    st.write("장소명 :", name, "  \n위도 :", latitude, "  \n경도 :", longitude)

                    filtered_data = roaddata[(abs(roaddata['longitude']-longitude) <= 0.0005) & (abs(roaddata['latitude']-latitude) <= 0.0005)]

                        # Create a pydeck map using the KAKAOMAP API
                    view_state = pdk.ViewState(latitude=df['Latitude'].mean(),
                                                longitude=df['Longitude'].mean(),
                                                zoom=16,
                                                pitch=0)

                    layer1 = pdk.Layer('ScatterplotLayer',
                                        data=df,
                                        get_position='[Longitude, Latitude]',
                                        get_radius=5,
                                        get_fill_color=[0, 255, 0],
                                        pickable=True)
                    layer2 = pdk.Layer('ScatterplotLayer',
                                        data=filtered_data,
                                        get_position='[longitude, latitude]',
                                        get_radius=5,
                                        get_fill_color=[255, 0, 0],
                                        pickable=True)

                    tool_tip = {'html': '{nodeid}',
                                    'style': {'backgroundColor': 'steelblue', 'color': 'white', 'zIndex': 10}}

                    map_config = pdk.Deck(layers=[layer1, layer2], initial_view_state=view_state, tooltip=tool_tip,
                                            map_style='road', height=210)

                    st.components.v1.html(map_config.to_html(as_string=True), height=210)
                else:
                    st.write('No results found.')
            with endmap:
                response = requests.get(url, headers=headers, params=endparams)
                data = response.json()
                if 'documents' in data:
                    place = data['documents'][0]
                    name = place['place_name']
                    latitude = float(place['y'])
                    longitude = float(place['x'])
                        # Create a DataFrame with place_name, latitude, and longitude columns
                    df = pd.DataFrame({'nodeid': name, 'Latitude': latitude, 'Longitude': longitude}, index=[0])
                    st.write("장소명 :", name, "  \n위도 :", latitude, "  \n경도 :", longitude)

                    filtered_data = roaddata[(abs(roaddata['longitude']-longitude) <= 0.0005) & (abs(roaddata['latitude']-latitude) <= 0.0005)]

                        # Create a pydeck map using the KAKAOMAP API
                    view_state = pdk.ViewState(latitude=df['Latitude'].mean(),
                                                longitude=df['Longitude'].mean(),
                                                zoom=16,
                                                pitch=0)

                    layer1 = pdk.Layer('ScatterplotLayer',
                                        data=df,
                                        get_position='[Longitude, Latitude]',
                                        get_radius=5,
                                        get_fill_color=[0, 255, 0],
                                        pickable=True)
                    layer2 = pdk.Layer('ScatterplotLayer',
                                        data=filtered_data,
                                        get_position='[longitude, latitude]',
                                        get_radius=5,
                                        get_fill_color=[255, 0, 0],
                                        pickable=True)

                    tool_tip = {'html': '{nodeid}',
                                    'style': {'backgroundColor': 'steelblue', 'color': 'white', 'zIndex': 10}}

                    map_config = pdk.Deck(layers=[layer1, layer2], initial_view_state=view_state, tooltip=tool_tip,
                                            map_style='road', height=210)

                    st.components.v1.html(map_config.to_html(as_string=True), height=210)
                else:
                    st.write('No results found.')
        st.info("👋 지역명을 검색한 후 현위치, 도착지와 가장 가까운 점의 노드 ID를 오른쪽에 입력하세요!")
a = 0
row = run_query(f"SELECT count(*) FROM users_search").iloc[0,0]
with col2:
    with st.form("경로추천"):
        st.markdown('2️⃣ 노드 번호를 입력하시면 길찾기를 도와드릴게요.')
        startid = st.text_input('출발지의 NodeID를 입력해주세요.')
        endid = st.text_input('도착지의 NodeID를 입력해주세요.')
        
        if st.form_submit_button('검색'):
            if st.session_state['uid'] and start and end and startid and endid:
                row += 1
                apply_sql = f"INSERT INTO users_search (uid, times, dep, arr, startid, endid, id) VALUES ('{st.session_state['uid']}', CURRENT_TIMESTAMP,'{start}','{end}','{startid}','{endid}','{row}')"
                run_tx(apply_sql)
            # p_nodes, p_coord, d_edge = get_shortest_path(startid, endid, 'Info')
            # print(p_nodes)
            # print(p_coord)
            # print(d_edge)
            st.write("변경된 지도 생성")
            a = '변경된 지도'
        st.info("👋 1️⃣의 결과 또는 검색기록을 활용하여 NodeID를 입력하세요!")
if a != 0:
    st.write(a)




# df = pd.DataFrame({'color':['#FF0000', '#00FF00'], 'path':[[[126.9484033871627,37.466352968363864],[126.941686527151,37.4824725161034],[126.963523905001,37.4770932409965],[126.952713197762,37.4812845080678]],
#                                                            [[126.963523905001,37.4770932409965],[126.960884263255,37.4658730147545]]]})

# view_state = pdk.ViewState(
#     latitude=37.4770932409965,
#     longitude=126.963523905001,
#     zoom=14
# )
# def hex_to_rgb(h):
#     h = h.lstrip('#')
#     return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# df['color'] = df['color'].apply(hex_to_rgb)

# layer = pdk.Layer(
#     type='PathLayer',
#     data=df,
#     pickable=True,
#     get_color = 'color',
#     width_scale=2,
#     width_min_pixels=2,
#     get_path='path',
#     get_width=5
# )

# r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={'html': '냐옹'}, map_style='road')

# st.pydeck_chart(r)



quit()
