# 🔥 RADICAL QR SCANNER FIX
# Bu dosya handle_scan fonksiyonunun yeni versiyonunu içerir

@socketio.on('scan_qr')
def handle_scan_radical(data):
    """🔥 RADICAL REWRITE: Ultra-reliable QR scanning"""
    print("\n" + "🔥"*50)
    print("RADICAL QR SCAN STARTING")
    print("🔥"*50)
    
    try:
        qr_id = data.get('qr_id', '').strip()
        session_id = data.get('session_id')
        user_id = session.get('user_id')
        
        print(f"📱 QR: {qr_id}")
        print(f"📱 Session: {session_id}")  
        print(f"📱 User: {user_id}")
        
        # VALIDATION
        if not all([qr_id, session_id, user_id]):
            print("❌ Missing required data")
            emit('scan_result', {'success': False, 'message': '❌ Eksik veri!'})
            return
        
        conn = get_db()
        cursor = conn.cursor()
        
        # STEP 1: Check QR exists
        execute_query(cursor, 'SELECT part_code, part_name FROM qr_codes WHERE qr_id = %s', (qr_id,))
        qr_data = cursor.fetchone()
        
        if not qr_data:
            close_db(conn)
            print("❌ QR not found")
            emit('scan_result', {'success': False, 'message': f'❌ QR kod bulunamadı: {qr_id}'})
            return
        
        part_code, part_name = qr_data
        print(f"✅ QR found: {part_code} - {part_name}")
        
        # STEP 2: Ensure session exists (RADICAL FIX)
        execute_query(cursor, 'SELECT COUNT(*) FROM count_sessions WHERE session_id = %s', (str(session_id),))
        if cursor.fetchone()[0] == 0:
            print("⚠️ Creating missing session")
            execute_query(cursor, 
                'INSERT INTO count_sessions (session_id, status, started_at) VALUES (%s, %s, %s)',
                (str(session_id), 'active', datetime.now()))
            print("✅ Session created")
        
        # STEP 3: Check duplicate
        execute_query(cursor, 'SELECT COUNT(*) FROM scanned_qr WHERE session_id = %s AND qr_id = %s', 
                     (str(session_id), qr_id))
        if cursor.fetchone()[0] > 0:
            close_db(conn)
            print("❌ Already scanned")
            emit('scan_result', {'success': False, 'message': f'⚠️ {part_name} zaten sayıldı!', 'duplicate': True})
            return
        
        # STEP 4: Insert scan record
        execute_query(cursor, 
            'INSERT INTO scanned_qr (session_id, qr_id, part_code, scanned_by, scanned_at) VALUES (%s, %s, %s, %s, %s)',
            (str(session_id), qr_id, part_code, user_id, datetime.now()))
        
        # STEP 5: Mark QR as used
        execute_query(cursor, 'UPDATE qr_codes SET is_used = true, used_at = %s WHERE qr_id = %s',
                     (datetime.now(), qr_id))
        
        conn.commit()
        close_db(conn)
        
        print(f"✅ SUCCESS: {part_name} scanned")
        
        # Get user name for display
        conn2 = get_db()
        cursor2 = conn2.cursor()
        execute_query(cursor2, 'SELECT full_name FROM envanter_users WHERE id = %s', (user_id,))
        user_result = cursor2.fetchone()
        user_name = user_result[0] if user_result else 'Kullanıcı'
        close_db(conn2)
        
        # 🔥 RADICAL BROADCAST - MULTIPLE EVENTS
        success_data = {
            'success': True,
            'message': f'✅ {part_name} sayıldı!',
            'qr_code': qr_id,
            'part_code': part_code,
            'part_name': part_name,
            'session_id': session_id,
            'scanned_by': user_name,
            'scanned_at': datetime.now().strftime('%H:%M:%S')
        }
        
        # Send to ALL clients - multiple events to ensure reception
        socketio.emit('scan_result', success_data)
        socketio.emit('qr_scanned', success_data)  # Alternative event
        socketio.emit('activity_update', success_data)  # Activity update
        
        print("🔥 RADICAL SUCCESS - TRIPLE BROADCAST COMPLETE!")
        print("🔥"*50)
        
    except Exception as e:
        print(f"❌ RADICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        emit('scan_result', {'success': False, 'message': f'❌ Sistem hatası: {e}'})


# 🔥 HELPER FUNCTION - Get total scanned count
def get_total_scanned(session_id):
    """Get total scanned count for session"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        execute_query(cursor, 'SELECT COUNT(*) FROM scanned_qr WHERE session_id = %s', (str(session_id),))
        count = cursor.fetchone()[0]
        close_db(conn)
        return count
    except:
        return 0