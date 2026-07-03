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

BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")

if 'relawan_data' not in st.session_state:
    try: st.session_state.relawan_data = pd.read_csv("data/relawan.csv")
    except: st.session_state.relawan_data = pd.DataFrame(columns=["Nama", "No_Handphone", "Latitude", "Longitude", "Status"])

if 'laporan_insiden' not in st.session_state: st.session_state.laporan_insiden = []
if 'logo_clicks' not in st.session_state: st.session_state.logo_clicks = 0
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False
if 'panic_triggered' not in st.session_state: st.session_state.panic_triggered = False
# store last triggered coordinates so post-trigger UI can access them reliably
if 'last_lat' not in st.session_state: st.session_state.last_lat = None
if 'last_lon' not in st.session_state: st.session_state.last_lon = None

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


# Helper: safe image loader to avoid Streamlit crashing when an image file is missing or unreadable
def safe_st_image(path_or_data, **kwargs):
    """Try to load an image from disk (preferred) or pass through raw data.
    If the file is missing or unreadable, fail gracefully with a message instead of raising.
    """
    try:
        # If path_or_data looks like a path to a file on disk, prefer reading bytes and passing them to st.image
        if isinstance(path_or_data, str) and os.path.exists(path_or_data):
            with open(path_or_data, 'rb') as f:
                data = f.read()
            st.image(data, **kwargs)
        else:
            # If the provided value isn't a file path or doesn't exist, attempt to pass it directly
            st.image(path_or_data, **kwargs)
    except Exception as e:
        # Don't raise here; show a user-friendly warning so the app doesn't crash due to missing assets
        st.warning(f"Gagal memuat gambar '{path_or_data}'. Harap pastikan file ada di folder 'assets' atau gunakan URL yang dapat diakses. (Error: {e})")


