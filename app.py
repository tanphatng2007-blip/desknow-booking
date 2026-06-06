from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)
app.secret_key = 'desknow_secret_key'

# Lưu ý: Các biến này lưu trên RAM, khi deploy lại web sẽ mất dữ liệu. 
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
        
        # Kiểm tra phòng trống
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
            'price': {'public': 10000, 'private': 15000, 'couple': 25000}[room_type] * int(request.form.get('hours', 1)),
            'status': 'pending'
        }
        pending_bookings.append(booking)
        return render_template('payment.html', data=booking)
    return render_template('index.html')

@app.route('/webhook-bank', methods=['POST'])
def webhook_bank():
    # In dữ liệu nhận được ra log của Render để debug
    data = request.json
    print(f"DEBUG - Webhook data received: {data}")
    
    if not data:
        return jsonify({'status': 'error', 'message': 'Empty JSON'}), 400

    content = data.get('content', '')
    
    # Kiểm tra đơn hàng khớp với nội dung chuyển khoản
    found = False
    for b in pending_bookings:
        # So khớp nội dung: "DeskNow [Tên]"
        if f"DeskNow {b['name']}".lower() in content.lower():
            b['status'] = 'confirmed'
            confirmed_bookings.append(b)
            pending_bookings.remove(b)
            print(f"DEBUG - Booking {b['id']} confirmed successfully!")
            found = True
            break
            
    if found:
        return jsonify({'status': 'success'}), 200
    else:
        print(f"DEBUG - No matching booking found for content: {content}")
        return jsonify({'status': 'not found'}), 404

@app.route('/admin')
def admin():
    return render_template('admin.html', bookings=pending_bookings)

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
