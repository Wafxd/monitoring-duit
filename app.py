import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client, Client

app = Flask(__name__)

# Kunci rahasia wajib untuk mengamankan session login
app.secret_key = os.environ.get("SECRET_KEY", "kunci_rahasia_bebas_apa_aja")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None

# --- ROUTE LOGIN & LOGOUT ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Hardcode Akun Admin & User (Bisa kamu ganti passwordnya)
        if username == 'admin' and password == 'admin123':
            session['role'] = 'admin'
            return redirect(url_for('index'))
        elif username == 'tamu' and password == 'tamu123':
            session['role'] = 'user'
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Username atau password salah!")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear() # Hapus sesi login
    return redirect(url_for('login'))


# --- ROUTE UTAMA ---
@app.route('/')
def index():
    # Proteksi: Lempar ke login jika belum ada sesi
    if 'role' not in session:
        return redirect(url_for('login'))

    try:
        response = supabase.table('transaksi').select('*').order('id', desc=False).execute()
        data = response.data

        for row in data:
            if row['tanggal']:
                try:
                    dt = datetime.strptime(row['tanggal'], '%Y-%m-%d')
                    row['tanggal'] = dt.strftime('%d %b %Y')
                except ValueError:
                    pass

        if data:
            last_record = data[-1]
            summary = {
                'total_aset': last_record['total_aset'],
                'saldo_darurat': last_record['saldo_darurat'],
                'saldo_reksadana': last_record['saldo_reksadana']
            }
        else:
            summary = {'total_aset': 0, 'saldo_darurat': 0, 'saldo_reksadana': 0}

        # Kirim variabel role ke HTML
        return render_template('index.html', data=data, summary=summary, role=session['role'])
    
    except Exception as e:
        return f"Gagal narik data. Detail: {str(e)}", 500

# --- ROUTE TAMBAH ---
@app.route('/tambah', methods=['POST'])
def tambah():
    # Proteksi: Hanya admin yang boleh nge-POST data
    if session.get('role') != 'admin':
        return "Akses Ditolak: Hanya Admin yang bisa menambah data.", 403

    tanggal = request.form.get('tanggal')
    keterangan = request.form.get('keterangan')
    uang_masuk = int(request.form.get('uang_masuk') or 0)
    uang_keluar = int(request.form.get('uang_keluar') or 0)
    
    last_record = supabase.table('transaksi').select('*').order('id', desc=True).limit(1).execute()
    
    saldo_darurat = last_record.data[0]['saldo_darurat'] if last_record.data else 0
    saldo_reksadana = last_record.data[0]['saldo_reksadana'] if last_record.data else 0

    saldo_darurat += uang_masuk
    keterangan_lower = keterangan.lower()
    
    if "reksa" in keterangan_lower or "invest" in keterangan_lower:
        saldo_darurat -= uang_keluar
        saldo_reksadana += uang_keluar
    else:
        saldo_darurat -= uang_keluar

    total_aset = saldo_darurat + saldo_reksadana

    supabase.table('transaksi').insert({
        "tanggal": tanggal,
        "keterangan": keterangan,
        "uang_masuk": uang_masuk,
        "uang_keluar": uang_keluar,
        "saldo_darurat": saldo_darurat,
        "saldo_reksadana": saldo_reksadana,
        "total_aset": total_aset
    }).execute()

    return redirect(url_for('index'))

# --- ROUTE HAPUS ---
@app.route('/hapus/<int:id>', methods=['POST'])
def hapus(id):
    # Proteksi: Hanya admin yang boleh menghapus
    if session.get('role') != 'admin':
        return "Akses Ditolak: Hanya Admin yang bisa menghapus data.", 403
    
    supabase.table('transaksi').delete().eq('id', id).execute()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)