with st.sidebar:
    # Use safe image loader for sidebar logo to avoid MediaFileStorageError when file missing
    safe_st_image("assets/logo_stieima.png", use_container_width=True)
    
    # PERBAIKAN NAVIGATION ACTION BUTTON
    # Pastikan state inisialisasi selalu terdeteksi
    if st.button("✨ Verifikasi Sistem Kampus Aman", use_container_width=True):
        st.session_state.logo_clicks += 1
        
    # KONDISI PASTI MUNCUL: Cukup jika logo_clicks > 0 langsung tayangkan tombol Kembali ke Halaman Utama
    if st.session_state.logo_clicks > 0:
        if st.button("⬅️ Kembali ke Halaman Utama", use_container_width=True):
            st.session_state.logo_clicks = 0
            st.session_state.admin_mode = False
            st.rerun()
            
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
    loc_data = streamlit_geolocation()
    
    col_l1, col_l2, col_l3 = st.columns([2, 1, 2])
    with col_l2:
        # Use safe image loader for main logo as well
        safe_st_image("assets/logo_aplikasi.png", use_column_width=True)
            
    st.markdown("<h2 style='text-align: center; color: #2d3748;'>LAPOR SIMBOK, Sistem Perlindungan Kampus Darurat jika terjadi kekerasan seksual & bullying; tekan ijin aktivasi GPS anda di ikon  atas kiri, lalu scrol kebawah klik BANTU AKU</h2>", unsafe_allow_html=True)
    
    if not (loc_data and loc_data.get("latitude") and loc_data.get("longitude") ):
        st.warning("⚠️ Mengakses koordinat GPS... Harap izinkan pelacakan lokasi peramban browser Anda agar tombol respons darurat aktif.")
        
    st.write("---")
    
    # PERBAIKAN TOTAL: Menghapus teks HTML mentah di Pusat Edukasi, dikonversi penuh ke Native Markdown Streamlit agar rapi dan tidak bocor sebagai kode
    st.markdown("### 📚 Pusat Edukasi & Panduan Mitigasi Krisis Kampus Aman")
    st.write("Sistem **Lapor Simbok** dikembangkan secara khusus oleh Tim Pengabdian Masyarakat STIEIMA sebagai instrumen perlindungan preventif dan represif bagi seluruh sivitas akademika dari segala[...]")
    
    st.markdown("#### 1. Batasan & Klasifikasi Tindakan Krisis")
    st.markdown("* **Bullying (Perundungan):** Segala bentuk intimidasi, pemaksaan, kekerasan psikologis atau verbal, serta pengucilan terencana yang terjadi di lingkungan fisik kampus maupun ruang si[...]")
    st.markdown("* **Kekerasan Seksual:** Setiap perbuatan fisik maupun non-fisik yang merendahkan, menghina, melecehkan, dan/atau menyerang tubuh atau fungsi reproduksi seseorang atas dasar ketimpang[...]")
    
    st.markdown("#### 2. Protokol Tiga Langkah Mitigasi Mandiri")
    st.markdown("1. **Amankan Diri Fisik:** Segera menjauh dari area konflik menuju koridor yang terpantau kamera CCTV, area ramai perkuliahan, atau langsung ke Posko Satgas Utama.")
    st.markdown("2. **Aktifkan Sinyal Lapor Simbok:** Pastikan GPS peramban aktif dan tekan tombol darurat merah **\"BANTU AKU....\"** di bawah untuk menyiarkan titik koordinat Bapak/Ibu langsung ke p[...]")
    st.markdown("3. **Preservasi Alat Bukti:** Amankan tangkapan layar (*screenshot*), rekaman audio, atau dokumentasi visual lainnya guna memperlancar proses investigasi dan penegakan regulasi hukum [...]")
    st.write("---")

    # --- TOMBOL DARURAT: ditempatkan langsung sesudah Pusat Edukasi ---
    c_b1, c_b2, c_b3 = st.columns([1, 2, 1])
    with c_b2:
        if loc_data and loc_data.get("latitude") and loc_data.get("longitude"):
            user_lat = loc_data["latitude"]
            user_lon = loc_data["longitude"]
            
            st.markdown("<p style='text-align: center; color: green; font-weight: bold;'>🟢 GPS Siap & Lokasi Terkunci Otomatis</p>", unsafe_allow_html=True)
            
            # gunakan key agar tidak bentrok jika komponen dirender beberapa kali
            if st.button("🚨 BANTU AKU.... ", use_container_width=True, type="primary", key="panic_button"):
                send_telegram_alert(user_lat, user_lon)
                st.session_state.laporan_insiden.append({
                    "Waktu": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Lat": user_lat, "Lon": user_lon, "Status": "Relawan Meluncur"
                })
                # simpan koordinat terakhir yang memicu panic agar UI pasca-trigger konsisten
                st.session_state.last_lat = user_lat
                st.session_state.last_lon = user_lon
                st.session_state.panic_triggered = True
                st.balloons()
        else:
            st.warning("Mengakses satelit GPS... Harap aktifkan/izinkan pelacakan lokasi peramban browser Anda.")

    # --- TAMPILAN PASCA-TRIGGER: informasi relawan & peta ---
    if st.session_state.panic_triggered:
        # ambil koordinat yang tersimpan saat tombol ditekan
        user_lat = st.session_state.last_lat
        user_lon = st.session_state.last_lon
        if user_lat is None or user_lon is None:
            st.error("Koordinat terakhir tidak tersedia. Pastikan GPS aktif dan coba lagi.")
        else:
            relawan_aktif = st.session_state.relawan_data[st.session_state.relawan_data["Status"] == "Aktif"]
            if not relawan_aktif.empty:
                relawan_aktif = relawan_aktif.copy()
                relawan_aktif["Jarak"] = relawan_aktif.apply(lambda r: hitung_jarak(user_lat, user_lon, r["Latitude"], r["Longitude"]), axis=1)
                terdekat = relawan_aktif.sort_values(by="Jarak").iloc[0]
                nama_relawan = terdekat["Nama"]
                jarak_relawan = round(terdekat["Jarak"], 2)
                posisi_relawan = f"koordinat ({terdekat['Latitude']}, {terdekat['Longitude']}) dengan jarak {jarak_relawan} km"
            else:
                nama_relawan = "Pusat Satgas STIEIMA"
                posisi_relawan = "Posko Utama Pusat Komando"
            
            st.error(f"⚠️ **INFORMASI PENOLONG:** Relawan **{nama_relawan}** sedang meluncur dari posisi **{posisi_relawan}** menuju tempat Anda.")
            
            st.markdown(
                "<div style='text-align: center; margin-top: 15px; margin-bottom: 20px;'>"
                "<a href='https://t.me/Lapor_Simbok_STIEIMA' target='_blank' style='text-decoration: none; color: #ffffff; background-color: #0088cc; padding: 8px 16px; border-radius: 20px; font-weight: bold;'>"
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
            for ins in st.session_state.laporan_insiden:
                folium.Marker([ins["Lat"], ins["Lon"]], popup=f"🚨 LOKASI KORBAN ({ins['Waktu']})", icon=folium.Icon(color='red', icon='exclamation-sign')).add_to(m_korban)
            folium_static(m_korban)

else:
    st_autorefresh(interval=10000, key="admin_sync_v12")
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
        with st.form("add_relawan_v12"):
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
