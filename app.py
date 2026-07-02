import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from streamlit_geolocation import streamlit_geolocation
from streamlit_autorefresh import st_autorefresh
import requests
import os
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import datetime

# --- SETTING ANTARMUKA HALAMAN ---
st.set_page_config(
    page_title="Lapor Simbok - STIEIMA",
    page_icon="🛡️",
    layout="wide"
)

# --- INISIALISASI DATA LOCAL ---
if 'relawan_data' not in st.session_state:
    try:
        st.session_state.relawan_data = pd.read_csv("data/relawan.csv")
    except:
        st.session_state.relawan_data = pd.DataFrame(columns=["Nama", "No_Handphone", "Latitude", "Longitude", "Status"])

if 'laporan_insiden' not in st.session_state:
    st.session_state.laporan_insiden = []

# KOORDINAT PUSAT KOMANDO (STIEIMA MALANG)
BASE_LAT, BASE_LON = -7.970222, 112.607498

# --- FUNGSI INTEGRASI TELEGRAM BOT ---
def send_telegram_alert(lat, lon):
    # Diambil aman dari Env Secrets Hugging Face
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "MOCK_TOKEN_DEMO")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "MOCK_CHAT_ID_DEMO")
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pesan = (
        f"🚨 *ALERT DARURAT: LAPOR SIMBOK* 🚨\n\n"
        f"📅 *Waktu Kejadian:* {timestamp}\n"
        f"📍 *Lokasi Korban:* {lat}, {lon}\n"
        f"🔗 [Buka Peta Lokasi](https://www.google.com/maps?q={lat},{lon})\n\n"
        f"Status: Tim Relawan terdekat diinstruksikan segera merespons ke lokasi!"
    )
    
    if bot_token != "MOCK_TOKEN_DEMO" and chat_id != "MOCK_CHAT_ID_DEMO":
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": pesan, "parse_mode": "Markdown"})
            return True
        except Exception as e:
            st.error(f"Gagal mengirim alert eksternal: {e}")
            return False
    return "SIMULATED"

