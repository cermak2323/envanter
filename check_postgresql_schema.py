#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
import os

# PostgreSQL bağlantı
try:
    conn = psycopg2.connect(
        host=os.environ.get('PGHOST', 'localhost'),
        user=os.environ.get('PGUSER', 'postgres'),
        password=os.environ.get('PGPASSWORD', ''),
        database=os.environ.get('PGDATABASE', 'postgres'),
        port=os.environ.get('PGPORT', '5432')
    )
    cursor = conn.cursor()
    
    print("=" * 70)
    print("PostgreSQL count_sessions Table Schema")
    print("=" * 70)
    
    # Get table columns
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'count_sessions'
        ORDER BY ordinal_position
    """)
    
    columns = cursor.fetchall()
    
    if columns:
        print("\n📋 Columns in count_sessions:")
        for col in columns:
            nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
            default = f"DEFAULT {col[3]}" if col[3] else ""
            print(f"   - {col[0]:25} | {col[1]:20} | {nullable:10} | {default}")
    else:
        print("❌ Table count_sessions not found!")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nTry connecting with PgAdmin4 and checking the table schema manually")
