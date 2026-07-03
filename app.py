import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from streamlit_geolocation import streamlit_geolocation
from streamlit_autorefresh import st_autorefresh
import requests
import os
import math
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import datetime

st.set_page_config(
    page_title="Lapor Simbok - STIEIMA",
    page_icon="🛡️",
    layout="wide"
)

BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", "8912832894:AAHxxO3NW1cS1b6zKsI2NWoixxyMmSxktgc"))
CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", "-5435549253"))

if 'relawan_data' not in st.session_state:
    try: st.session_state.relawan_data = pd.read_csv("data/relawan.csv")
    except: st.session_state.relawan_data = pd.DataFrame(columns=["Nama", "No_Handphone", "Latitude", "Longitude", "Status"])

if 'laporan_insiden' not in st.session_state: st.session_state.laporan_insiden = []
if 'logo_clicks' not in st.session_state: st.session_state.logo_clicks = 0
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False
if 'panic_triggered' not in st.session_state: st.session_state.panic_triggered = False

BASE_LAT, BASE_LON = -7.970222, 112.607498

def hitung_jarak(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def send_telegram_alert(lat, lon):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pesan = (
        f"🚨 *ALERT DARURAT: LAPOR SIMBOK* 🚨\n\n"
        f"📅 *Waktu Kejadian:* {timestamp}\n"
        f"📍 *Lokasi Korban:* {lat}, {lon}\n"
        f"🔗 [Buka Peta Lokasi](https://maps.google.com/?q={lat},{lon})\n\n"
        f"Status: Mohon Satgas terdekat segera merespons ke lokasi!"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"})
        return resp.status_code == 200
    except: return False

def generate_pdf_report(insiden_list):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1a365d'), spaceAfter=12)
    story.append(Paragraph("LAPORAN REKAPITULASI INSIDEN - LAPOR SIMBOK", title_style))
    story.append(Paragraph(f"Dicetak Otomatis pada: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 15))
    data = [["Waktu Kejadian", "Latitude", "Longitude", "Status Tindakan"]]
    for ins in insiden_list: data.append([ins['Waktu'], str(ins['Lat']), str(ins['Lon']), ins['Status']])
    t = Table(data, colWidths=[150, 100, 100, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a365d')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f7fafc')),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
    ]))
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer

with st.sidebar:
    if os.path.exists("assets/logo_stieima.png"):
        st.image("assets/logo_stieima.png", use_column_width=True)
    
    if st.button("✨ Verifikasi Sistem Kampus Aman", use_container_width=True):
        st.session_state.logo_clicks += 1
        
    if st.session_state.logo_clicks >= 3:
        st.info("🔓 Fitur Terkunci Terdeteksi.")
        password_input = st.text_input("Masukkan Kode Akses Pusat:", type="password")
        if password_input == "simbok123":
            st.session_state.admin_mode = True
            st.success("Mode Admin Diaktifkan!")
            
    if st.session_state.admin_mode:
        st.write("---")
        admin_nav = st.radio("Menu Tersembunyi Admin:", ["📋 Monitor Insiden Aktif", "📊 Database Relawan", "📄 Export Arsip Dokumen"])
        if st.button("🚪 Keluar Mode Admin"):
            st.session_state.admin_mode = False
            st.session_state.logo_clicks = 0
            st.rerun()

    st.write("---")
    st.markdown("""
    <div style='font-size: 0.85em; color: #2d3748; line-height: 1.4; font-family: sans-serif;'>
        <strong style='font-size: 1em; color: #1a202c;'>🏢 TIM Pengabdian Masyarakat STIEIMA 2026</strong>
        <ul style='margin-top: 5px; margin-bottom: 0; padding-left: 15px; list-style-type: disc;'>
            <li style='margin-bottom: 4px; text-align: left;'><strong>Pelindung:</strong> Assoc.Prof.Dr. Hj. Amelia Setyawati, S.H., M.M | Ketua STIEIMA</li>
            <li style='margin-bottom: 4px; text-align: left;'><strong>Penanggung Jawab:</strong> Drs. Sudarjo, M.Pd., M.Si. | Ketua LPPM</li>
            <li style='margin-bottom: 4px; text-align: left;'><strong>Ketua Tim:</strong> Dimas Putri Mega Pratesa, S.Pd., M.Pd. | Ketua TIM</li>
            <li style='margin-bottom: 0px; text-align: left;'><strong>Arsitek & Pengembang Utama:</strong> Ir. M Nasri AW, M.Eng.Sc, M.Kom | Dosen STIEIMA</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

if not st.session_state.admin_mode:
    # Menginisialisasi geolokasi secara tersembunyi di awal halaman utama
    loc_data = streamlit_geolocation()
    
    col_l1, col_l2, col_l3 = st.columns([2, 1, 2])
    with col_l2:
        if os.path.exists("assets/logo_aplikasi.png"):
            st.image("assets/logo_aplikasi.png", use_column_width=True)
            
    st.markdown("<h2 style='text-align: center; color: #2d3748;'>Sistem Perlindungan Kampus Darurat</h2>", unsafe_allow_html=True)
    
    # PERBAIKAN 1: Pindahkan notif aktivasi GPS browser dari pojok kiri atas ke bawah judul utama
    if not (loc_data and loc_data.get("latitude") and loc_data.get("longitude")):
        st.warning("⚠️ Mengakses koordinat GPS... Harap izinkan pelacakan lokasi peramban browser Anda agar tombol respons darurat aktif.")
        
    st.write("---")
    
    with st.expander("📚 Cari Tahu: Informasi & Panduan Mitigasi Krisis Kampus Aman", expanded=False):
        st.markdown("""
        ### Apa itu Bullying & Kekerasan Seksual?
        * **Bullying (Perundungan):** Perilaku agresif yang tidak menyenangkan baik secara verbal, fisik, ataupun sosial di dunia nyata maupun maya.
        * **Kekerasan Seksual:** Setiap perbuatan merendahkan, menghina, melecehkan, dan/atau menyerang tubuh seseorang karena ketimpangan relasi kuasa.
        """)
    
    c_b1, c_b2, c_b3 = st.columns([1, 2, 1])
    with c_b2:
        if loc_data and loc_data.get("latitude") and loc_data.get("longitude"):
            user_lat = loc_data["latitude"]
            user_lon = loc_data["longitude"]
            
            st.markdown("<p style='text-align: center; color: green; font-weight: bold;'>🟢 GPS Siap & Lokasi Terkunci Otomatis</p>", unsafe_allow_html=True)
            
            if st.button("🚨 BANTU AKU.... ", use_container_width=True, type="primary"):
                send_telegram_alert(user_lat, user_lon)
                st.session_state.laporan_insiden.append({
                    "Waktu": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Lat": user_lat, "Lon": user_lon, "Status": "Relawan Meluncur"
                })
                st.session_state.panic_triggered = True
                st.balloons()
            
            if st.session_state.panic_triggered:
                relawan_aktif = st.session_state.relawan_data[st.session_state.relawan_data["Status"] == "Aktif"]
                if not relawan_aktif.empty:
                    relawan_aktif["Jarak"] = relawan_aktif.apply(lambda r: hitung_jarak(user_lat, user_lon, r["Latitude"], r["Longitude"]), axis=1)
                    terdekat = relawan_aktif.sort_values(by="Jarak").iloc[0]
                    nama_relawan = terdekat["Nama"]
                    jarak_relawan = round(terdekat["Jarak"], 2)
                    posisi_relawan = f"koordinat ({terdekat['Latitude']}, {terdekat['Longitude']}) dengan jarak {jarak_relawan} km"
                else:
                    nama_relawan = "Pusat Satgas STIEIMA"
                    posisi_relawan = "Posko Utama Pusat Komando"
                
                # Kotak Informasi Penolong
                st.error(f"⚠️ **INFORMASI PENOLONG:** Relawan **{nama_relawan}** sedang meluncur dari posisi **{posisi_relawan}** menuju tempat Anda.")
                
                # PERBAIKAN 2: Pindahkan tombol Hubungi Satgas Telegram ke bawah kotak INFORMASI PENOLONG (untuk insiden terlambat)
                st.markdown(
                    "<div style='text-align: center; margin-top: 10px; margin-bottom: 15px;'>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    "<div style='text-align: center;'>"
                    "<a href='https://t.me/Lapor_Simbok_STIEIMA' target='_blank' style='text-decoration: none; color: #ffffff; background-color: #0088cc; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 0.9em; display: inline-flex; align-items: center; gap: 8px;'>"
                    "💬 Hubungi Satgas (Telegram Group)"
                    "</a>"
                    "<br><small style='color: #718096;'>*Klik di sini untuk mengirim pesan langsung jika respon tim di lapangan lambat / terlambat datang</small>"
                    "</div>", 
                    unsafe_allow_html=True
                )
                
                st.markdown("### 🗺️ Peta Pantauan Lapangan Aktif")
                m_korban = folium.Map(location=[user_lat, user_lon], zoom_start=14)
                folium.Marker([user_lat, user_lon], popup="Posisi Anda", icon=folium.Icon(color='red', icon='info-sign')).add_to(m_korban)
                folium.Marker([BASE_LAT, BASE_LON], popup="Home Base STIEIMA", icon=folium.Icon(color='blue', icon='home')).add_to(m_korban)
                for _, row in st.session_state.relawan_data.iterrows():
                    folium.Marker([row["Latitude"], row["Longitude"]], popup=f"Relawan: {row['Nama']}", icon=folium.Icon(color='green', icon='user')).add_to(m_korban)
                folium_static(m_korban)

else:
    st_autorefresh(interval=10000, key="admin_sync_v8")
    st.markdown("<h1>💻 Control Room & Dispatcher Admin</h1>", unsafe_allow_html=True)
    
    if admin_nav == "📋 Monitor Insiden Aktif":
        st.subheader("Live Mapping Insiden")
        m_admin = folium.Map(location=[BASE_LAT, BASE_LON], zoom_start=13)
        folium.Marker([BASE_LAT, BASE_LON], popup="Home Base STIEIMA", icon=folium.Icon(color='blue', icon='star')).add_to(m_admin)
        for _, row in st.session_state.relawan_data.iterrows():
            folium.Marker([row["Latitude"], row["Longitude"]], popup=f"Relawan: {row['Nama']}", icon=folium.Icon(color='green', icon='user')).add_to(m_admin)
        for ins in st.session_state.laporan_insiden:
            folium.Marker([ins["Lat"], ins["Lon"]], popup=f"🚨 LOKASI KORBAN ({ins['Waktu']})", icon=folium.Icon(color='red', icon='exclamation-sign')).add_to(m_admin)
        folium_static(m_admin)
        
        st.subheader("Tabel Antrean Tindakan Darurat")
        st.dataframe(pd.DataFrame(st.session_state.laporan_insiden) if st.session_state.laporan_insiden else pd.DataFrame(columns=["Waktu", "Lat", "Lon", "Status"]), use_container_width=True)

    elif admin_nav == "📊 Database Relawan":
        st.subheader("Tambah Anggota Relawan Baru")
        with st.form("add_relawan_v8"):
            nama = st.text_input("Nama Relawan")
            hp = st.text_input("No Handphone")
            lat_sim = st.number_input("Simulasi Latitude", value=-7.9715, format="%.6f")
            lon_sim = st.number_input("Simulasi Longitude", value=112.6085, format="%.6f")
            if st.form_submit_button("Simpan Data"):
                if nama and hp:
                    new_rel = pd.DataFrame([{"Nama": nama, "No_Handphone": hp, "Latitude": lat_sim, "Longitude": lon_sim, "Status": "Aktif"}])
                    st.session_state.relawan_data = pd.concat([st.session_state.relawan_data, new_rel], ignore_index=True)
                    st.session_state.relawan_data.to_csv("data/relawan.csv", index=False)
                    st.success("Relawan berhasil tersimpan!")
                    st.rerun()
        st.data_editor(st.session_state.relawan_data, use_container_width=True)
        
    elif admin_nav == "📄 Export Arsip Dokumen":
        st.subheader("Cetak Rekapitulasi Laporan PDF")
        if st.session_state.laporan_insiden:
            pdf_file = generate_pdf_report(st.session_state.laporan_insiden)
            st.download_button("📥 Download PDF Report", data=pdf_file, file_name="Laporan_Insiden_Simbok.pdf", mime="application/pdf")
