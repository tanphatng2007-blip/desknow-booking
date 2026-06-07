from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
app.secret_key = 'desknow_secret_key'

# Cấu hình múi giờ Việt Nam (UTC+7)
ICT = timezone(timedelta(hours=7))

# Lưu trữ dữ liệu
pending_bookings = []
confirmed_bookings = []
history_bookings = [] 

# Cấu trúc phòng
rooms = {
    'private': [f'C{i}' for i in range(1, 20)],
    'couple': [f'B{i}' for i in range(1, 23)],
    'public': ['Public']
}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        room_type = request.form['room_type']
        date = request.form['date']
        time = request.form['time']
        hours = int(request.form.get('hours', 1))
        
        available_table = None
        if room_type == 'public':
            available_table = 'Public'
        else:
            for table in rooms[room_type]:
                is_booked = any(b['table'] == table and b['date'] == date and b['time'] == time 
                                for b in confirmed_bookings + pending_bookings)
                if not is_booked:
                    available_table = table
                    break
        
        if not available_table:
            return render_template('full.html')

        booking_dt = datetime.strptime(f"{date} {time}", '%Y-%m-%d %H:%M')
        
        booking = {
            'id': len(pending_bookings) + len(confirmed_bookings) + len(history_bookings),
            'name': request.form['name'],
            'phone': request.form['phone'], # Đã thêm SĐT
            'email': request.form['email'],
            'date': date,
            'time': time,
            'hours': hours,
            'booking_datetime': booking_dt.strftime('%d/%m/%Y %H:%M'),
            'checkout_expected': (booking_dt + timedelta(hours=hours)).strftime('%d/%m/%Y %H:%M'),
            'table': available_table,
            'room_type': room_type,
            'price': {'public': 10000, 'private': 15000, 'couple': 25000}[room_type] * hours,
            'status': 'pending',
            'created_at': datetime.now(ICT).timestamp() # Sử dụng múi giờ ICT
        }
        pending_bookings.append(booking)
        return render_template('payment.html', data=booking)
    return render_template('index.html')

@app.route('/confirm/<int:booking_id>')
def confirm_booking(booking_id):
    for b in pending_bookings:
        if b['id'] == booking_id:
            b['status'] = 'confirmed'
            b['confirmed_at'] = datetime.now(ICT).strftime("%d/%m/%Y %H:%M:%S") # Sử dụng múi giờ ICT
            confirmed_bookings.append(b)
            pending_bookings.remove(b)
            break
    return redirect(url_for('admin'))

@app.route('/check-out/<int:booking_id>')
def check_out(booking_id):
    global confirmed_bookings
    for b in confirmed_bookings:
        if b['id'] == booking_id:
            b['checkout_at'] = datetime.now(ICT).strftime("%d/%m/%Y %H:%M:%S") # Sử dụng múi giờ ICT
            history_bookings.append(b)
            confirmed_bookings.remove(b)
            break
    return redirect(url_for('admin'))

@app.route('/webhook-bank', methods=['POST'])
def webhook_bank():
    data = request.json
    if not data: return jsonify({'status': 'error'}), 400
    content = data.get('content', '')
    for b in pending_bookings:
        if f"DeskNow {b['name']}".lower() in content.lower():
            b['status'] = 'confirmed'
            b['confirmed_at'] = datetime.now(ICT).strftime("%d/%m/%Y %H:%M:%S") # Sử dụng múi giờ ICT
            confirmed_bookings.append(b)
            pending_bookings.remove(b)
            return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'not found'}), 404

# API tìm kiếm cho Admin
@app.route('/search-booking', methods=['GET'])
def search_booking():
    query = request.args.get('q', '').lower()
    results = [b for b in (pending_bookings + confirmed_bookings + history_bookings) 
               if query in b['name'].lower() or query in b.get('phone', '')]
    return jsonify(results)

@app.route('/cancel-booking/<int:booking_id>')
def cancel_booking(booking_id):
    global pending_bookings
    pending_bookings = [b for b in pending_bookings if b['id'] != booking_id]
    return jsonify({'status': 'cancelled'})

@app.route('/admin')
def admin():
    return render_template('admin.html', pending=pending_bookings, confirmed=confirmed_bookings)

@app.route('/history')
def history():
    return render_template('history.html', history=history_bookings)

@app.route('/check-status/<int:booking_id>')
def check_status(booking_id):
    for b in pending_bookings:
        if b['id'] == booking_id: return jsonify({'status': 'pending'})
    for b in confirmed_bookings:
        if b['id'] == booking_id: return jsonify({'status': 'confirmed'})
    return jsonify({'status': 'none'})

@app.route('/success')
def success():
    booking = confirmed_bookings[-1] if confirmed_bookings else None
    return render_template('success.html', data=booking)

if __name__ == '__main__':
    app.run(debug=True)
