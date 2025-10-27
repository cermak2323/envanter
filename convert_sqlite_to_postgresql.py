#!/usr/bin/env python3
"""
PostgreSQL Migration Helper
SQLite syntax'ını PostgreSQL syntax'ına çevirir
"""

import re

def convert_sqlite_to_postgresql(file_path):
    """SQLite syntax'ını PostgreSQL syntax'ına çevir"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # SQLite çift tırnak string'lerini PostgreSQL tek tırnak'a çevir
    # Sadece SQL sorguları içindeki string'leri değiştir
    content = re.sub(r'= "([^"]*)"', r"= '\1'", content)
    content = re.sub(r'!= "([^"]*)"', r"!= '\1'", content)
    content = re.sub(r'status = "([^"]*)"', r"status = '\1'", content)
    content = re.sub(r'role = "([^"]*)"', r"role = '\1'", content)
    
    # conn.close() çağrılarını close_db(conn) ile değiştir
    content = content.replace('conn.close()', 'close_db(conn)')
    
    # SQL parameter style'ını değiştir (? -> %s)
    # Bu daha karmaşık, manuel yapacağız
    
    print("✅ SQLite to PostgreSQL conversion completed")
    return content

if __name__ == "__main__":
    import sys
    
    file_path = "app.py"
    
    try:
        converted_content = convert_sqlite_to_postgresql(file_path)
        
        # Backup oluştur
        with open(f"{file_path}.backup", 'w', encoding='utf-8') as f:
            with open(file_path, 'r', encoding='utf-8') as orig:
                f.write(orig.read())
        
        # Güncellenmiş içeriği yaz
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(converted_content)
            
        print(f"✅ {file_path} başarıyla güncellendi")
        print(f"📁 Backup dosyası: {file_path}.backup")
        
    except Exception as e:
        print(f"❌ Hata: {e}")