from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)
app.secret_key = 'desknow_secret_key'

pending_bookings = []
confirmed_bookings = []

rooms = {
    'private': [f'A{i}' for i in range(1, 9)],
    'couple': [f'B{i}' for i in range(1, 13)],
    'public': ['Public']
}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        room_type = request.form['room_type']
        date = request.form['date']
        time = request.form['time']
        
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

        booking = {
            'id': len(pending_bookings) + len(confirmed_bookings),
            'name': request.form['name'],
            'email': request.form['email'],
            'date': date,
            'time': time,
            'table': available_table,
            'room_type': room_type,
            'price': {'public': 10000, 'private': 15000, 'couple': 25000}[room_type] * int(request.form['hours']),
            'status': 'pending'
        }
        pending_bookings.append(booking)
        return render_template('payment.html', data=booking)
    return render_template('index.html')

@app.route('/webhook-bank', methods=['POST'])
def webhook_bank():
    data = request.json
    # Giả sử dịch vụ trung gian gửi nội dung chuyển khoản trong khóa 'content'
    content = data.get('content', '')
    
    for b in pending_bookings:
        # Kiểm tra cú pháp "DeskNow + Tên" trong nội dung chuyển khoản
        if f"DeskNow {b['name']}".lower() in content.lower():
            b['status'] = 'confirmed'
            confirmed_bookings.append(b)
            pending_bookings.remove(b)
            return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'not found'}), 404

@app.route('/admin')
def admin():
    return render_template('admin.html', bookings=pending_bookings)

@app.route('/confirm/<int:booking_id>')
def confirm_booking(booking_id):
    for b in pending_bookings:
        if b['id'] == booking_id:
            b['status'] = 'confirmed'
            confirmed_bookings.append(b)
            pending_bookings.remove(b)
            break
    return redirect(url_for('admin'))

@app.route('/check-status/<int:booking_id>')
def check_status(booking_id):
    for b in pending_bookings + confirmed_bookings:
        if b['id'] == booking_id: return jsonify({'status': b['status']})
    return jsonify({'status': 'none'})

@app.route('/success')
def success():
    booking = confirmed_bookings[-1] if confirmed_bookings else None
    return render_template('success.html', data=booking)

if __name__ == '__main__':
    app.run(debug=True)