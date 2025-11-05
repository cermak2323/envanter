# This is the updated get_reports function that uses the correct column names
# You should replace the old function in app.py with this one

@app.route('/get_reports')
@login_required
def get_reports():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        # Use the correct column names from schema
        cursor.execute('''
            SELECT id, session_id, report_filename, report_title, created_at,
                   total_expected, total_scanned, accuracy_rate
            FROM count_reports
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        reports = []
        for row in rows:
            # Map DB columns to the frontend-expected format
            reports.append({
                'id': row[0],
                'session_id': row[1],
                'filename': row[2],  # report_filename
                'title': row[3],     # report_title
                'created_at': row[4],
                'total_expected': row[5],
                'total_scanned': row[6],
                'total_difference': (row[6] - row[5]) if (row[5] is not None and row[6] is not None) else None,
                'created_by': 'Bilinmeyen'  # Default since we don't track creator
            })

        return jsonify(reports)

    except psycopg2.Error as e:
        logging.exception(f"Database error in get_reports: {e}")
        # Try to rollback and close connection cleanly
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        return jsonify({'error': 'Database error occurred'}), 500
        
    except Exception as e:
        logging.exception(f"Unexpected error in get_reports: {e}")
        return jsonify({'error': 'Internal server error'}), 500
        
    finally:
        try:
            if conn:
                close_db(conn)
        except Exception as e:
            logging.error(f"Error closing database connection: {e}"))