# --- FUNGSI EKSPOR ARSIP PDF (REPORTLAB) ---
def generate_pdf_report(insiden_list):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1a365d'), spaceAfter=12
    )
    
    story.append(Paragraph("LAPORAN REKAPITULASI INSIDEN - LAPOR SIMBOK", title_style))
    story.append(Paragraph(f"Dicetak Otomatis pada: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 15))
    
    data = [["Waktu Kejadian", "Latitude", "Longitude", "Status Tindakan"]]
    for ins in insiden_list:
        data.append([ins['Waktu'], str(ins['Lat']), str(ins['Lon']), ins['Status']])
        
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

# --- SIDEBAR MENU NAVIGATION ---
st.sidebar.markdown("### 🛡️ LAPOR SIMBOK")
menu = st.sidebar.radio("Pilih Antarmuka Menu:", ["🚨 Panic Button (Korban)", "💻 Dashboard Admin", "📚 Cari Tahu & Edukasi"])

# --- MENU 1: PANIC BUTTON ---
if menu == "🚨 Panic Button (Korban)":
    st.markdown("<h1 style='text-align: center; color: #e53e3e;'>🚨 EMERGENCY PANIC BUTTON</h1>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("#### 1. Aktifkan Izin Lokasi Perangkat Anda")
        loc_data = streamlit_geolocation()
        
        if loc_data and loc_data.get("latitude") and loc_data.get("longitude"):
            user_lat = loc_data["latitude"]
            user_lon = loc_data["longitude"]
            st.success(f"📍 Posisi Anda Terkunci: {user_lat}, {user_lon}")
            
            st.markdown("#### 2. Tekan Tombol Darurat")
            if st.button("🔴 TOLONG AKU", use_container_width=True, type="primary"):
                status_tg = send_telegram_alert(user_lat, user_lon)
                
                # Masukkan ke log antrean
                st.session_state.laporan_insiden.append({
                    "Waktu": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Lat": user_lat, "Lon": user_lon, "Status": "Relawan Meluncur"
                })
                
                st.balloons()
                st.error("⚠️ Sinyal Bahaya Terkirim! Notifikasi peta lokasi Anda telah diteruskan otomatis ke grup Telegram Relawan STIEIMA.")
                
                # Tampilkan Peta Respons Terdekat
                st.markdown("### 🗺️ Peta Pantauan Lapangan Aktif")
                m_korban = folium.Map(location=[user_lat, user_lon], zoom_start=15)
                folium.Marker([user_lat, user_lon], popup="Posisi Anda", icon=folium.Icon(color='red', icon='info-sign')).add_to(m_korban)
                folium.Marker([BASE_LAT, BASE_LON], popup="Pusat STIEIMA", icon=folium.Icon(color='blue', icon='home')).add_to(m_korban)
                
                for _, row in st.session_state.relawan_data.iterrows():
                    if row["Status"] == "Aktif":
                        folium.Marker([row["Latitude"], row["Longitude"]], popup=f"Relawan: {row['Nama']}", icon=folium.Icon(color='green')).add_to(m_korban)
                folium_static(m_korban)
        else:
            st.warning("Menunggu konfirmasi izin akses sistem lokasi koordinat browser...")

# --- MENU 2: DASHBOARD ADMIN ---
elif menu == "💻 Dashboard Admin":
    st_autorefresh(interval=10000, key="admin_sync") # Sinkronisasi otomatis data masuk tiap 10 detik
    st.markdown("<h1>💻 Control Room & Dispatcher Admin</h1>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["📋 Monitor Insiden Aktif", "🧑‍🤝‍🧑 Database Relawan", "📄 Export Arsip Dokumen"])
    
    with t1:
        st.subheader("Live Mapping Insiden")
        m_admin = folium.Map(location=[BASE_LAT, BASE_LON], zoom_start=14)
        folium.Marker([BASE_LAT, BASE_LON], popup="Pusat Operasional", icon=folium.Icon(color='blue', icon='star')).add_to(m_admin)
        
        for ins in st.session_state.laporan_insiden:
            folium.Marker([ins["Lat"], ins["Lon"]], popup="🚨 LOKASI KORBAN", icon=folium.Icon(color='red')).add_to(m_admin)
        folium_static(m_admin)
        
        st.subheader("Tabel Antrean Tindakan")
        st.dataframe(pd.DataFrame(st.session_state.laporan_insiden) if st.session_state.laporan_insiden else pd.DataFrame(columns=["Waktu", "Lat", "Lon", "Status"]), use_container_width=True)

    with t2:
        st.subheader("Tambah Anggota Relawan Baru")
        with st.form("add_relawan"):
            nama = st.text_input("Nama Relawan")
            hp = st.text_input("No Handphone")
            lat_sim = st.number_input("Simulasi Latitude", value=-7.9715)
            lon_sim = st.number_input("Simulasi Longitude", value=112.6085)
            if st.form_submit_button("Simpan Data"):
                new_rel = pd.DataFrame([{"Nama": nama, "No_Handphone": hp, "Latitude": lat_sim, "Longitude": lon_sim, "Status": "Aktif"}])
                st.session_state.relawan_data = pd.concat([st.session_state.relawan_data, new_rel], ignore_index=True)
                st.session_state.relawan_data.to_csv("data/relawan.csv", index=False)
                st.success("Relawan tersimpan!")
        st.data_editor(st.session_state.relawan_data, use_container_width=True)

    with t3:
        st.subheader("Cetak Laporan Penanganan PDF")
        if st.session_state.laporan_insiden:
            pdf_file = generate_pdf_report(st.session_state.laporan_insiden)
            st.download_button("📥 Download PDF Report", data=pdf_file, file_name="Laporan_Insiden_Simbok.pdf", mime="application/pdf")
        else:
            st.info("Belum ada riwayat insiden untuk dicetak.")

# --- MENU 3: CARI TAHU & EDUKASI ---
elif menu == "📚 Cari Tahu & Edukasi":
    st.markdown("<h1>📚 Pusat Informasi & Edukasi Kampus Aman</h1>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        if os.path.exists("assets/logo_stieima.png"): st.image("assets/logo_stieima.png", width=150)
    with c2:
        if os.path.exists("assets/logo_aplikasi.png"): st.image("assets/logo_aplikasi.png", width=150)
        
    st.markdown("""
    ### Panduan Singkat Penanganan Mandiri:
    1. **Tetap Tenang & Cari Ruang Ramai:** Sebisa mungkin dekati area yang terpantau CCTV atau ramai sivitas akademika.
    2. **Aktifkan Lapor Simbok:** Tekan tombol merah besar untuk memicu sinyal darurat ke satgas relawan.
    
    ---
    ### 🏢 Pengembang & Tim Pengabdian Masyarakat STIEIMA
    * **Pelindung:** Assoc.Prof.Dr. Hj. Amelia Setyawati, S.H., M.M | *Ketua STIEIMA*
    * **Penanggung Jawab:** Drs. Sudarjo, M.Pd., M.Si. | *Ketua LPPM*
    * **Ketua Tim:** Dimas Putri Mega Pratesa, S.Pd., M.Pd. | *Dosen STIEIMA*
    * **Arsitek & Pengembang Utama:** Ir. M Nasri AW, M.Eng.Sc, M.Kom | *Dosen STIEIMA*
    """)