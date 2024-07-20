!pip install Streamlit
!pip install yfinance
!pip install streamlit folium googlemaps
!pip install streamlit_folium
!pip install requests
!pip install haversine
!pip install polyline

from google.colab import drive
drive.mount('/content/drive')

%%writefile my_app.py
import streamlit as st
import requests
import random
import string
import pandas as pd
import folium
import googlemaps
import polyline
from haversine import haversine
from streamlit_folium import folium_static
from datetime import datetime, timedelta

def main():
    st.title("配車システム🚖")
    st.caption("こちらは、Python Streamlitを用いた(仮想的な)配車システムのアプリです。")

    section = st.sidebar.selectbox("目次", ["配車の予約", "ダッシュボード"])

    if section == "配車の予約":

        st.sidebar.title("お客様情報の入力")
        st.sidebar.caption("下記の内容を入力してください")
        passenger_name = st.sidebar.text_input("お名前を入力してください")
        st.sidebar.write("乗車日を選択してください")
        date = st.sidebar.date_input("", key="date_input")
        st.sidebar.write("乗車時間を選択してください")
        time = st.sidebar.time_input("", key="time_input")
        date_time = datetime.combine(date, time)

        api_key = st.secrets["GOOGLE_MAPS_API_KEY"]
        departure = st.sidebar.text_input("乗車地点を入力してください")
        destination = st.sidebar.text_input("降車地点を入力してください")

        reservations = []

        if st.button("予約番号を生成"):
            reservation_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            reservations.append(reservation_id)
            st.success(f"予約番号{reservation_id}が生成されました")

        random.seed(42)
        driver_names = [chr(65 + i) for i in range(26)]
        random_evaluation = [random.randint(1, 5) for _ in driver_names]
        data = {
            "ドライバー名": [names(driver) for driver in driver_names],
            "評価": ['⭐' * level for level in random_evaluation]
        }
        df = pd.DataFrame(data)
        st.write("【手配可能なドライバーと評価】")

        driver_coordinates = [(random.uniform(24.396308, 45.551483), random.uniform(122.934570, 153.986672)) for _ in driver_names]

        if departure:
            geocoding_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={departure}&key={api_key}"
            response = requests.get(geocoding_url)
            geocoding_data = response.json()

            if geocoding_data.get("status") == "OK":
                location = geocoding_data["results"][0]["geometry"]["location"]
                current_coordinates = (location["lat"], location["lng"])

                df["距離(km)"] = [haversine(current_coordinates, driver_coord) for driver_coord in driver_coordinates]

                driver_to_pickup_time = [timedelta(minutes=(haversine(driver_coord, current_coordinates) / 50.0 * 60.0)) for driver_coord in driver_coordinates]
                driver_time_df = df[["ドライバー名"]].copy()
                driver_time_df["時間"] = [time.seconds // 3600 for time in driver_to_pickup_time]
                driver_time_df["分"] = [(time.seconds // 60) % 60 for time in driver_to_pickup_time]
                driver_time_df["秒"] = [time.seconds % 60 for time in driver_to_pickup_time]
                times = [f"{h}時間{m}分{s}秒" for h, m, s in zip(driver_time_df["時間"], driver_time_df["分"], driver_time_df["秒"])]
                driver_time_df["時間"] = times
                df["ドライバーが到着するまでにかかる時間"] = times

        if destination:
            geocoding_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={destination}&key={api_key}"
            response = requests.get(geocoding_url)
            geocoding_data = response.json()

            if geocoding_data.get("status") == "OK":
                location = geocoding_data["results"][0]["geometry"]["location"]
                arrival_coordinates = (location["lat"], location["lng"])

                directions_url = f"https://maps.googleapis.com/maps/api/directions/json?origin={departure}&destination={destination}&key={api_key}"
                response_directions = requests.get(directions_url)
                directions_data = response_directions.json()

                if directions_data.get("status") == "OK":
                    polyline_point = directions_data["routes"][0]["overview_polyline"]["points"]
                    decoded_point = polyline.decode(polyline_point)

                    duration_text = directions_data["routes"][0]["legs"][0]["duration"]["text"]
                    arrival_time = date_time + timedelta(minutes=int(duration_text.split()[0]))
                    arrival_time_str = arrival_time.strftime("%Y-%m-%d %H:%M:%S")

                    m = folium.Map(location=current_coordinates, zoom_start=10)

                    for i, driver_name in enumerate(driver_names):
                        folium.Marker(location=driver_coordinates[i], popup=f"ドライバー{driver_name}").add_to(m)

                    folium.Marker(location=current_coordinates, popup=f"乗車地点：{departure}", icon=folium.Icon(color="lightgreen")).add_to(m)

                    folium.Marker(location=arrival_coordinates, popup=f"降車地点：{destination}", icon=folium.Icon(color="lightblue")).add_to(m)

                    folium.PolyLine(locations=decoded_point, color="gray", weight=5).add_to(m)

                    folium_static(m)

                    selected_driver = st.sidebar.selectbox("ドライバーを選択してください", driver_names)
                    st.write(df)

                else:
                    st.error("乗車・降車地点の座標を取得できませんでした。都市名を正しく入力してください。")

        if departure and destination:
            gmaps = googlemaps.Client(key=api_key)
            directions_result = gmaps.directions(departure, destination, mode="driving", departure_time=datetime.now())

            if directions_result:
                distance_km = directions_result[0]["legs"][0]["distance"]["value"] / 1000
                base_fare_per_km = 450
                fare = base_fare_per_km * distance_km

                method = st.sidebar.radio("支払方法を選択してください", ("現金", "クレジットカード"))

                if method == "クレジットカード":
                    st.sidebar.write("💳クレジットカード情報")
                    card_number = st.sidebar.text_input("カード番号")
                    card_holder = st.sidebar.text_input("カード名義人")
                    expiration_date = st.sidebar.date_input("有効期限")

                    st.sidebar.caption("お支払い金額")
                    st.sidebar.write(f"{fare}円")

                    if st.sidebar.button("支払う"):
                        st.sidebar.success(f"{fare}円のクレジットカード支払いが完了しました")

                else:
                    st.sidebar.write("お支払い金額")
                    st.sidebar.write(f"{fare}円")
                    st.sidebar.write(f"直接ドライバーにお支払いください")

            else:
                st.error("運賃を計算できませんでした…")

        if st.button("配車をリクエストする📲"):

            if not passenger_name or not date_time or not departure or not destination or not selected_driver:
                st.warning("すべての情報を入力してください")

            else:
                if selected_driver:
                    st.success(f"ドライバー{selected_driver}が到着しました。\n{passenger_name}さん、{destination}へ行ってらっしゃいませ🚕")
                    st.write("【ご予約内容の確認】")
                    st.write(f"お名前：{passenger_name}")
                    st.write(f"乗車日時：{date_time}")
                    st.write(f"乗車地点：{departure}")
                    st.write(f"降車地点：{destination}")
                    st.write(f"ドライバー名 : ドライバー{selected_driver} → {'⭐' * random_evaluation[ord(selected_driver) - 65]}")
                    st.write(f"運賃：{fare}円")
                    st.write(f"到着予定時間：{duration_text} later  → {arrival_time_str}")

                else:
                    st.warning(f"現在手配可能なドライバーがいません、少々お待ちください…🙇")

    else:
        st.subheader("ドライバーのパフォーマンスレポート")
        driver_new_names = [chr(65 + i) for i in range(26)] + [chr(97 + i) for i in range(26)]
        driver_data = pd.DataFrame({
            "ドライバー名": driver_new_names,
            "配車回数": [random.randint(50, 200) for _ in range(52)],
            "利用可能時間(時間)": [random.uniform(100, 200) for _ in range(52)],
            "キャンセル率": [round(random.uniform(0, 10), 2) for _ in range(52)],
            "収益(円)": [random.randint(670, 100000000) for _ in range(52)]
        })
        df = pd.DataFrame(driver_data)
        st.write(df)

def names(driver_name):
    return f"ドライバー{driver_name}"

if __name__ == "__main__":
    main()

print('your globalip: ' + requests.get('https://ifconfig.me').text)
!streamlit run my_app.py & sleep 3 && npx localtunnel --port 8501
