import os
from datetime import datetime # <--- Tambahkan ini di paling atas
from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client, Client

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Variabel untuk menampung pesan error
pesan_error = None
supabase = None

# Cek 1: Apakah Vercel benar-benar membaca variabelnya?
if not SUPABASE_URL or not SUPABASE_KEY:
    pesan_error = f"BOCORAN ERROR: Vercel gagal baca variabel. Status URL Terbaca: {bool(SUPABASE_URL)} | Status Key Terbaca: {bool(SUPABASE_KEY)}"
else:
    # Cek 2: Apakah koneksi ke Supabase ditolak?
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        pesan_error = f"BOCORAN ERROR: Koneksi ke Supabase gagal. Detail: {str(e)}"

@app.route('/')
def index():
    # Jika ada error dari Cek 1 atau Cek 2, tampilkan di layar putih
    if pesan_error:
        return pesan_error, 500

    # Cek 3: Apakah ada yang salah saat narik data dari tabel?
    try:
        response = supabase.table('transaksi').select('*').order('id', desc=False).execute()
        data = response.data

        # --- TAMBAHKAN BLOK INI UNTUK FORMAT TANGGAL ---
        for row in data:
            if row['tanggal']:
                try:
                    # Ubah '2026-03-06' jadi '06 Mar 2026'
                    dt = datetime.strptime(row['tanggal'], '%Y-%m-%d')
                    row['tanggal'] = dt.strftime('%d %b %Y')
                except ValueError:
                    pass
        # ------------------------------------------------

        if data:
            last_record = data[-1]
            summary = {
                'total_aset': last_record['total_aset'],
                'saldo_darurat': last_record['saldo_darurat'],
                'saldo_reksadana': last_record['saldo_reksadana']
            }
        else:
            summary = {'total_aset': 0, 'saldo_darurat': 0, 'saldo_reksadana': 0}

        return render_template('index.html', data=data, summary=summary)
    
    except Exception as e:
        return f"BOCORAN ERROR: Gagal narik data. Detail: {str(e)}", 500

@app.route('/tambah', methods=['POST'])
def tambah():
    tanggal = request.form.get('tanggal')
    keterangan = request.form.get('keterangan')
    uang_masuk = int(request.form.get('uang_masuk') or 0)
    uang_keluar = int(request.form.get('uang_keluar') or 0)
    
    last_record = supabase.table('transaksi').select('*').order('id', desc=True).limit(1).execute()
    
    saldo_darurat = last_record.data[0]['saldo_darurat'] if last_record.data else 0
    saldo_reksadana = last_record.data[0]['saldo_reksadana'] if last_record.data else 0

    if uang_masuk == 500000:
        saldo_darurat += 300000
        saldo_reksadana += 200000
    else:
        saldo_darurat += uang_masuk
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

if __name__ == '__main__':
    app.run(debug=True)