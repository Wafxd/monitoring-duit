import os
from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client, Client

app = Flask(__name__)

# Ini cara yang benar agar Vercel bisa membaca variabel rahasia
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Tambahkan try-except agar Vercel tidak langsung crash jika variabel belum diset
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None

@app.route('/')
def index():
    if not supabase:
        return "Supabase belum dikonfigurasi. Harap isi Environment Variables di Vercel.", 500

    # Ambil semua data transaksi, urutkan dari yang terlama ke terbaru
    response = supabase.table('transaksi').select('*').order('id', desc=False).execute()
    data = response.data

    # Menghitung data untuk Kartu Ringkasan (Summary Cards)
    if data:
        last_record = data[-1] # Ambil baris terakhir
        summary = {
            'total_aset': last_record['total_aset'],
            'saldo_darurat': last_record['saldo_darurat'],
            'saldo_reksadana': last_record['saldo_reksadana']
        }
    else:
        summary = {'total_aset': 0, 'saldo_darurat': 0, 'saldo_reksadana': 0}

    return render_template('index.html', data=data, summary=summary)

@app.route('/tambah', methods=['POST'])
def tambah():
    tanggal = request.form.get('tanggal')
    keterangan = request.form.get('keterangan')
    uang_masuk = int(request.form.get('uang_masuk') or 0)
    uang_keluar = int(request.form.get('uang_keluar') or 0)
    
    # Ambil saldo dari transaksi terakhir untuk kalkulasi
    last_record = supabase.table('transaksi').select('*').order('id', desc=True).limit(1).execute()
    
    saldo_darurat = last_record.data[0]['saldo_darurat'] if last_record.data else 0
    saldo_reksadana = last_record.data[0]['saldo_reksadana'] if last_record.data else 0

    # Logika pembagian otomatis
    if uang_masuk == 500000:
        saldo_darurat += 300000
        saldo_reksadana += 200000
    else:
        # Jika ada pengeluaran darurat biasa
        saldo_darurat += uang_masuk
        saldo_darurat -= uang_keluar

    total_aset = saldo_darurat + saldo_reksadana

    # Insert ke Supabase
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