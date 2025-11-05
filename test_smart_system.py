#!/usr/bin/env python3
import pandas as pd
import sqlite3
import uuid
import qrcode
import os
from datetime import datetime

def test_smart_qr_system():
    """Akıllı QR sistemini test et"""
    
    # Test verilerini yükle
    df = pd.read_csv('test_smart_qr.csv')
    print('📊 Test verileri:')
    print(df)
    
    # Database connection
    conn = sqlite3.connect('instance/envanter_local.db')
    cursor = conn.cursor()
    
    print('\n🔍 İşlem öncesi QR durumu:')
    cursor.execute('SELECT part_code, COUNT(*) as qr_count FROM qr_codes GROUP BY part_code')
    before_qr = cursor.fetchall()
    for qr in before_qr:
        print(f'  {qr[0]}: {qr[1]} QR kod')
    
    # Akıllı QR sistemi simülasyonu
    for _, row in df.iterrows():
        part_code = row['part_code']
        part_name = row['part_name'] 
        quantity = int(row['quantity'])
        
        print(f'\n🔧 İşleniyor: {part_code} - {quantity} adet')
        
        # Mevcut QR kodlarını say
        cursor.execute('SELECT COUNT(*) FROM qr_codes WHERE part_code = ?', (part_code,))
        existing_qr_count = cursor.fetchone()[0]
        print(f'  📊 Mevcut QR: {existing_qr_count}')
        print(f'  📋 Gerekli QR: {quantity}')
        
        # Parts tablosunu güncelle/ekle
        cursor.execute('SELECT id FROM parts WHERE part_code = ?', (part_code,))
        part_exists = cursor.fetchone()
        
        if part_exists:
            print(f'  ✅ Parça mevcut - güncelleniyor')
            cursor.execute('''UPDATE parts SET part_name = ?, created_at = ? 
                             WHERE part_code = ?''', 
                          (part_name, datetime.now(), part_code))
        else:
            print(f'  🆕 Yeni parça ekleniyor')
            cursor.execute('''INSERT INTO parts (part_code, part_name, description, 
                             created_at, created_by, is_active) 
                             VALUES (?, ?, ?, ?, ?, ?)''',
                          (part_code, part_name, '', datetime.now(), 'test_user', True))
        
        # Eksik QR kodları hesapla ve oluştur
        missing_qr = quantity - existing_qr_count
        
        if missing_qr > 0:
            print(f'  ➕ {missing_qr} QR kod oluşturuluyor')
            
            for i in range(missing_qr):
                qr_id = str(uuid.uuid4())[:8]
                
                # QR kod verisi oluştur
                cursor.execute('''INSERT INTO qr_codes (qr_id, part_code, part_name, 
                                 created_at, created_by, is_used, is_downloaded) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
                              (qr_id, part_code, part_name, datetime.now(), 
                               'test_user', False, False))
                print(f'    📱 QR oluşturuldu: {qr_id}')
                
        elif missing_qr < 0:
            print(f'  ⚠️  Fazla QR var: {abs(missing_qr)} (SİLİNMEYECEK - Akıllı sistem!)')
        else:
            print(f'  ✅ QR sayısı ideal')
    
    conn.commit()
    
    print('\n🔍 İşlem sonrası QR durumu:')
    cursor.execute('SELECT part_code, COUNT(*) as qr_count FROM qr_codes GROUP BY part_code')
    after_qr = cursor.fetchall()
    for qr in after_qr:
        print(f'  {qr[0]}: {qr[1]} QR kod')
    
    total_qr = sum(qr[1] for qr in after_qr) if after_qr else 0
    print(f'\n📊 Toplam QR Codes: {total_qr}')
    
    conn.close()
    print('\n✅ Akıllı QR sistemi testi tamamlandı!')

if __name__ == '__main__':
    test_smart_qr_system()